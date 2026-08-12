import sys
import os
import time
import math

import rospy
import cv2
import numpy as np
from sensor_msgs.msg import LaserScan, Image
from jetracer.nvidia_racecar import NvidiaRacecar

class SpeedTrack:
    def __init__(self): 
        rospy.loginfo("Đang khởi tạo JetRacer Controller...")
        # Setup tham số 
        self.setup_parameters()
        
        # Khởi tạo xe
        self.initialize_hardware()
        
        # Khởi tạo Video Writer: lưu video quá trình chạy        
        self.video_writer = None
        self.initialize_video_writer()

        self.latest_image = None
        # rospy.Subscriber('/scan', LaserScan, self.detector.callback)
        rospy.Subscriber('/csi_cam_0/image_raw', Image, self.camera_callback)
        rospy.loginfo("Đã đăng ký vào các topic /scan và /csi_cam_0/image_raw.")
        
        rospy.loginfo("Khởi tạo hoàn tất. Sẵn sàng hoạt động.")
    
    # Setup tham số 
    def setup_parameters(self):
        # Kích thước ảnh 
        self.WIDTH, self.HEIGHT = 500, 300 
        
        # Tham số cho Lane Detector
        # ROI (Region of Interest) cho lane detection (dải gần xe, dùng để bám line)
        self.ROI_Y = int(self.HEIGHT * 0.3)
        self.ROI_H = int(self.HEIGHT * 0.4)
    
        # Camera / Video writer 
        self.VIDEO_OUTPUT_FILENAME = 'test_car/jetracer_run.avi'
        self.VIDEO_FPS = 20
        self.VIDEO_FOURCC = cv2.VideoWriter_fourcc(*'MJPG')
        
    # Khởi tạo xe 
    def initialize_hardware(self):
        """Khởi tạo JetRacer thông qua RacerController."""
        self.car = NvidiaRacecar()
        rospy.loginfo("JetRacer hardware đã được khởi tạo qua RacerController.")

    # ========== CAMERA ============
    # 1. Camera callback
    def camera_callback(self, image_msg):
        try:
            if image_msg.encoding.endswith('compressed'):
                np_arr = np.frombuffer(image_msg.data, np.uint8)
                cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            else:
                cv_image = np.frombuffer(image_msg.data, dtype=np.uint8).reshape(image_msg.height, image_msg.width, -1)
            if 'rgb' in image_msg.encoding: cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
            self.latest_image = cv2.resize(cv_image, (self.WIDTH, self.HEIGHT))
        except Exception as e: rospy.logerr(f"Lỗi chuyển đổi ảnh: {e}")

    # 2. Video writer 
    def initialize_video_writer(self):
        """Khởi tạo đối tượng VideoWriter."""
        try:
            # Kích thước video sẽ giống kích thước ảnh robot xử lý
            frame_size = (self.WIDTH, self.HEIGHT)
            self.video_writer = cv2.VideoWriter(self.VIDEO_OUTPUT_FILENAME, 
                                                self.VIDEO_FOURCC, 
                                                self.VIDEO_FPS, 
                                                frame_size)
            if self.video_writer.isOpened():
                rospy.loginfo(f"Bắt đầu ghi video vào file '{self.VIDEO_OUTPUT_FILENAME}'")
            else:
                rospy.logerr("Không thể mở file video để ghi.")
                self.video_writer = None
        except Exception as e:
            rospy.logerr(f"Lỗi khi khởi tạo VideoWriter: {e}")
            self.video_writer = None
    
    # 3. Tạo debug frame 
    def draw_debug_info(self, image):
        if image is None:
            return None
        debug_frame = image.copy()
 
        # cv2.rectangle(debug_frame, (0, self.ROI_Y),
        #                (self.WIDTH - 1, self.ROI_Y + self.ROI_H), (0, 255, 0), 1)
 
        # # cv2.putText(debug_frame, state_text, (10, 20),
        # #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
 
        
        # target = self.lane_target
        # if target is not None:
        #     offset_px, cy = target
        #     cx = int(self.WIDTH / 2 + offset_px)
        #     cv2.line(debug_frame, (cx, self.ROI_Y), (cx, self.ROI_Y + self.ROI_H), (0, 0, 255), 2)
 
        return debug_frame
        
    # 4. Lưu thông tin debug vào video
    def _record_frame(self):
        """Hàm trợ giúp để vẽ thông tin và ghi một khung hình vào video."""
        if self.video_writer is not None and self.latest_image is not None:
            debug_frame = self.draw_debug_info(self.latest_image)
            if debug_frame is not None:
                self.video_writer.write(debug_frame)

    # ========== HÀM LOOP CHÍNH ============
    def run(self):
        rospy.loginfo("Bắt đầu vòng lặp. Đợi 3 giây...") 
        time.sleep(3) 
        rospy.loginfo("Hành trình bắt đầu!")
        rate = rospy.Rate(20)

        while not rospy.is_shutdown():
            if self.latest_image is not None:
                # Show hình ảnh
                # cv2.imshow('Speed Track', self.latest_image)
                key = cv2.waitKey(1) & 0xFF
                if key == 27: # Kill bằng ESC
                    break
                
                self.car.throttle = 0.
                
                
            self._record_frame()
            rate.sleep()
        self.cleanup()
        cv2.destroyAllWindows()
        
    # ========== utils function ============
    # 1. Cleanup bộ nhớ của xé
    def cleanup(self):
        rospy.loginfo("Dừng robot và giải phóng tài nguyên...")
        if hasattr(self, 'car') and self.car is not None:
            self.car.throttle = 0 
            self.car.steering = 0 
            rospy.loginfo("Đã lưu và đóng file video.")

        if hasattr(self, 'video_writer') and self.video_writer is not None:
            self.video_writer.release()
            rospy.loginfo("Đã lưu và đóng file video.")
            
        rospy.loginfo("Đã giải phóng tài nguyên. Chương trình kết thúc.")


def main():
    rospy.init_node('jetbot_controller_node', anonymous=True)
    try:
        controller = SpeedTrack()
        controller.run()
    except rospy.ROSInterruptException: rospy.loginfo("Node đã bị ngắt.")
    except Exception as e: rospy.logerr(f"Lỗi không xác định: {e}", exc_info=True)
    

if __name__ == '__main__':
    main()