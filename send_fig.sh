#!/bin/bash

# 引数は2つ
# 第1引数が接続先IPアドレス、第2引数が送信する画像ファイル名

# リモートマシンのユーザ名と接続先IPアドレス
# 第1引数をREMOTE_IPに格納する
REMOTE_USER="et2023"
REMOTE_IP="$1"

# 送信する画像ファイル
# 第2引数をIMAGE_NAMEに格納
IMAGE_NAME="$2"

# リモート上のコピー先のパス
REMOTE_DIRECTORY="./fig_image/"

# SSH経由で画像を転送
scp "$REMOTE_USER@$REMOTE_IP:~/work/RasPike/sdk/workspace/etrobocon2023/rear_camera_py/image_data/$IMAGE_NAME" "$REMOTE_DIRECTORY"

# スクリプトの終了
exit 0