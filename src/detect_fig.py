"""物体検出を行うモジュール.

ベストショット画像を選択するための物体検出を行う。
@author: kawanoichi
"""

import torch
from pathlib import Path
import os
import numpy as np
import sys
from ultralytics.utils.plotting import Annotator, colors
home_directory = os.path.expanduser("~")  # noqa
PATH = os.path.join(
    home_directory, "etrobocon2023-camera-system", "yolo")  # noqa
sys.path.append(PATH)  # noqa
from models.common import DetectMultiBackend
from utils.general import (
    check_img_size, cv2, non_max_suppression, scale_boxes)
from utils.torch_utils import select_device
from utils.augmentations import letterbox


def exit_check(path):
    """ファイル, ディレクトリが存在するかの確認パス"""
    if not os.path.exists(path):
        print(f"Error: {path} does not exist.")
        sys.exit(1)


class Detect():
    """yolov5(物体検出)をロボコン用に編集したクラス."""

    DEVICE = 'cpu'
    IMG_SIZE=(640, 480)

    def __init__(self, 
                 img_path = 'image.png',
                 weights='best.pt',
                 label_data='label_data.yaml',
                 conf_thres=0.25,
                 iou_thres=0.45,
                 max_det=10,
                 line_thickness=3,
                 stride=32):
        """コンストラクタ.

        Args:
            img_path (str): 画像パス
            weights (str): 重みファイルパス
            label_data (str): ラベルを記述したファイルパス
            conf_thres (float): 信頼度閾値
            iou_thres (float): NMS IOU 閾値
            max_det (int): 最大検出数
            line_thickness (int): カメラID
            stride (int): ストライド
        """
        exit_check(img_path)
        exit_check(weights)
        exit_check(label_data)
        self.img_path = img_path
        self.weights = weights
        self.label_data = label_data
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        self.max_det = max_det
        self.line_thickness = line_thickness
        self.stride = stride

    def read_image(self, auto=True):
        """画像を読み込む関数.

        Args:
            img_path: 画像パス
        Returns:
            im: パディング処理を行った入力画像
            im0: 入力画像 
        """
        im0 = cv2.imread(self.img_path)  # BGR
        if im0 is None:
            return None, None

        # リサイズとパディング処理
        im = letterbox(im0, Detect.IMG_SIZE, stride=self.stride,
                        auto=auto)[0]
        # BGR -> RGB
        im = im.transpose((2, 0, 1))[::-1]
        # 連続したメモリ領域に変換
        im = np.ascontiguousarray(im)

        return im, im0


    def predict(self, save_path=None):
        """物体の検出を行う関数.
        Args:
            save_path(str): 検出結果の画像保存パス
                            Noneの場合、保存しない 
        Returns:
            im: パディング処理を行った入力画像
            im0: 入力画像 
        """
        # cpuを指定
        device = select_device(Detect.DEVICE)

        # モデルの読み込み
        model = DetectMultiBackend(
            self.weights, device=device, dnn=False, data=self.label_data, fp16=False)

        stride, labels, pt = model.stride, model.names, model.pt

        # 画像のサイズを指定されたストライド（ステップ）の倍数に合わせるための関数
        img_size = check_img_size(Detect.IMG_SIZE, s=stride)  # >> [640, 640]

        # モデルの初期化
        bs = 1  # batch_size
        model.warmup(imgsz=(1 if pt or model.triton else bs,
                     3, *img_size))  # warmup

        # 画像の読み込み
        im, im0s = self.read_image()
        
        im = torch.from_numpy(im).to(model.device) # PyTorchのテンソルに変換
        im = im.half() if model.fp16 else im.float()  # uint8 to fp16/32

        # スケーリング
        im /= 255  # 0 - 255 to 0.0 - 1.0

        # torch.Size([3, 640, 640]) >> torch.Size([1, 3, 640, 640])
        if len(im.shape) == 3:
            im = im[None]

        # 検出
        pred = model(im, augment=False, visualize=False)

        # 非最大値抑制 (NMS) により重複検出を拒否
        # conf_thres: 信頼度の閾値, iou_thres: IoUの閾値
        # classes: 検出するクラスのリスト, agnostic: Trueの場合、クラスを無視してNMSを実行
        pred = non_max_suppression(
            pred, self.conf_thres, self.iou_thres, max_det=self.max_det, classes=None, agnostic=False)
        print("pred", len(pred))

        if save_path:
            # 検出結果の処理
            for det in pred:  # det:検出結果
                print(Path(self.img_path).name, " 検出数", len(det), )

                im0 = im0s.copy()

                # 画像にバウンディングボックスやラベルなどのアノテーションを追加
                annotator = Annotator(
                    im0, line_width=self.line_thickness, example=str(labels))

                if len(det):
                    # バウンディングボックス座標を画像サイズから別のサイズに変換
                    det[:, :4] = scale_boxes(
                        im.shape[2:], det[:, :4], im0.shape).round()

                    # Write results
                    # バウンディングボックスの座標(xyxy：[x_min, y_min, x_max, y_max] 形式)、信頼度(conf)、クラスID(cls)
                    for *xyxy, conf, cls in reversed(det):
                        c = int(cls)  # クラスid
                        label = f'{labels[c]} {conf:.2f}'
                        # 画像にバウンディングボックスとラベルを追加
                        annotator.box_label(xyxy, label, color=colors(c, True))

            # 検出結果を含む画像を保存
            im0 = annotator.result()
            cv2.imwrite(save_path, im0)
            print('保存')


if __name__ == '__main__':
    image_path = '/home/kawano/etrobocon2023-camera-system/yolo/test_image.png'
    save_path = '/home/kawano/etrobocon2023-camera-system/yolo/detect_test_image.png'
    weights = '/home/kawano/etrobocon2023-camera-system/yolo/best.pt'
    label_data = '/home/kawano/etrobocon2023-camera-system/yolo/label_data.yaml'
    d = Detect(img_path=image_path, weights=weights, label_data=label_data)
    d.predict(save_path)
    print('完了')
