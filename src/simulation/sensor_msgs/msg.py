# sensor_msgs/msg.py mock file
class LaserScan:
    def __init__(self):
        self.ranges = [1.0] * 360
        self.angle_min = 0.0
        self.angle_increment = 0.0174

class Image:
    def __init__(self):
        self.height = 300
        self.width = 300
        self.encoding = 'rgb8'
        self.data = b'\x00' * (300 * 300 * 3)
