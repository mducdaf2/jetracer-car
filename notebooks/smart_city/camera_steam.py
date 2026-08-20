import os
import cv2
import numpy as np
import rospy
from sensor_msgs.msg import Image


class CameraStream:
    """Class hỗ trợ đăng ký ROS Topic camera, tự động decode ảnh BGR 

    và tích hợp sẵn chức năng ghi video debug.
    """

    def __init__(
        self,
        topic_name='/csi_cam_0/image_raw',
        width=500,
        height=300,
        record_video=False,
        output_path='test_car/jetracer_run.avi',
        fps=20,
    ):
        self.width = width
        self.height = height
        self.latest_image = None
        self.record_video = record_video
        self.output_path = output_path
        self.fps = fps
        self.video_writer = None

        # Tự động khởi tạo ROS Node nếu chưa được tạo ở nơi khác
        try:
            if hasattr(rospy, 'core') and not rospy.core.is_initialized():
                rospy.init_node('jetracer_camera_stream_node', anonymous=True)
            elif hasattr(rospy, 'init_node'):
                rospy.init_node('jetracer_camera_stream_node', anonymous=True)
        except Exception as e:
            print(f"Bỏ qua khởi tạo ROS Node: {e}")

        # Đăng ký Subscriber
        self.sub = rospy.Subscriber(topic_name, Image, self._camera_callback)
        rospy.loginfo(f"📷 Đã Subscribe vào Topic: {topic_name}")

        # Khởi tạo VideoWriter nếu bật record
        if self.record_video:
            self._init_video_writer()

    def _camera_callback(self, image_msg):
        """Callback tự động giải mã ảnh từ ROS Image sang OpenCV BGR Array"""
        try:
            if image_msg.encoding.endswith('compressed'):
                np_arr = np.frombuffer(image_msg.data, np.uint8)
                cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            else:
                cv_image = np.frombuffer(
                    image_msg.data, dtype=np.uint8
                ).reshape(image_msg.height, image_msg.width, -1)

            if 'rgb' in image_msg.encoding:
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)

            # Resize về kích thước thiết lập
            self.latest_image = cv2.resize(
                cv_image, (self.width, self.height)
            )

            # Tự động ghi frame nếu bật ghi video
            if self.record_video and self.video_writer is not None:
                self.video_writer.write(self.latest_image)

        except Exception as e:
            rospy.logerr(f"Lỗi giải mã ảnh ROS: {e}")

    def _init_video_writer(self):
        """Khởi tạo cv2.VideoWriter"""
        try:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            self.video_writer = cv2.VideoWriter(
                self.output_path, fourcc, self.fps, (self.width, self.height)
            )
            rospy.loginfo(f"📹 Bắt đầu ghi video tại: {self.output_path}")
        except Exception as e:
            rospy.logerr(f"Lỗi khởi tạo VideoWriter: {e}")

    def get_frame(self):
        """
        Lấy frame ảnh mới nhất dạng OpenCV BGR (NumPy Array).
        Trả về None nếu chưa nhận được frame nào từ camera.
        """
        if self.latest_image is None:
            return None
        return self.latest_image.copy()

    def release(self):
        """Đóng subscriber và lưu video (nếu có)"""
        self.sub.unregister()
        if self.video_writer is not None:
            self.video_writer.release()
            rospy.loginfo("📹 Đã đóng file video.")