import os
import time
import cv2
from typing import Optional

from simulation import rospy
from simulation.sensor_msgs.msg import Image
from simulation.jetracer.nvidia_racecar import NvidiaRacecar

from .camera import decode_image, draw_debug_info, resize_frame
from .drive import RacecarDriver
from .recorder import VideoRecorder


class SpeedTrackNode:
    def __init__(self) -> None:
        rospy.loginfo('Đang khởi tạo JetRacer Controller...')
        self.setup_parameters()
        self.latest_image: Optional[cv2.Mat] = None
        self.car = NvidiaRacecar()
        self.driver = RacecarDriver(self.car)
        self.video_recorder = VideoRecorder(self.VIDEO_OUTPUT_FILENAME, self.frame_size, self.VIDEO_FPS, self.VIDEO_FOURCC)

        os.makedirs(os.path.dirname(self.VIDEO_OUTPUT_FILENAME), exist_ok=True)
        self.image_subscriber = rospy.Subscriber('/csi_cam_0/image_raw', Image, self.camera_callback)
        rospy.loginfo("Đã đăng ký vào topic /csi_cam_0/image_raw.")
        rospy.loginfo('Khởi tạo hoàn tất. Sẵn sàng hoạt động.')

    def setup_parameters(self) -> None:
        self.WIDTH = 500
        self.HEIGHT = 300
        self.frame_size = (self.WIDTH, self.HEIGHT)
        self.VIDEO_OUTPUT_FILENAME = 'test_car/jetracer_run.avi'
        self.VIDEO_FPS = 20.0
        self.VIDEO_FOURCC = 'MJPG'

    def camera_callback(self, image_msg: Image) -> None:
        frame = decode_image(image_msg)
        if frame is None:
            rospy.logerr('Không thể giải mã ảnh từ camera.')
            return
        self.latest_image = resize_frame(frame, self.frame_size)

    def initialize_video_writer(self) -> None:
        if self.video_recorder.start():
            rospy.loginfo(f"Bắt đầu ghi video vào file '{self.VIDEO_OUTPUT_FILENAME}'")
        else:
            rospy.logerr('Không thể mở file video để ghi.')
            self.video_recorder = None  # type: ignore[assignment]

    def run(self) -> None:
        self.initialize_video_writer()
        rospy.loginfo('Bắt đầu vòng lặp. Đợi 3 giây...')
        time.sleep(3)
        rospy.loginfo('Hành trình bắt đầu!')
        rate = rospy.Rate(20)

        while not rospy.is_shutdown():
            if self.latest_image is None:
                rate.sleep()
                continue

            debug_frame = draw_debug_info(self.latest_image, 'Speed Track')
            cv2.imshow('Speed Track', debug_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break

            steering, throttle = self.driver.apply(self.latest_image)
            rospy.loginfo(f'Steering: {steering} - Throttle: {throttle}')
            if self.video_recorder is not None:
                self.video_recorder.write(debug_frame)
            rate.sleep()

        self.cleanup()
        cv2.destroyAllWindows()

    def cleanup(self) -> None:
        rospy.loginfo('Dừng robot và giải phóng tài nguyên...')
        self.driver.stop()
        if self.video_recorder is not None:
            self.video_recorder.release()
            rospy.loginfo('Đã lưu và đóng file video.')
        rospy.loginfo('Đã giải phóng tài nguyên. Chương trình kết thúc.')


def main() -> None:
    rospy.init_node('jetbot_controller_node', anonymous=True)
    try:
        controller = SpeedTrackNode()
        controller.run()
    except rospy.ROSInterruptException:
        rospy.loginfo('Node đã bị ngắt.')
    except Exception as exc:
        rospy.logerr(f'Lỗi không xác định: {exc}', exc_info=True)
