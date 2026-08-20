# rospy.py mock file
from networkx import exception
import time
import threading
import numpy as np
import cv2

# Monkey-patch cv2.findContours to be backward compatible (always return 3 values)
# OpenCV 4.x returns (contours, hierarchy), OpenCV 3.x returns (image, contours, hierarchy)
old_findContours = cv2.findContours
def mock_findContours(*args, **kwargs):
    res = old_findContours(*args, **kwargs)
    if len(res) == 2:
        return None, res[0], res[1]
    return res
cv2.findContours = mock_findContours

def loginfo(msg, *args, **kwargs):
    print(f"[INFO] {msg}")

def logwarn(msg, *args, **kwargs):
    print(f"[WARN] {msg}")

def logerr(msg, *args, **kwargs):
    print(f"[ERROR] {msg}")

_last_logged = {}

def _throttle(sec, msg, level, *args, **kwargs):
    now = time.time()
    key = (msg, level)
    if key not in _last_logged or now - _last_logged[key] >= sec:
        _last_logged[key] = now
        print(f"[{level}] {msg}")

def loginfo_throttle(sec, msg, *args, **kwargs):
    _throttle(sec, msg, "INFO", *args, **kwargs)

def logwarn_throttle(sec, msg, *args, **kwargs):
    _throttle(sec, msg, "WARN", *args, **kwargs)

def logerr_throttle(sec, msg, *args, **kwargs):
    _throttle(sec, msg, "ERROR", *args, **kwargs)

def get_time():
    return time.time()

_shutdown = False
def is_shutdown():
    return _shutdown

latest_frame = None
frame_lock = threading.Lock()

def camera_callback(self, image_msg):
    print("camera_callback", image_msg.width, image_msg.height)


from multiprocessing import shared_memory
import struct

SHM_NAME = "donkey_camera"
HEADER_SIZE = 16

_publish_shm = None

def publish_image(img):
    global _publish_shm
    h, w, c = img.shape
    size = HEADER_SIZE + img.nbytes

    if _publish_shm is None:
        try:
            _publish_shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=size)
        except FileExistsError:
            _publish_shm = shared_memory.SharedMemory(name=SHM_NAME)

    try:
        buf = _publish_shm.buf
        struct.pack_into("IIII", buf, 0, h, w, c, img.dtype.itemsize)
        buf[HEADER_SIZE:HEADER_SIZE + img.nbytes] = img.tobytes()
    except Exception:
        try:
            _publish_shm.close()
        except Exception:
            pass
        _publish_shm = None


class Rate:
    def __init__(self, hz):
        self.sleep_time = 1.0/hz
    def sleep(self):
        time.sleep(self.sleep_time)

class MockImageMsg:
    def __init__(self):
        self.height = 300
        self.width = 300
        self.encoding = 'rgb8'
        self.data = b''

class Subscriber:
    def __init__(self, topic, msg_type, callback):
        self.topic = topic
        self.callback = callback
        if topic == '/csi_cam_0/image_raw':
            self.thread = threading.Thread(target=self._feed_images, daemon=True)
            self.thread.start()

    def _feed_images(self):
        shm = None
        while not _shutdown:
            try:
                if shm is None:
                    shm = shared_memory.SharedMemory(name="donkey_camera")

                h, w, c, itemsize = struct.unpack_from("IIII", shm.buf, 0)
                if h <= 0 or w <= 0 or c <= 0 or itemsize <= 0:
                    time.sleep(0.1)
                    continue

                nbytes = h * w * c * itemsize
                frame = np.ndarray(
                    (h, w, c),
                    dtype=np.uint8,
                    buffer=shm.buf[16:16+nbytes]
                ).copy()

                msg = MockImageMsg()
                msg.height = h
                msg.width = w
                msg.encoding = "rgb8"
                msg.data = frame.tobytes()

                self.callback(msg)
            except FileNotFoundError:
                time.sleep(0.1)
            except Exception as e:
                if shm is not None:
                    try:
                        shm.close()
                    except Exception:
                        pass
                    shm = None
                time.sleep(0.1)

            time.sleep(0.02)

def init_node(name, anonymous=False):
    print(f"ROS Node initialized: {name}")

class ROSInterruptException(Exception):
    pass

SHM_CONTROL_NAME = "donkey_control"
_control_pub_shm = None
_control_sub_shm = None

def publish_control(steering, throttle):
    global _control_pub_shm
    if _control_pub_shm is None:
        try:
            _control_pub_shm = shared_memory.SharedMemory(name=SHM_CONTROL_NAME, create=True, size=16)
        except FileExistsError:
            _control_pub_shm = shared_memory.SharedMemory(name=SHM_CONTROL_NAME)
    try:
        struct.pack_into("ff", _control_pub_shm.buf, 0, float(steering), float(throttle))
    except Exception:
        try:
            _control_pub_shm.close()
        except Exception:
            pass
        _control_pub_shm = None

def read_control():
    global _control_sub_shm
    if _control_sub_shm is None:
        try:
            _control_sub_shm = shared_memory.SharedMemory(name=SHM_CONTROL_NAME)
        except FileNotFoundError:
            return 0.0, 0.0
        except Exception:
            return 0.0, 0.0
    try:
        steering, throttle = struct.unpack_from("ff", _control_sub_shm.buf, 0)
        return steering, throttle
    except Exception:
        try:
            _control_sub_shm.close()
        except Exception:
            pass
        _control_sub_shm = None
        return 0.0, 0.0

# --- Bổ sung thêm vào cuối file rospy.py mock ---
class _MockCore:
    def is_initialized(self):
        return True  # Luôn trả về True để bỏ qua bước init_node thật khi mock

core = _MockCore()