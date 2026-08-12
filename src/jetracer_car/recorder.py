import cv2
from typing import Optional, Tuple


class VideoRecorder:
    def __init__(self, filename: str, frame_size: Tuple[int, int], fps: float = 20.0, fourcc: str = 'MJPG'):
        self.filename = filename
        self.frame_size = frame_size
        self.fps = fps
        self.fourcc = cv2.VideoWriter_fourcc(*fourcc)
        self.writer: Optional[cv2.VideoWriter] = None

    def start(self) -> bool:
        self.writer = cv2.VideoWriter(self.filename, self.fourcc, self.fps, self.frame_size)
        return bool(self.writer is not None and self.writer.isOpened())

    def write(self, frame: cv2.Mat) -> None:
        if self.writer is None or frame is None:
            return
        self.writer.write(frame)

    def release(self) -> None:
        if self.writer is not None:
            self.writer.release()
            self.writer = None
