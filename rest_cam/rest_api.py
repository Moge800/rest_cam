import fastapi
from threading import Thread
import json
import subprocess
from logging import getLogger, StreamHandler, DEBUG
from rest_cam.img_edit import encode_image
from rest_cam.cam_ctl import Camera
import uvicorn

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.addHandler(handler)

ACTIVE_CAMERAS = {}
app = fastapi.FastAPI()
logger.info("Starting RESTful Camera Service")


@app.get("/status")
def get_status(cam_id: int = None) -> fastapi.Response:
    """カメラの状態を取得する

    Args:
        cam_id (int, optional): カメラID. Defaults to None. Noneの場合は全カメラの状態を取得

    Returns:
        fastapi.Response: カメラの状態を含むレスポンス
    """
    logger.info(f"Status requested for camera {cam_id if cam_id is not None else 'all'}")
    if cam_id is not None and cam_id in ACTIVE_CAMERAS:
        status = ACTIVE_CAMERAS[cam_id].get_status()
        return fastapi.Response(content=json.dumps(status), media_type="application/json")
    else:
        status = {cam_id: cam.get_status() for cam_id, cam in ACTIVE_CAMERAS.items()}
        return fastapi.Response(content=json.dumps(status), media_type="application/json")


@app.get("/get_image")
def get_image(cam_id: int = 0, encoding: str = "png") -> fastapi.Response:
    """カメラから最新画像を1枚取得する

    Args:
        cam_id (int, optional): カメラID. Defaults to 0.
        encoding (str, optional): エンコーディング形式. Defaults to "png".["png", "jpg", "bmp"] のいずれか

    Returns:
        fastapi.Response: 画像データを含むレスポンス
    """
    logger.info(f"Requesting image from camera {cam_id} with encoding {encoding}")
    if encoding not in ["png", "jpg", "bmp"]:
        return fastapi.Response(status_code=400, content="Invalid encoding format")
    if cam_id in ACTIVE_CAMERAS:
        camera: Camera = ACTIVE_CAMERAS[cam_id]
        image = camera.get_frame()
        ret, buf = encode_image(image, encoding)
        if not ret:
            return fastapi.Response(status_code=500, content=f"Encoding failed. {encoding} is not supported.")
        return fastapi.Response(content=buf.tobytes(), media_type=f"image/{encoding}")
    return fastapi.Response(status_code=404, content="Camera not found")


@app.get("/shutdown")
def shutdown_event(execute: bool = False) -> fastapi.Response:
    """システムシャットダウン

    Args:
        execute (bool, optional): 実際にシャットダウンを実行するかどうか. Defaults to False.

    Returns:
        fastapi.Response: シャットダウンの実行結果を含むレスポンス

    """
    logger.info(f"Shutdown requested. execute={execute}")
    if not execute:
        return fastapi.Response(content="Set execute=true to actually shutdown", media_type="text/plain")

    def shutdown():
        for cam in ACTIVE_CAMERAS.values():
            try:
                cam.release()
            except Exception:
                pass
        subprocess.run(["sudo", "shutdown", "-h", "now"])

    try:
        thread = Thread(target=shutdown, daemon=True)
        thread.start()
    except Exception as e:
        return fastapi.Response(status_code=500, content=f"Shutdown failed: {e}")

    return fastapi.Response(content="Shutdown initiated", media_type="text/plain")


@app.get("/reboot")
def reboot_event(execute: bool = False) -> fastapi.Response:
    """システム再起動

    Args:
        execute (bool, optional): 実際に再起動を実行するかどうか. Defaults to False.

    Returns:
        fastapi.Response: 再起動の実行結果を含むレスポンス

    """
    logger.info(f"Reboot requested. execute={execute}")
    if not execute:
        return fastapi.Response(content="Set execute=true to actually reboot", media_type="text/plain")

    def reboot():
        for cam in ACTIVE_CAMERAS.values():
            try:
                cam.release()
            except Exception:
                pass
        subprocess.run(["sudo", "reboot"])

    try:
        thread = Thread(target=reboot, daemon=True)
        thread.start()
    except Exception as e:
        return fastapi.Response(status_code=500, content=f"Reboot failed: {e}")

    return fastapi.Response(content="Reboot initiated", media_type="text/plain")


def main(CAMERA_IDS: list[int] = [0]):
    """カメラを初期化してAPIサーバーを起動する

    Args:
        CAMERA_IDS (list[int], optional): 使用するカメラのIDリスト. Defaults to [0].
    """

    for cam_id in CAMERA_IDS:
        ACTIVE_CAMERAS[cam_id] = Camera(cam_id)

    uvicorn.run(app, host="localhost", port=8000)
