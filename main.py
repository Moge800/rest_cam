import fastapi
import uvicorn
import cv2
import numpy as np
from threading import Thread, Lock
import json

app = fastapi.FastAPI()


class Camera:
    def __init__(self, camera_id=0):
        self.camera_id = camera_id
        self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap.isOpened():
            raise ValueError("Camera not accessible")
        self.lock = Lock()
        self.frame = None
        self.running = True
        self.thread = Thread(target=self.capture_loop, daemon=True)
        self.thread.start()

    def capture_loop(self):
        err_count = 0
        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                err_count += 1
                if err_count > 10:
                    print("Too many errors, stopping capture.")
                    self.running = False
                continue
            err_count = 0
            with self.lock:
                self.frame = frame

    def get_frame(self) -> np.ndarray:
        if not self.running:
            raise ValueError("Camera is not running. Please restart the camera.")
        with self.lock:
            if self.frame is None:
                raise ValueError("No frame available. Please restart the camera.")
            return self.frame.copy()

    def release(self):
        self.running = False
        if hasattr(self, "thread") and self.thread.is_alive():
            self.thread.join(timeout=1)
        if self.cap is not None:
            self.cap.release()

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
def get_status(cam_id: int = None):
    if cam_id is not None and cam_id in ACTIVE_CAMERAS:
        status = ACTIVE_CAMERAS[cam_id].get_status()
        return fastapi.Response(content=json.dumps(status), media_type="application/json")
    else:
        status = {cam_id: cam.get_status() for cam_id, cam in ACTIVE_CAMERAS.items()}
        return fastapi.Response(content=json.dumps(status), media_type="application/json")


@app.get("/get_image")
def get_image(cam_id: int = 0):
    if cam_id in ACTIVE_CAMERAS:
        camera = ACTIVE_CAMERAS[cam_id]
        try:
            image_bytes = camera.get_frame()
            return fastapi.Response(content=image_bytes, media_type="image/jpeg")
        finally:
            camera.release()
    return fastapi.Response(status_code=404, content="Camera not found")


if __name__ == "__main__":
    ACTIVE_CAMERAS = {0: Camera(0), 1: Camera(1)}

    uvicorn.run(app, host="localhost", port=8000)
