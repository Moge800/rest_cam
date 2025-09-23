import cv2
import numpy as np
from threading import Thread, Lock
from logging import getLogger, StreamHandler, DEBUG

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.addHandler(handler)


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
