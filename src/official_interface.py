"""競技システムインタフェース.

競技システムとの通信を行うクラス.
@author: miyashita64
"""
import requests
import cv2


class ResponseError(Exception):
    """レスポンスエラー用の例外."""

    def __init__(self, message):
        """コンストラクタ.

        Args:
            message (string): エラーメッセージ
        """
        super().__init__(message)


class OfficialInterface:
    """IoT列車の操作を行うクラス."""

    SERVER_IP = "192.168.100.1"    # 競技システムのIPアドレス
    TEAM_ID = 63                   # チームID

    @classmethod
    def set_train_pwm(cls, pwm) -> bool:
        """IoT列車のPWM値を設定する.

        Args:
            pwm (int): モータ出力

        Returns:
            success (bool): 通信が成功したか(成功:true/失敗:false)
        """
        success = False
        url = f"http://{cls.SERVER_IP}/train?pwm={pwm}"
        try:
            # APIにリクエストを送信
            response = requests.put(url)
            # レスポンスのステータスコードが200の場合、通信成功
            if response.status_code != 200:
                raise ResponseError("Failed to set PWM for IoT train.")
            success = True
        except Exception as e:
            print(e)
        return success

    @classmethod
    def upload_snap(cls, img_path, resize_img_path) -> bool:
        """フィグ画像をアップロードする.

        Args:
            img_path (str): アップロードする画像のパス
            resize_img_path (str): リサイズした画像を保存するパス

        Returns:
            success (bool): 通信が成功したか(成功:true/失敗:false)
        """
        success = False
        url = f"http://{cls.SERVER_IP}/snap"
        headers = {
            "Content-Type": "image/png"
        }
        # チームIDをリクエストに含める
        params = {
            "id": cls.TEAM_ID
        }

        try:
            # 指定された画像を開く
            with open(img_path, "rb") as image_file:
                cls.resize_img(img_path, resize_img_path)
                image_data = image_file.read()
            # APIにリクエストを送信
            response = requests.post(url, headers=headers,
                                     data=image_data, params=params)
            # レスポンスのステータスコードが200の場合、通信成功
            if response.status_code != 200:
                raise ResponseError("Failed to send fig image.")
            success = True
        except Exception as e:
            print(e)
        return success

    @classmethod
    def resize_img(cls, img_path, save_path, resize_w, resize_h) -> None:
        """一枚の画像をリサイズ.

        Args:
            img_path (string): リサイズする画像のパス
            save_path (string): リサイズした画像を保存するパス
            resize_w (int): リサイズする画像の幅
            resize_h (int): リサイズする画像の高さ
        """
        # 読み込み
        img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        height, width, _ = img.shape
        # リサイズ
        resized_img = cv2.resize(img, (resize_w, resize_h))
        cv2.imwrite(save_path, resized_img)
