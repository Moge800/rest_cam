import fastapi
import uvicorn
import cv2
import numpy as np
from typing import Tuple
from threading import Thread, Lock
import json
import subprocess
from logging import getLogger, StreamHandler, DEBUG

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.addHandler(handler)

ACTIVE_CAMERAS = {}
app = fastapi.FastAPI()
logger.info("Starting RESTful Camera Service")


class Camera:
    def __init__(self, camera_id=0) -> None:
        self.camera_id = camera_id
        self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap.isOpened():
            logger.error(f"Camera {self.camera_id} not accessible")
            raise ValueError(f"Camera {self.camera_id} not accessible")
        self.lock = Lock()
        self.frame = None
        self.running = True
        self.thread = Thread(target=self.capture_loop, daemon=True)
        self.thread.start()
        logger.info(f"Camera {self.camera_id} initialized and capture thread started")
        logger.debug(f"{self.get_status()}")

    def capture_loop(self) -> None:
        err_count = 0
        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                err_count += 1
                if err_count > 10:
                    logger.error(f"Camera {self.camera_id} read error exceeded limit, stopping capture")
                    self.running = False
                continue
            err_count = 0
            with self.lock:
                self.frame = frame

    def get_frame(self) -> np.ndarray:
        if not self.running:
            logger.error(f"Camera {self.camera_id} is not running")
            raise ValueError(f"Camera {self.camera_id} is not running. Please restart the camera.")
        with self.lock:
            if self.frame is None:
                logger.error(f"Camera {self.camera_id} has no frame available")
                raise ValueError(f"Camera {self.camera_id} has no frame available. Please restart the camera.")
            return self.frame.copy()

    def release(self) -> None:
        self.running = False
        if hasattr(self, "thread") and self.thread.is_alive():
            self.thread.join(timeout=1)
        if self.cap is not None:
            self.cap.release()
            logger.info(f"Camera {self.camera_id} released")

    def get_status(self) -> dict:
        with self.lock:
            return {
                "camera_id": self.camera_id,
                "is_opened": self.cap.isOpened(),
                "frame_width": self.cap.get(cv2.CAP_PROP_FRAME_WIDTH),
                "frame_height": self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
                "frame_channels": self.frame.shape[2] if self.frame is not None else 0,
                "camera_fps": self.cap.get(cv2.CAP_PROP_FPS),
                "frame_data_size": self.frame.nbytes if self.frame is not None else 0,
            }


@app.get("/status")
def get_status(cam_id: int = None) -> fastapi.Response:
    logger.info(f"Status requested for camera {cam_id if cam_id is not None else 'all'}")
    if cam_id is not None and cam_id in ACTIVE_CAMERAS:
        status = ACTIVE_CAMERAS[cam_id].get_status()
        return fastapi.Response(content=json.dumps(status), media_type="application/json")
    else:
        status = {cam_id: cam.get_status() for cam_id, cam in ACTIVE_CAMERAS.items()}
        return fastapi.Response(content=json.dumps(status), media_type="application/json")


def encode_image(image: np.ndarray, encoding: str) -> Tuple[bool, np.ndarray]:
    if encoding == "png":
        ret, buf = cv2.imencode(".png", image)
    elif encoding == "jpg":
        ret, buf = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    elif encoding == "bmp":
        ret, buf = cv2.imencode(".bmp", image)
    else:
        return False, None
    return ret, buf


@app.get("/get_image")
def get_image(cam_id: int = 0, encoding: str = "png") -> fastapi.Response:
    logger.info(f"Requesting image from camera {cam_id} with encoding {encoding}")
    if encoding not in ["png", "jpg", "bmp"]:
        return fastapi.Response(status_code=400, content="Invalid encoding format")
    if cam_id in ACTIVE_CAMERAS:
        camera = ACTIVE_CAMERAS[cam_id]
        # 最後に release しない（カメラはアプリ終了時にまとめて解放する）
        image = camera.get_frame()
        ret, buf = encode_image(image, encoding)
        if not ret:
            return fastapi.Response(status_code=500, content=f"Encoding failed. {encoding} is not supported.")
        return fastapi.Response(content=buf.tobytes(), media_type=f"image/{encoding}")
    return fastapi.Response(status_code=404, content="Camera not found")


@app.get("/shutdown")
def shutdown_event(execute: bool = False) -> fastapi.Response:
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


if __name__ == "__main__":
    ACTIVE_CAMERAS = {0: Camera(0)}  # , 1: Camera(1)}

    uvicorn.run(app, host="localhost", port=8000)
