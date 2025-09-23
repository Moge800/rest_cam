import cv2
import numpy as np
from typing import Tuple


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
