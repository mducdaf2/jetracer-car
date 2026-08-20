import time
from jetracer.nvidia_racecar import NvidiaRacecar


class RacecarController:
    """
    Tầng Điều khiển Động cơ (Hardware Abstraction Layer)
    Quản lý các thao tác phần cứng của JetRacer.
    """
    def __init__(
        self,
        base_throttle=0.15,      # Mức ga chuẩn khi bám đường (0.0 -> 1.0)
        cm_per_second=30.0,       # Ước lượng tốc độ: 30cm / 1 giây
        straight_steering=0.0,    # Góc lái đi thẳng
        left_steering=-0.75,      # Góc lái rẽ trái
        right_steering=0.75       # Góc lái rẽ phải
    ):
        self.car = NvidiaRacecar()
        self.base_throttle = base_throttle
        self.cm_per_second = cm_per_second
        
        self.steering_config = {
            "STRAIGHT": straight_steering,
            "LEFT": left_steering,
            "RIGHT": right_steering
        }
        
        # Dừng xe khi khởi tạo
        self.stop()

    def set_steering(self, value):
        """Giới hạn và đặt góc lái trực tiếp (-1.0 đến 1.0)"""
        self.car.steering = max(-1.0, min(1.0, float(value)))

    def set_throttle(self, value):
        """Giới hạn và đặt mức ga trực tiếp (-1.0 đến 1.0)"""
        self.car.throttle = max(-1.0, min(1.0, float(value)))

    def stop(self):
        """Dừng xe ngay lập tức"""
        self.car.throttle = 0.0
        self.car.steering = self.steering_config["STRAIGHT"]

    def move_cm(self, distance_cm, speed_factor=1.0, steering_offset=0.0):
        """Đi tiến thẳng một khoảng cách ước tính (cm)"""
        duration = distance_cm / (self.cm_per_second * speed_factor)
        self.car.steering = self.steering_config["STRAIGHT"] + steering_offset
        self.car.throttle = self.base_throttle * speed_factor
        
        time.sleep(duration)
        self.stop()

    def turn_left(self, duration=1.2, speed_factor=1.0):
        """Thực hiện thao tác rẽ trái tại ngã 3/ngã 4"""
        self.car.steering = self.steering_config["LEFT"]
        self.car.throttle = self.base_throttle * speed_factor
        time.sleep(duration)
        self.stop()

    def turn_right(self, duration=1.2, speed_factor=1.0):
        """Thực hiện thao tác rẽ phải tại ngã 3/ngã 4"""
        self.car.steering = self.steering_config["RIGHT"]
        self.car.throttle = self.base_throttle * speed_factor
        time.sleep(duration)
        self.stop()