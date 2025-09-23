# REST Camera Service

Webカメラへの RESTful API アクセスを提供する Python サービスです。FastAPI を使用してカメラの映像取得、ステータス確認、システム制御などの機能を提供します。

## 機能

- **カメラ画像取得**: PNG、JPG、BMP形式での画像取得
- **カメラステータス**: カメラの状態、解像度、FPS などの情報取得
- **リアルタイム処理**: バックグラウンドでの連続フレーム取得
- **システム制御**: シャットダウン・再起動機能
- **Web UI**: FastAPI の自動生成ドキュメント

## 必要な環境

- Python 3.7+
- Webカメラ（USB カメラまたは仮想カメラ）
- Windows 10/11、Linux、macOS 対応

## インストール

1. リポジトリをクローン:

   ```bash
   git clone https://github.com/Moge800/rest_cam.git
   cd rest_cam
   ```

2. 仮想環境を作成・有効化:

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

3. 必要なパッケージをインストール:

   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

### サーバー起動

```bash
python main.py
```

サーバーは `http://localhost:8000` で起動します。

### API ドキュメント

ブラウザで `http://localhost:8000/docs` にアクセスすると、対話的な API ドキュメントを確認できます。

## プロジェクト構造

```text
rest_cam/
├── main.py                 # エントリーポイント（開発用）
├── requirements.txt        # 依存パッケージリスト
├── README.md              # このファイル
├── LICENSE                # MITライセンス
├── rest_cam/              # メインパッケージ
│   ├── __init__.py
│   ├── rest_api.py        # FastAPI アプリケーション定義
│   ├── cam_ctl.py         # カメラ制御クラス
│   └── img_edit.py        # 画像エンコーディング機能
└── .venv/                 # Python仮想環境
```

## API エンドポイント

### 画像取得

```http
GET /get_image?cam_id=0&encoding=png
```

**パラメータ:**

- `cam_id` (int): カメラID（デフォルト: 0）
- `encoding` (str): 画像フォーマット（png, jpg, bmp）

**レスポンス:** 画像データ（バイナリ）

### ステータス取得

```http
GET /status?cam_id=1
```

**パラメータ:**

- `cam_id` (int, オプション): 特定のカメラID

**レスポンス例:**

```json
{
  "camera_id": 0,
  "is_opened": true,
  "frame_width": 1920.0,
  "frame_height": 1080.0,
  "frame_channels": 3,
  "camera_fps": 30.0,
  "frame_data_size": 6220800
}
```

### システム制御

**シャットダウン:**

```http
GET /shutdown?execute=true
```

**再起動:**

```http
GET /reboot?execute=true
```

## 使用例

### cURL を使用した例

**画像取得:**

```bash
# PNG形式で画像を取得してファイルに保存
curl "http://localhost:8000/get_image?cam_id=0&encoding=png" -o image.png

# JPEG形式で画像を取得
curl "http://localhost:8000/get_image?cam_id=0&encoding=jpg" -o image.jpg
```

**ステータス確認:**

```bash
# 全カメラのステータス取得
curl "http://localhost:8000/status"

# 特定のカメラのステータス取得
curl "http://localhost:8000/status?cam_id=0"
```

### Python を使用した例

```python
import requests
from PIL import Image
import io

# カメラから画像を取得
response = requests.get("http://localhost:8000/get_image?cam_id=0&encoding=png")
if response.status_code == 200:
    # PILで画像を開く
    image = Image.open(io.BytesIO(response.content))
    image.show()
    # ファイルに保存
    image.save("captured_image.png")

# ステータス取得
status_response = requests.get("http://localhost:8000/status?cam_id=0")
status = status_response.json()
print(f"Camera resolution: {status['frame_width']}x{status['frame_height']}")
print(f"FPS: {status['camera_fps']}")
```

## アーキテクチャ

- **Camera クラス**: 個別のカメラを管理（フレーム取得、状態管理）
- **バックグラウンドスレッド**: 連続的なフレーム取得
- **スレッドセーフ**: Lock を使用した安全なフレームアクセス
- **エラーハンドリング**: カメラアクセスエラーの自動復旧

## 開発

### プロジェクト構成

- `rest_cam/rest_api.py`: FastAPI アプリケーションとエンドポイント定義
- `rest_cam/cam_ctl.py`: `Camera` クラスによるカメラ制御
- `rest_cam/img_edit.py`: 画像エンコーディング機能
- `main.py`: 開発用のエントリーポイント

### カメラの追加

`main.py` またはアプリケーション起動時にカメラを追加できます：

```python
from rest_cam.rest_api import ACTIVE_CAMERAS, app
from rest_cam.cam_ctl import Camera

# カメラを追加
ACTIVE_CAMERAS.update({
    0: Camera(0),  # 1台目のカメラ
    1: Camera(1),  # 2台目のカメラ
})

# サーバー起動
import uvicorn
uvicorn.run(app, host="localhost", port=8000)
```

### ログ設定

ログレベルは `DEBUG` に設定されており、詳細な動作ログが出力されます。

## トラブルシューティング

### カメラが認識されない

- カメラが他のアプリケーションで使用されていないか確認
- USB接続を確認
- カメラドライバーが正しくインストールされているか確認

### システム制御について

**注意**: シャットダウン・再起動機能は Linux 環境でのみ動作します。Windows 環境では管理者権限や代替コマンドが必要です。

### VCAMDS ログについて

ログに表示される `[VCAMDS]` は仮想カメラ（Virtual Camera DirectShow）からの出力です。OBS Studio や ManyCam などの仮想カメラソフトウェアが動作している場合に表示されます。

### パフォーマンス

- 高解像度での連続取得はCPU使用率が高くなる場合があります
- 必要に応じて画像サイズやフレームレートを調整してください

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 貢献

バグ報告や機能改善の提案は、GitHub の Issues でお願いします。
