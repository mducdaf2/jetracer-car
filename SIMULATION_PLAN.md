# 🚀 Kế Hoạch Simulation - JetRacer Smart City & Speed Track

## 📋 Tổng Quan
- **Task 1**: Speed Track - Xe chạy nhanh trên đường thẳng
- **Task 2**: Smart City - Xe chạy tự động: tám làn + nhận diện biển báo
- **Mục tiêu**: Test thuật toán trước khi chạy trên xe thật

---

## 🏗️ Architecture Simulation

```
┌─────────────────────────────────────────────────────────┐
│                    ROS Simulation                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐         ┌──────────────────┐     │
│  │ Vision Simulator │         │ Robot Simulator  │     │
│  ├──────────────────┤         ├──────────────────┤     │
│  │ • Lane Detection │         │ • Serial Mock    │     │
│  │ • Sign Detection │         │ • Odometry Calc  │     │
│  │ • Synthetic IMG  │         │ • Motor Control  │     │
│  └────────┬─────────┘         └────────┬─────────┘     │
│           │                            │                │
│           └──────────┬─────────────────┘                │
│                      │                                  │
│           ┌──────────▼──────────┐                       │
│           │  Control Algorithm  │                       │
│           ├─────────────────────┤                       │
│           │ • Lane Following    │                       │
│           │ • Sign Response     │                       │
│           │ • Path Planning     │                       │
│           │ • Speed Control     │                       │
│           └─────────────────────┘                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Cấu Trúc Folder Cần Tạo

```
simulation/
├── nodes/
│   ├── lane_detector.py         # Nhận diện làn từ ảnh (+ OpenCV window)
│   ├── sign_detector.py         # Nhận diện biển báo (+ OpenCV window)
│   ├── robot_controller.py      # Logic điều khiển chính
│   └── odometry_publisher.py    # Publish odometry giả + TF
│
├── simulators/
│   ├── vision_simulator.py      # Tạo ảnh test giả (publish /csi_cam_0/image_raw)
│   ├── serial_mock.py           # Mock cổng Serial
│   └── vehicle_physics.py       # Mô phỏng vật lý xe
│
├── utils/
│   ├── image_generator.py       # Tạo ảnh đường/biển báo
│   ├── ros_helpers.py           # Helper functions
│   ├── visualization.py         # RViz marker helpers
│   └── config.py                # Cấu hình chung (PID, thresholds)
│
├── launch/
│   ├── simulation_speed_track.launch   # + RViz
│   └── simulation_smart_city.launch    # + RViz + OpenCV windows
│
├── rviz/
│   ├── sim_speed_track.rviz     # RViz config cho Speed Track
│   └── sim_smart_city.rviz      # RViz config cho Smart City (có visualization)
│
├── config/
│   ├── simulation_params.yaml   # Cấu hình PID, thresholds, v.v
│   └── vehicle_config.yaml      # Cấu hình xe (size, weight, v.v)
│
├── tests/
│   ├── test_lane_detection.py
│   ├── test_sign_detection.py
│   └── test_controller.py
│
└── data/
    ├── test_images/             # Ảnh test (lane, signs)
    └── rosbag/                  # Lưu recorded bags

```

---

## 🔧 Chi Tiết Các Thành Phần

### 1️⃣ **Vision Simulator** 
**File**: `simulators/vision_simulator.py`

**Chức năng**:
- Tạo ảnh làn đường (lane lines) giả
- Tạo ảnh biển báo (sign) giả
- Publish lên topic `/csi_cam_0/image_raw`

**Input/Output**:
```
Input:  robot_state (vị trí, góc quay)
Output: sensor_msgs/Image → `/csi_cam_0/image_raw`
```

**Ảnh sinh tạo**:
- Làn đường: 2-4 đường trắng trên nền xám
- Biển báo: Hình ảnh chuẩn (STOP, TURN_LEFT, TURN_RIGHT, SPEED_UP)

---

### 2️⃣ **Lane Detection Node**
**File**: `nodes/lane_detector.py`

**Chức năng**:
- Subscribe: `/csi_cam_0/image_raw`
- Detect: Vị trí làn trái/phải
- Publish: `/lane_info` (custom msg hoặc Float32)
  - Lane offset: -1.0 (quá trái) → 0.0 (giữa) → 1.0 (quá phải)

**Algorithm**:
```python
1. Canny Edge Detection
2. Hough Line Transform
3. Filter đường trắng
4. Calculate offset từ center
```

---

### 3️⃣ **Sign Detection Node**
**File**: `nodes/sign_detector.py`

**Chức năng**:
- Subscribe: `/csi_cam_0/image_raw`
- Detect: Loại biển báo + confidence
- Publish: `/sign_detected` (std_msgs/String hoặc Int32)

**Biển báo cần detect**:
```
STOP        (code: 0)  → Dừng 2 giây
SPEED_UP    (code: 1)  → Tăng tốc độ
SPEED_DOWN  (code: 2)  → Giảm tốc độ
TURN_LEFT   (code: 3)  → Rẽ trái
TURN_RIGHT  (code: 4)  → Rẽ phải
```

---

### 4️⃣ **Robot Controller Node**
**File**: `nodes/robot_controller.py`

**Chức năng**:
- Subscribe: `/lane_info`, `/sign_detected`
- Control logic: Tính toán cmd_vel
- Publish: `/cmd_vel` (geometry_msgs/Twist)

**Thuật toán**:
```python
# Lane Following (PID)
steering_error = lane_offset
steering_command = PID(steering_error)  # Tính góc quay

# Speed Control
if sign == STOP:
    speed = 0
elif sign == SPEED_UP:
    speed = 1.0
elif sign == SPEED_DOWN:
    speed = 0.3
else:
    speed = 0.5

# Publish Twist
cmd_vel.linear.x = speed
cmd_vel.angular.z = steering_command
```

---

### 5️⃣ **Serial Mock**
**File**: `simulators/serial_mock.py`

**Chức năng**:
- Mock file `/dev/ttyUSB0` (hoặc port khác)
- Nhận lệnh điều khiển từ `jetracer.cpp`
- Trả về dữ liệu odometry/IMU giả

**Format**:
```
Send:    [0xAA 0x55 type data checksum]  ← từ jetracer.cpp
Receive: [odometry_x odometry_y yaw]     ← trả về
```

---

### 6️⃣ **Odometry Publisher**
**File**: `nodes/odometry_publisher.py`

**Chức năng**:
- Simulate vị trí xe dựa trên cmd_vel
- Publish: `/odom` (nav_msgs/Odometry)
- Publish TF: `odom` → `base_footprint`

**Physics**:
```python
# Kinematics đơn giản
x += speed * cos(yaw) * dt
y += speed * sin(yaw) * dt
yaw += angular_z * dt
```

---

## 🎯 Task Implementation Plan

### **SPEED TRACK** (Đơn giản nhất)
```
1. Xe chạy thẳng với tốc độ cố định
2. Không cần lane detection
3. Test: Tăng tốc độ dần từ 0.3 → 1.0 m/s
4. Kiểm tra: Odometry có đúng không

Files cần:
  ✅ vehicle_physics.py
  ✅ odometry_publisher.py
  ✅ serial_mock.py
```

### **SMART CITY** (Phức tạp hơn)
```
1. Lane following: tám làn tự động
2. Sign detection: nhận diện biển báo
3. Điều khiển tích hợp cả hai

Files cần:
  ✅ vision_simulator.py (tạo ảnh)
  ✅ lane_detector.py (detect làn)
  ✅ sign_detector.py (detect biển báo)
  ✅ robot_controller.py (điều khiển)
  ✅ Tất cả của Speed Track
```

---

## 📊 ROS Topics Setup

| Topic | Type | Publish | Subscribe | Mô tả |
|-------|------|---------|-----------|-------|
| `/csi_cam_0/image_raw` | sensor_msgs/Image | vision_sim | lane_det, sign_det | Ảnh camera |
| `/lane_info` | Float32 | lane_det | robot_ctrl | Vị trí làn (-1→1) |
| `/sign_detected` | Int32 | sign_det | robot_ctrl | Biển báo (0-4) |
| `/cmd_vel` | geometry_msgs/Twist | robot_ctrl | serial_mock | Lệnh điều khiển |
| `/odom` | nav_msgs/Odometry | odom_pub | Navigation | Odometry |
| `/tf` | geometry_msgs/TransformStamped | odom_pub | TF | Transform |

---

## 🚀 Độ Ưu Tiên Phát Triển

### **Phase 1** (Cơ bản)
```
1. Serial Mock + Vehicle Physics
2. Odometry Publisher
3. Speed Track test
└─ Mục tiêu: Xe chạy thẳng đúng vị trí
```

### **Phase 2** (Lane Following)
```
1. Vision Simulator (tạo ảnh làn)
2. Lane Detector (Canny + Hough)
3. Robot Controller (PID steering)
└─ Mục tiêu: Xe tự động tám làn
```

### **Phase 3** (Sign Detection)
```
1. Vision Simulator (thêm biển báo)
2. Sign Detector (Shape/Color matching)
3. Update Robot Controller
└─ Mục tiêu: Xe nhận diện biển báo + phản ứng
```

### **Phase 4** (Testing & Tuning)
```
1. Test suite
2. Parameterize (dễ thay đổi hệ số)
3. Visualization (RViz)
```

---

## 🎥 Visualization Layer (Quan Sát Real-time)

### **RViz Visualization**
**File**: `rviz/sim_smart_city.rviz`

**Hiển thị**:
- 🤖 Robot (TF: base_footprint)
- 📍 Odometry & Path (quỹ đạo xe đã đi)
- 🚩 Target marker
- 🛣️ Lane markers (vẽ các đường lane)
- 🚦 Sign detection bounding box + label
- 📡 Sensor info (nếu có)

```
RViz Setup:
├── Fixed Frame: odom
├── Displays:
│   ├── RobotModel (TF)
│   ├── Path (/planned_path)
│   ├── Marker Array (lanes, signs)
│   ├── Image (/csi_cam_0/image_raw)
│   └── Odometry (/odom)
```

### **OpenCV Debug Windows**
**Chạy bên cạnh**:
```
lane_detector.py:
  └─ Window 1: Lane detection visualization
     ├── Original image
     ├── Canny edges
     ├── Detected lines (Hough)
     └── Lane offset display

sign_detector.py:
  └─ Window 2: Sign detection visualization
     ├── Original image
     ├── ROI boxes
     ├── Detected signs (bounding box)
     └── Confidence score
```

### **Terminal Real-time Monitor**
```bash
# Terminal 1: Xem robotstate
rostopic echo /odom | head -20

# Terminal 2: Xem lane detection
rostopic echo /lane_info

# Terminal 3: Xem sign detection
rostopic echo /sign_detected

# Terminal 4: Debug controller
rostopic echo /cmd_vel
```

### **ROS Bag Recording**
```bash
# Record toàn bộ topics
rosbag record -a -o sim_test.bag

# Replay để review
rosbag play sim_test.bag --pause
# Sau đó play từng frame từng frame để analyze
```

---

## 💡 Tips Hiệu Quả Simulation

### ✅ **Các điểm cần lưu ý**:

1. **Image Synthesis** (không dùng Camera thật)
   - Tạo ảnh giả → nhanh + không phụ thuộc phần cứng
   - Dễ test case cực đoan (làn lệch, biển báo mờ)

2. **Modular Design**
   - Mỗi node độc lập → dễ test từng phần
   - Mock được từng dependency

3. **Parameter Config**
   - Đưa tất cả hệ số vào file `.yaml`
   - Dễ tune PID, threshold detection

4. **Logging & Visualization**
   - **RViz**: Hiển thị làn, biển báo, đường đi (3D view)
   - **OpenCV Windows**: Real-time debug detection
   - **Terminal Echo**: Monitor topics
   - **Rosbag**: Record lại để replay & analyze

5. **Unit Tests**
   - Test lane_detector với ảnh chuẩn
   - Test sign_detector với ảnh biển báo
   - Test controller logic

---

## 📝 Launch Files

### `simulation_speed_track.launch`
```xml
<launch>
  <!-- Tắt hardware thật -->
  <param name="/use_sim_time" value="false" />
  
  <!-- Cấu hình chung -->
  <rosparam command="load" file="$(find jetracer)/simulation/config/simulation_params.yaml" />
  
  <!-- Bật các node simulation -->
  <node name="serial_mock" pkg="jetracer" type="serial_mock.py" output="screen" />
  <node name="odom_publisher" pkg="jetracer" type="odometry_publisher.py" output="screen" />
  
  <!-- RViz Visualization -->
  <node name="rviz" pkg="rviz" type="rviz" 
        args="-d $(find jetracer)/simulation/rviz/sim_speed_track.rviz" />
  
  <!-- Terminal monitor (optional) -->
  <node name="rqt_graph" pkg="rqt_graph" type="rqt_graph" />
</launch>
```

### `simulation_smart_city.launch`
```xml
<launch>
  <!-- Tắt hardware thật -->
  <param name="/use_sim_time" value="false" />
  
  <!-- Cấu hình chung -->
  <rosparam command="load" file="$(find jetracer)/simulation/config/simulation_params.yaml" />
  <rosparam command="load" file="$(find jetracer)/simulation/config/vehicle_config.yaml" />
  
  <!-- Simulation nodes -->
  <node name="vision_simulator" pkg="jetracer" type="vision_simulator.py" output="screen" />
  <node name="lane_detector" pkg="jetracer" type="lane_detector.py" output="screen" />
  <node name="sign_detector" pkg="jetracer" type="sign_detector.py" output="screen" />
  <node name="robot_controller" pkg="jetracer" type="robot_controller.py" output="screen" />
  <node name="odom_publisher" pkg="jetracer" type="odometry_publisher.py" output="screen" />
  <node name="serial_mock" pkg="jetracer" type="serial_mock.py" output="screen" />
  
  <!-- Visualization - RViz -->
  <node name="rviz" pkg="rviz" type="rviz" 
        args="-d $(find jetracer)/simulation/rviz/sim_smart_city.rviz" />
  
  <!-- Node graph visualization (optional) -->
  <node name="rqt_graph" pkg="rqt_graph" type="rqt_graph" />
</launch>
```

---

## 🎬 Cách Chạy Simulation

### **Speed Track Test**
```bash
# Terminal 1: Launch simulation
roslaunch jetracer simulation_speed_track.launch

# Terminal 2: Monitor odometry (optional)
rostopic echo /odom

# Terminal 3: Monitor cmd_vel
rostopic echo /cmd_vel
```

### **Smart City Test**
```bash
# Terminal 1: Launch simulation
roslaunch jetracer simulation_smart_city.launch
# → RViz sẽ mở tự động
# → OpenCV windows (lane_detector, sign_detector) sẽ hiển thị real-time

# Terminal 2: Monitor lane detection
rostopic echo /lane_info

# Terminal 3: Monitor sign detection
rostopic echo /sign_detected

# Terminal 4: Record bag (nếu muốn review sau)
rosbag record -a -o test_run.bag
```

### **Review Sau Đó**
```bash
# Replay lại
rosbag play test_run.bag --pause

# Xem graph
rosbag info test_run.bag
```

---

## 🎓 Tóm Tắt

| Giai đoạn | Thành phần | Ưu tiên | Thời gian ước | Kết quả |
|-----------|-----------|--------|--------------|--------|
| Phase 1 | Serial Mock, Odometry | 🔴 cao | 1-2 giờ | Xe chạy đúng vị trí |
| Phase 2 | Lane Detection | 🔴 cao | 2-3 giờ | Tám làn tự động |
| Phase 3 | Sign Detection | 🟡 trung | 2-3 giờ | Nhận diện biển báo |
| Phase 4 | Testing & Tuning | 🟢 thấp | 1-2 giờ | Ready deploy |

---

## ❓ Tiếp Theo

Bạn sẵn sàng **bắt đầu code** không?

**Tôi sẽ code theo thứ tự**:
1. ✅ **Phase 1**: Serial Mock + Vehicle Physics + Odometry Publisher
2. ✅ **Phase 2**: Vision Simulator + Lane Detector + Lane Following Controller
3. ✅ **Phase 3**: Sign Detector + Sign Response Controller
4. ✅ **Phase 4**: RViz Config + Testing

**Bạn chỉ cần**:
- Chạy `roslaunch` command
- Xem RViz + OpenCV windows
- Thay đổi parameters nếu cần

---

## 📊 Visualization Checklist

- [ ] RViz config file tạo
- [ ] Marker publisher trong vision_simulator
- [ ] OpenCV window trong lane_detector
- [ ] OpenCV window trong sign_detector
- [ ] Terminal echo command docs
- [ ] ROS bag recording setup
- [ ] rqt_graph visualization

---

## 🚀 Ready to Code?

Bạn muốn tôi **bắt đầu code ngay** không?

Chọn:
- **YES**: Bắt đầu Phase 1 ngay
- **NO**: Cần hỏi thêm gì?
