from utils.torch_utils import select_device, smart_inference_mode  # OK
from utils.general import (
    check_img_size, cv2, non_max_suppression, scale_boxes)
from utils.dataloaders import LoadImages
from models.common import DetectMultiBackend
from ultralytics.utils.plotting import Annotator, colors
import argparse
import os
from pathlib import Path

import torch


@smart_inference_mode()
def predict(
        weights='best.pt',  # 重みファイルのpath
        source='detect_image',  # 予測を行う画像データ
        save_dir='runs/detect',  # 結果の保存先path
        data='label_data.yaml',  # dataset.yaml path
        imgsz=(640, 640),  # inference size (height, width)
        conf_thres=0.25,  # 信頼度閾値
        iou_thres=0.45,  # NMS IOU 閾値
        max_det=1000,  # maximum detections per image
        device='cpu',  # cuda device, i.e. 0 or 0,1,2,3 or cpu
        save_result=True,  # do not save images/videos
        line_thickness=3,  # バウンディングボックスの線の太さ (pixels)
):
    # 保存先ディレクトリがなければ作成
    save_dir = os.path.join(save_dir, 'result')
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    else:
        save_dir += str(len(os.listdir(save_dir))+1)
        print("save_dir", save_dir)
        os.makedirs(save_dir, exist_ok=True)

    # Load model
    device = select_device(device)  # >> cuda:0

    model = DetectMultiBackend(
        weights, device=device, dnn=False, data=data, fp16=False)

    """
    stride 32
    labels {0: 'front', 1: 'back', 2: 'right', 3: 'left'}
    pt True
    """
    stride, labels, pt = model.stride, model.names, model.pt

    # 画像のサイズを指定されたストライド（ステップ）の倍数に合わせるための関数
    imgsz = check_img_size(imgsz, s=stride)  # >> [640, 640]

    # Dataloader
    bs = 1  # batch_size
    dataset = LoadImages(source, img_size=imgsz,
                         stride=stride, auto=pt)

    # Run inference
    model.warmup(imgsz=(1 if pt or model.triton else bs, 3, *imgsz))  # warmup

    """初回ループの出力
    path: /home/kawano/etrobocon2023-camera-system/src/detect_fig/verification_data/image1.png
    im:画像データのNumPy配列 (3, 640, 640)
    im0s: オリジナルの画像データ(640, 640, 3)
    s: image 1/36 /home/kawano/etrobocon2023-camera-system/src/detect_fig/verification_data/image1.png: 
    """
    for path, im, im0s, _, _ in dataset:
        # TODO: withを消していいと思うが、その時はdtにいらない要素がある？

        # PyTorchのテンソルに変換
        im = torch.from_numpy(im).to(model.device)

        # model.fp16がTrueの場合は、テンソルを半精度浮動小数点数（float16）に変換
        # そうでない場合は、単精度浮動小数点数（float32）に変換
        im = im.half() if model.fp16 else im.float()  # uint8 to fp16/32

        # テンソルの値を0から255の範囲から0.0から1.0の範囲にスケーリング
        im /= 255  # 0 - 255 to 0.0 - 1.0

        # もしimの形状が3次元（例：[3, 640, 640]）の場合、バッチ次元を追加して4次元のテンソルに変換
        # これは、モデルに複数の画像を一度に処理させるための操作
        if len(im.shape) == 3:
            # expand for batch dim torch.Size([3, 640, 640]) >> torch.Size([1, 3, 640, 640])
            im = im[None]

        """
        im: 入力画像
        augment: データ拡張を行うかどうか
        visualize: 可視化を行うかどうか
        len(pred): 2
        """
        pred = model(im, augment=False, visualize=False)

        """
        pred: 物体検出結果
        conf_thres: 信頼度の閾値
        iou_thres: IoUの閾値
        classes: 検出するクラスのリスト
        agnostic_nms: NMS(Non-Maximum Suppression)を適用するか
        max_det: 最大検出数
        """
        # NMS(Non-Maximum Suppression)関数
        # 重なりのある複数の物体検出結果をフィルタリング
        pred = non_max_suppression(
            pred, conf_thres, iou_thres, max_det=max_det, classes=None, agnostic=False)

        # 検出結果の処理
        for det in pred:  # det:検出結果
            print(Path(path).name, " 検出数", len(det), )

            # im0: 入力画像
            im0 = im0s.copy()

            # path >> /home/kawano/etrobocon2023-camera-system/src/detect_fig/verification_data/image1.png
            path = Path(path)  # 入力と出力が同じだが、意味あるの？

            # save_path >> runs/detect/result22/image1.png
            save_path = os.path.join(str(save_dir), str(path.name))  # im.jpg

            # 画像にバウンディングボックスやラベルなどのアノテーションを追加
            annotator = Annotator(
                im0, line_width=line_thickness, example=str(labels))

            if len(det):
                # バウンディングボックス座標を画像サイズから別のサイズに変換
                det[:, :4] = scale_boxes(
                    im.shape[2:], det[:, :4], im0.shape).round()

                # Write results
                # バウンディングボックスの座標(xyxy：[x_min, y_min, x_max, y_max] 形式)、信頼度(conf)、クラスID(cls)
                for *xyxy, conf, cls in reversed(det):
                    if save_result:
                        c = int(cls)  # クラスid

                        label = f'{labels[c]} {conf:.2f}'
                        # label >> front 0.94
                        #
                        """
                        annotator.box_label():画像にバウンディングボックスとラベルを追加
                        colors():検出されたクラスのインデックスに基づいて、一意の色を生成。
                                 True パラメータは、色をランダムに選択することを指示。
                                 異なるクラスは異なる色で表示されます。
                        """
                        annotator.box_label(xyxy, label, color=colors(c, True))

            # 検出結果を含む画像を保存
            im0 = annotator.result()
            if save_result:
                cv2.imwrite(save_path, im0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str,
                        default='best.pt', help='学習済みモデル(重み)のパス')
    parser.add_argument('--source', type=str, default='detect_image',
                        help='物体検出を行うファイルパス、もしくはそれを格納したディレクトリパス')
    parser.add_argument('--data', type=str, default='label_data.yaml',
                        help='ラベルを記述したファイルのパス')
    parser.add_argument('--imgsz', '--img', '--img-size', nargs='+',
                        type=int, default=[640], help='画像サイズ')
    parser.add_argument('--conf-thres', type=float,
                        default=0.3, help='信頼度閾値')
    parser.add_argument('--iou-thres', type=float,
                        default=0.2, help='NMS IoU閾値')  # 低いほどはじかれやすい
    parser.add_argument('--max-det', type=int, default=2,
                        help='画像あたりの最大検出数')
    parser.add_argument('--device', default='cpu',
                        help='cuda id or cpu')
    parser.add_argument('--save_result', default=True,
                        help='結果を画像に描画し、保存する')
    parser.add_argument('--save_dir', default='detect_result',
                        help='保存先ディレクトリ')
    parser.add_argument('--line-thickness', default=3,
                        type=int, help='バウンディングボックスの線の太さ (pixels)')
    opt = parser.parse_args()
    opt.imgsz *= 2 if len(opt.imgsz) == 1 else 1

    predict(**vars(opt))

    print('完了!!')
