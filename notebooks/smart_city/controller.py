import time
import atexit
import logging

try:
    from jetracer.nvidia_racecar import NvidiaRacecar
except ImportError:
    NvidiaRacecar = None  # cho phép import/test code này trên máy không phải Jetson

logger = logging.getLogger("RacecarController")


class RacecarController:
    """
    Tầng Điều khiển Động cơ (Hardware Abstraction Layer)
    Quản lý các thao tác phần cứng của JetRacer (Jetson Nano).
    """

    def __init__(
        self,
        base_throttle=0.15,     # Mức ga chuẩn khi bám đường (0.0 -> 1.0)
        cm_per_second=30.0,     # Ước lượng tốc độ: 30cm / 1 giây
        straight_steering=0.0,  # Góc lái đi thẳng
        left_steering=-1.0,     # Góc lái rẽ trái
        right_steering=1.0,     # Góc lái rẽ phải
        max_throttle=0.5,       # Trần an toàn tuyệt đối cho throttle, bất kể speed_factor
        # Cấu hình cho thao tác "rẽ 90 độ tại chỗ" kiểu 2 pha:
        # Pha 1: tiến + bẻ lái theo hướng muốn rẽ
        # Pha 2: lùi  + bẻ lái NGƯỢC hướng (vẫn tiếp tục xoay cùng chiều, nhưng lùi lại
        #         để triệt tiêu bớt độ dịch chuyển tịnh tiến -> xoay gần tại chỗ hơn)
        # Các giá trị này BẮT BUỘC phải tự hiệu chỉnh bằng calibrate_turn_90()
        # vì phụ thuộc xe, mặt sàn, mức pin của từng người.
        turn90_forward_duration_left=3,
        turn90_reverse_duration_left=3,
        turn90_forward_duration_right=3,
        turn90_reverse_duration_right=3,
        # Thời gian dừng (throttle=0) giữa pha tiến và pha lùi, để ESC kịp
        # nhận lệnh đảo chiều. Nếu xe không chịu lùi, thử tăng giá trị này lên.
        pause_between_phases=0.15,
        # "Kick-start": bắn ga cao hơn trong một khoảng ngắn ở đầu mỗi pha để
        # thắng ma sát tĩnh. LƯU Ý: xe xuất phát từ trạng thái ĐỨNG YÊN HOÀN
        # TOÀN nên ma sát tĩnh cao hơn nhiều so với lúc đang lăn — nếu kick
        # quá ngắn, bánh chỉ vừa nhích đã bị cắt ga. Giá trị dưới đây chỉ là
        # điểm khởi đầu, BẮT BUỘC phải tự test lại bằng diagnose_motor.py.
        kick_throttle=0.5,
        kick_duration=0.2,
    ):
        if NvidiaRacecar is None:
            raise RuntimeError(
                "Không tìm thấy thư viện jetracer. Hãy chạy code này trên Jetson Nano "
                "đã cài đặt JetRacer, hoặc mock NvidiaRacecar khi test trên máy khác."
            )

        self.car = NvidiaRacecar()
        self.base_throttle = self._clamp(base_throttle, -1.0, 1.0)
        self.cm_per_second = max(float(cm_per_second), 1e-6)  # tránh chia cho 0
        self.max_throttle = self._clamp(max_throttle, 0.0, 1.0)

        self.steering_config = {
            "STRAIGHT": self._clamp(straight_steering, -1.0, 1.0),
            "LEFT": self._clamp(left_steering, -1.0, 1.0),
            "RIGHT": self._clamp(right_steering, -1.0, 1.0),
        }

        self.turn90_config = {
            "LEFT": {
                "forward": max(0.0, float(turn90_forward_duration_left)),
                "reverse": max(0.0, float(turn90_reverse_duration_left)),
            },
            "RIGHT": {
                "forward": max(0.0, float(turn90_forward_duration_right)),
                "reverse": max(0.0, float(turn90_reverse_duration_right)),
            },
        }
        self.pause_between_phases = max(0.0, float(pause_between_phases))
        self.kick_throttle = self._clamp(kick_throttle, 0.0, 1.0)
        self.kick_duration = max(0.0, float(kick_duration))

        self.stop()
        # Bất kể chương trình kết thúc kiểu gì (bình thường, exception, Ctrl+C),
        # luôn cố gắng dừng xe trước khi thoát.
        atexit.register(self.stop)

    # --- Cho phép dùng: with RacecarController() as car: ... ---
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False  # không nuốt exception, để lỗi vẫn hiện ra ngoài

    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass

    @staticmethod
    def _clamp(value, lo, hi):
        return max(lo, min(hi, float(value)))

    def _safe_throttle(self, value):
        """Giới hạn throttle trong [-max_throttle, max_throttle]."""
        return self._clamp(value, -self.max_throttle, self.max_throttle)

    def set_steering(self, value):
        """Giới hạn và đặt góc lái trực tiếp (-1.0 đến 1.0)"""
        self.car.steering = self._clamp(value, -1.0, 1.0)

    def set_throttle(self, value):
        """Giới hạn và đặt mức ga trực tiếp, không vượt quá max_throttle"""
        self.car.throttle = self._safe_throttle(value)

    def stop(self):
        """Dừng xe ngay lập tức"""
        self.car.throttle = 0.0
        self.car.steering = self.steering_config["STRAIGHT"]

    def _run_timed(self, steering, throttle, duration, kick_throttle=0.0, kick_duration=0.0):
        """
        Chạy xe với góc lái/ga cho trước trong `duration` giây.
        Dùng try/finally để đảm bảo xe LUÔN được dừng, kể cả khi
        sleep() bị ngắt giữa chừng (Ctrl+C, lỗi cảm biến, exception khác...).
        Đây là điểm khác biệt an toàn quan trọng nhất so với bản gốc.

        Nếu kick_duration > 0: trong `kick_duration` giây đầu tiên, ga sẽ
        được bắn lên mức kick_throttle (cùng dấu với `throttle`) để thắng
        ma sát tĩnh, sau đó mới hạ về mức `throttle` cho phần thời gian
        còn lại. Hữu ích khi base_throttle quá thấp khiến xe chỉ rung bánh
        mà gần như không di chuyển.
        """
        if duration < 0:
            raise ValueError("duration phải >= 0")

        self.car.steering = self._clamp(steering, -1.0, 1.0)

        kick_duration = min(max(0.0, kick_duration), duration)
        try:
            if kick_duration > 0 and kick_throttle:
                kick_signed = kick_throttle if throttle >= 0 else -abs(kick_throttle)
                self.car.throttle = self._safe_throttle(kick_signed)
                time.sleep(kick_duration)

            self.car.throttle = self._safe_throttle(throttle)
            time.sleep(duration - kick_duration)
        finally:
            self.stop()

    def move_cm(self, distance_cm, speed_factor=1.0, steering_offset=0.0):
        """
        Đi một khoảng cách ước tính (cm).
        distance_cm > 0: đi tiến, distance_cm < 0: lùi.
        """
        speed_factor = self._clamp(speed_factor, 0.05, 1.0)
        duration = abs(distance_cm) / (self.cm_per_second * speed_factor)
        steering = self.steering_config["STRAIGHT"] + steering_offset
        throttle = self.base_throttle * speed_factor
        if distance_cm < 0:
            throttle = -throttle
        self._run_timed(steering, throttle, duration)

    def turn(self, direction, duration=1.2, speed_factor=1.0):
        """
        Thực hiện thao tác rẽ tại ngã 3/ngã 4.
        direction: "LEFT" hoặc "RIGHT"
        """
        direction = direction.upper()
        if direction not in ("LEFT", "RIGHT"):
            raise ValueError('direction phải là "LEFT" hoặc "RIGHT"')

        speed_factor = self._clamp(speed_factor, 0.05, 1.0)
        steering = self.steering_config[direction]
        throttle = self.base_throttle * speed_factor
        self._run_timed(steering, throttle, duration)

    # Giữ API cũ để không phải sửa code đang gọi turn_left/turn_right ở nơi khác
    def turn_left(self, duration=1.2, speed_factor=1.0):
        """Thực hiện thao tác rẽ trái tại ngã 3/ngã 4"""
        self.turn("LEFT", duration, speed_factor)

    def turn_right(self, duration=1.2, speed_factor=1.0):
        """Thực hiện thao tác rẽ phải tại ngã 3/ngã 4"""
        self.turn("RIGHT", duration, speed_factor)

    # ------------------------------------------------------------------
    # RẼ 90 ĐỘ TẠI CHỖ
    # ------------------------------------------------------------------
    # LƯU Ý QUAN TRỌNG:
    # JetRacer dùng hệ lái Ackermann (chỉ bánh trước xoay), khác với robot
    # bánh vi sai (differential drive) hay xe tank. Vì vậy xe KHÔNG THỂ xoay
    # tại chỗ tuyệt đối 0 bán kính — nó buộc phải nhích tới một chút trong
    # lúc đổi hướng. Đây là giới hạn vật lý, không phải lỗi code.
    #
    # Không có IMU/gyro nên không thể biết chính xác xe đã quay bao nhiêu độ.
    # Giải pháp thực tế: bẻ lái hết cỡ (bán kính quay nhỏ nhất có thể) + chạy
    # ga thấp trong một khoảng thời gian đã HIỆU CHỈNH TRƯỚC bằng mắt, sao
    # cho khoảng thời gian đó tương ứng với ~90 độ trên chính chiếc xe của bạn.
    # ------------------------------------------------------------------

    def turn_90(self, direction, speed_factor=0.6, forward_duration=None, reverse_duration=None):
        """
        Rẽ 90 độ tại chỗ kiểu 2 pha (giống động tác quay đầu trong ngõ hẹp):

            Pha 1: TIẾN + bẻ lái theo `direction`
            Pha 2: LÙI  + bẻ lái NGƯỢC lại `direction`

        Về mặt động học, khi lùi mà bẻ lái ngược hướng so với lúc tiến, xe
        vẫn xoay TIẾP TỤC CÙNG MỘT CHIỀU (vì cả dấu vận tốc lẫn dấu góc lái
        đều đảo, nhân lại triệt tiêu nhau), nhưng vì đang lùi nên phần dịch
        chuyển tịnh tiến của pha 2 sẽ kéo xe ngược lại pha 1 -> tổng quãng
        đường xe bị xê dịch nhỏ hơn nhiều so với chỉ rẽ khi tiến liên tục.

        direction: "LEFT" hoặc "RIGHT" — hướng muốn xe xoay tới.
        forward_duration / reverse_duration: nếu để None sẽ dùng giá trị
        đã hiệu chỉnh sẵn trong self.turn90_config.
        """
        direction = direction.upper()
        if direction not in ("LEFT", "RIGHT"):
            raise ValueError('direction phải là "LEFT" hoặc "RIGHT"')
        opposite = "RIGHT" if direction == "LEFT" else "LEFT"

        cfg = self.turn90_config[direction]
        fwd_duration = cfg["forward"] if forward_duration is None else max(0.0, forward_duration)
        rev_duration = cfg["reverse"] if reverse_duration is None else max(0.0, reverse_duration)
        speed_factor = self._clamp(speed_factor, 0.05, 1.0)
        throttle = self.base_throttle * speed_factor

        # Pha 1: tiến + bẻ lái theo direction (có kick-start để thắng ma sát tĩnh)
        self._run_timed(
            self.steering_config[direction], throttle, fwd_duration,
            kick_throttle=self.kick_throttle, kick_duration=self.kick_duration,
        )

        # Dừng ngắn giữa 2 pha để ESC kịp nhận lệnh đảo chiều
        if self.pause_between_phases > 0:
            time.sleep(self.pause_between_phases)

        # Pha 2: lùi + bẻ lái ngược lại direction (cũng cần kick-start vì
        # lùi từ trạng thái đứng yên thường cần lực khởi động lớn hơn cả lúc tiến)
        self._run_timed(
            self.steering_config[opposite], -throttle, rev_duration,
            kick_throttle=self.kick_throttle, kick_duration=self.kick_duration,
        )

    def turn_90_left(self, speed_factor=0.6):
        """Rẽ trái 90 độ tại chỗ: tiến-rẽ trái, rồi lùi-rẽ phải."""
        self.turn_90("LEFT", speed_factor)

    def turn_90_right(self, speed_factor=0.6):
        """Rẽ phải 90 độ tại chỗ: tiến-rẽ phải, rồi lùi-rẽ trái."""
        self.turn_90("RIGHT", speed_factor)

    def calibrate_turn_90(self, direction, forward_duration, reverse_duration, speed_factor=0.6):
        """
        Hàm hỗ trợ hiệu chỉnh maneuver 2 pha. Chạy thử với forward_duration /
        reverse_duration cho trước, rồi tự quan sát bằng mắt:

          - Nếu tổng góc quay CHƯA đủ 90 độ -> tăng forward_duration
            và/hoặc reverse_duration rồi thử lại.
          - Nếu quay QUÁ 90 độ -> giảm xuống.
          - Nếu xe bị trôi/dịch quá nhiều về phía trước hoặc phía sau ->
            tăng reverse_duration (hoặc giảm forward_duration) để 2 pha
            cân bằng nhau hơn, giữ xe gần vị trí ban đầu.
          - Nếu bánh chỉ rung nhẹ, xe gần như không di chuyển (chỉ 1-2cm) ->
            tăng self.kick_throttle (VD 0.4 -> 0.55) hoặc self.kick_duration
            (VD 0.08 -> 0.12) để có đủ lực thắng ma sát tĩnh lúc khởi động.
            Cũng có thể base_throttle đang quá thấp, thử tăng base_throttle
            hoặc dùng speed_factor cao hơn khi test.

        Khi tìm được cặp giá trị đúng, gán vào các tham số
        turn90_forward_duration_left/right, turn90_reverse_duration_left/right
        lúc khởi tạo RacecarController, hoặc gán thẳng vào self.turn90_config.

        Ví dụ:
            car = RacecarController()
            car.calibrate_turn_90("LEFT", forward_duration=0.3, reverse_duration=0.3)
            # quan sát -> chưa đủ 90 độ, xe hơi lệch về phía trước
            car.calibrate_turn_90("LEFT", forward_duration=0.25, reverse_duration=0.35)
            # quan sát -> đủ 90 độ, gần tại chỗ -> chốt
            car.turn90_config["LEFT"] = {"forward": 0.25, "reverse": 0.35}
        """
        direction = direction.upper()
        if direction not in ("LEFT", "RIGHT"):
            raise ValueError('direction phải là "LEFT" hoặc "RIGHT"')

        logger.info(
            "Test rẽ 90 độ %s: tiến %.2fs, lùi %.2fs (speed_factor=%.2f) — hãy quan sát",
            direction, forward_duration, reverse_duration, speed_factor,
        )
        self.turn_90(
            direction,
            speed_factor=speed_factor,
            forward_duration=forward_duration,
            reverse_duration=reverse_duration,
        )


if __name__ == "__main__":
    # Ví dụ sử dụng an toàn với context manager:
    # with RacecarController(base_throttle=0.15) as car:
    #     car.move_cm(50)
    #     car.turn_90_left()          # rẽ trái 90 độ tại chỗ (ước lượng)
    #     car.move_cm(30)
    #     car.turn_90_right()

    # Ví dụ quy trình hiệu chỉnh turn_90 kiểu 2 pha (chạy riêng, tách khỏi logic chính):
    # with RacecarController() as car:
    #     car.calibrate_turn_90("LEFT", forward_duration=0.3, reverse_duration=0.3)
    #     # -> quan sát góc quay + độ dịch chuyển, chỉnh 2 giá trị, thử lại
    #     # -> sau đó chốt: RacecarController(
    #     #        turn90_forward_duration_left=<giá trị đúng>,
    #     #        turn90_reverse_duration_left=<giá trị đúng>,
    #     #    )
    pass