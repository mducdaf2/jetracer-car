import simulation.rospy
import cv2
import numpy as np 

def camera_callback(image_msg):
    try:
        if image_msg.encoding.endswith('compressed'):
            np_arr = np.frombuffer(image_msg.data, np.uint8)
            cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        else:
            cv_image = np.frombuffer(image_msg.data, dtype=np.uint8).reshape(image_msg.height, image_msg.width, -1)
        if 'rgb' in image_msg.encoding: cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
        self.latest_image = cv2.resize(cv_image, (self.WIDTH, self.HEIGHT))
    except Exception as e: rospy.logerr(f"Lỗi chuyển đổi ảnh: {e}")