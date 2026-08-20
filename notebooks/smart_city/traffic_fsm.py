import time


class TrafficFSM:

  def __init__(
      self,
      default_state='FORWARD',
      conf_threshold=0.5,
      min_consecutive_frames=3,
      state_timeout=2.0,
      min_bbox_area=900,  # Diện tích box tối thiểu (vd: 30x30 px) để loại biển xa/làn bên
      roi_x_min=0.05,  # Bỏ 15% lề trái ảnh
      roi_x_max=0.95,  # Bỏ 15% lề phải ảnh
  ):
    """FSM có thêm bộ lọc vị trí và kích thước biển báo."""
    self.STATE_STOP = 'STOP'
    self.STATE_FORWARD = 'FORWARD'
    self.STATE_TURN_LEFT = 'TURN_LEFT'
    self.STATE_TURN_RIGHT = 'TURN_RIGHT'

    self.default_state = default_state
    self.conf_threshold = conf_threshold
    self.min_consecutive_frames = min_consecutive_frames
    self.state_timeout = state_timeout

    # Cấu hình bộ lọc không gian (Spatial Filter)
    self.min_bbox_area = min_bbox_area
    self.roi_x_min = roi_x_min
    self.roi_x_max = roi_x_max

    # Tracking
    self.current_state = self.default_state
    self.last_detected_label = None
    self.consecutive_count = 0
    self.last_detection_time = time.time()

    self.class_to_state = {
        'red-light': self.STATE_STOP,
        'prohibition-sign': self.STATE_STOP,
        'green-light': self.STATE_FORWARD,
        'straight-ahead-sign': self.STATE_FORWARD,
        'left-turn-sign': self.STATE_TURN_LEFT,
        'right-turn-sign': self.STATE_TURN_RIGHT,
    }

    self.priority = {
        'red-light': 4,
        'prohibition-sign': 4,
        'green-light': 3,
        'left-turn-sign': 2,
        'right-turn-sign': 2,
        'straight-ahead-sign': 1,
    }

  def _is_valid_spatial_detection(self, det, img_w, img_h):
    """Kiểm tra biển báo có nằm trong vùng di chuyển thực tế của xe không.

    Format bbox chuẩn: [x1, y1, x2, y2] hoặc d['bbox']
    """
    if 'bbox' not in det:
      return True  # Nếu model không trả về bbox thì bỏ qua bước lọc này

    x1, y1, x2, y2 = det['bbox']
    w = x2 - x1
    h = y2 - y1
    area = w * h

    # 1. Lọc theo diện tích (quá nhỏ = ở xa hoặc làn khác)
    if area < self.min_bbox_area:
      return False

    # 2. Lọc theo ROI (Biển báo nằm quá sát mép trái/phải màn hình)
    center_x_ratio = ((x1 + x2) / 2.0) / img_w
    if not (self.roi_x_min <= center_x_ratio <= self.roi_x_max):
      return False

    return True

  def _select_best_detection(self, detections, img_w, img_h):
    """Lọc các detection hợp lệ cả về Confidence và Vị trí."""
    valid_dets = []
    for d in detections:
      if (
          d['confidence'] >= self.conf_threshold
          and d['class_name'] in self.class_to_state
      ):

        # Kiểm tra điều kiện vị trí không gian
        if self._is_valid_spatial_detection(d, img_w, img_h):
          valid_dets.append(d)

    if not valid_dets:
      return None

    # Ưu tiên: 1. Loại biển (Priority) -> 2. Biển to nhất (gần xe nhất) -> 3. Confidence
    valid_dets.sort(
        key=lambda d: (
            self.priority.get(d['class_name'], 0),
            (
                (d['bbox'][2] - d['bbox'][0]) * (d['bbox'][3] - d['bbox'][1])
                if 'bbox' in d
                else 0
            ),
            d['confidence'],
        ),
        reverse=True,
    )
    return valid_dets[0]['class_name']

  def update(self, detections, img_w=640, img_h=480):
    """Cập nhật FSM.

    Cần truyền thêm chiều rộng (img_w) và chiều cao (img_h) của ảnh.
    """
    now = time.time()
    best_label = self._select_best_detection(detections, img_w, img_h)

    if best_label is not None:
      if best_label == self.last_detected_label:
        self.consecutive_count += 1
      else:
        self.last_detected_label = best_label
        self.consecutive_count = 1

      if self.consecutive_count >= self.min_consecutive_frames:
        self.current_state = self.class_to_state[best_label]
        self.last_detection_time = now
    else:
      if now - self.last_detection_time > self.state_timeout:
        self.current_state = self.default_state
        self.last_detected_label = None
        self.consecutive_count = 0

    return self.current_state