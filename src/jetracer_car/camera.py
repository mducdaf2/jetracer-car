import cv2
import numpy as np
from typing import Any, Optional, Tuple


def decode_image(image_msg: Any) -> Optional[np.ndarray]:
    """Decode a ROS Image message into an OpenCV BGR frame."""
    try:
        if image_msg.encoding.endswith('compressed'):
            np_arr = np.frombuffer(image_msg.data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        else:
            frame = np.frombuffer(image_msg.data, dtype=np.uint8)
            frame = frame.reshape(image_msg.height, image_msg.width, -1)
            if 'rgb' in image_msg.encoding.lower():
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame
    except Exception:
        return None


def resize_frame(frame: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
    return cv2.resize(frame, size, interpolation=cv2.INTER_AREA)


def draw_debug_info(frame: np.ndarray, text: str | None = None) -> np.ndarray:
    debug_frame = frame.copy()
    if text:
        cv2.putText(
            debug_frame,
            text,
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
    return debug_frame
