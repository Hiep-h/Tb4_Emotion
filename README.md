# TB4 Emotion Control

Bài thực hành: nhận diện biểu cảm khuôn mặt qua webcam và điều khiển TurtleBot di chuyển theo
quỹ đạo tương ứng, thông qua ROS 2 và topic `/cmd_vel`.

```
Webcam ─► OpenCV ─► DeepFace | FER ─► bỏ phiếu ổn định ─► /detected_emotion ─► emotion_behavior_node ─► /cmd_vel
              └─► cửa sổ hiển thị: khung mặt, 6 thanh điểm, hành động hiện tại
```

## Biểu cảm → hành động

| Biểu cảm | Hành động | Thông số mặc định |
|---|---|---|
| Happy | Quỹ đạo cong sang **trái** | 0,12 m/s + 0,5 rad/s trong 4 s: cung bán kính 0,24 m, quay 2 rad (~115°) |
| Sad | Quỹ đạo cong sang **phải** | như trên, ngược chiều |
| Neutral | **Dừng** tại chỗ | dừng ngay, kể cả khi đang chạy một quỹ đạo |
| Angry | **Lùi** nhẹ | -0,10 m/s trong 1,5 s (~0,15 m) |
| Surprise | **Xoay một vòng** tại chỗ | 0,8 rad/s trong 2π/0,8 ≈ 7,85 s |
| Fear | **Tiến** nhẹ | 0,10 m/s trong 1,5 s (~0,15 m) |

`Disgust` (có trong cả DeepFace và FER nhưng đề không dùng) được coi là "không quyết định", robot
không làm gì.

Cách dùng khi chạy: mỗi biểu cảm **kích hoạt một lần** khi nó đổi và ổn định. **Giữ nét mặt** trong lúc
robot chạy (Happy/Sad khoảng 4 s, Surprise khoảng 8 s), vì khi nét mặt chuyển về Neutral thì robot
dừng ngay. Muốn lặp quỹ đạo khi vẫn giữ nét mặt, đặt `retrigger_s` (ví dụ `5.0`).

## Cài đặt

Ubuntu 22.04, ROS 2 Humble, webcam.

```bash
# 1. Đặt package vào workspace
cd ~/ros2_ws/src && git clone <repo này>

# 2. Thư viện nhận diện biểu cảm (đúng thứ tự). TensorFlow bản CPU ~274 MB, nhẹ hơn bản đầy đủ ~572 MB
pip install --default-timeout=120 --retries 10 tensorflow-cpu==2.21.0
pip install --default-timeout=120 --retries 10 --no-deps tf-keras==2.21.0
pip install --default-timeout=120 --retries 10 -r requirements.txt
pip install --default-timeout=120 --retries 10 --no-deps deepface retina-face

# 3. Build
cd ~/ros2_ws && colcon build --packages-select tb4_emotion_control
source install/setup.bash
```

Lưu ý khi cài:
- `pip install deepface` **không** tự cài TensorFlow. Cần TensorFlow và, với TF ≥ 2.16, cả `tf-keras`
  (lệnh ở bước 2). Tổng dung lượng tải khoảng 0,4 GB (Linux x86_64). Lần chạy đầu DeepFace còn tải
  thêm trọng số model nên cần mạng.
- Nếu `import tensorflow` báo `No module named 'tensorflow.python'` thì cài đặt bị ngắt giữa chừng:
  `pip uninstall -y tensorflow tensorflow-cpu`, xóa thư mục `tensorflow` còn sót trong
  `~/.local/lib/python3.10/site-packages/`, rồi cài lại.
- **NumPy phải là 1.x.** `opencv-python` 4.12 trở lên đòi NumPy 2, mà NumPy 2 làm hỏng scipy/pandas của
  hệ thống (lỗi `module that was compiled using NumPy 1.x cannot be run in NumPy 2` hoặc
  `numpy.dtype size changed`) và `cv_bridge` của ROS 2 Humble. Vì vậy `requirements.txt` ghim NumPy < 2 và
  OpenCV 4.11. Nếu lỡ cài phải bản mới:
  `pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python opencv-contrib-python-headless`
  rồi `pip install -r requirements.txt`.
- DeepFace và retina-face khai báo cần OpenCV bản *headless* (không hiện được cửa sổ), nên cài chúng bằng
  `--no-deps` như trên để không ghi đè bản OpenCV có giao diện.
- Backend `fer` (`backend:=fer`) với `fer` 25.x được import bằng `from fer.fer import FER`; mã đã xử lý
  cả cách import cũ.

## Chạy

Terminal 1, khởi chạy TurtleBot trong Gazebo (theo các bài thực hành trước, ví dụ):

```bash
ros2 launch turtlebot4_ignition_bringup turtlebot4_ignition.launch.py
```

Terminal 2:

```bash
source ~/ros2_ws/install/setup.bash
ros2 launch tb4_emotion_control emotion_control.launch.py
```

Tùy chọn: `backend:=fer`, `camera_index:=1`, `show_preview:=false`.
Nhấn `q` hoặc `Esc` trong cửa sổ webcam để thoát.

Kiểm tra phía robot khi chưa có webcam hoặc muốn xem từng quỹ đạo: `fake:=true` phát lần lượt cả 6
biểu cảm (mỗi biểu cảm 10 s, xen kẽ Neutral):

```bash
ros2 launch tb4_emotion_control emotion_control.launch.py fake:=true
ros2 topic echo /cmd_vel
```

Nếu `/cmd_vel` của robot là `TwistStamped` (ROS 2 Jazzy trở lên) thêm `use_stamped:=true`.

## Thành phần

| Node | Vào | Ra | Vai trò |
|---|---|---|---|
| `emotion_recognition_node` | Webcam | `/detected_emotion` (`std_msgs/String`, JSON) | Phân tích biểu cảm trong luồng riêng (webcam luôn mượt), bỏ phiếu đa số, vẽ kết quả |
| `emotion_behavior_node` | `/detected_emotion` | `/cmd_vel` | Kích hoạt quỹ đạo, dừng khi Neutral hoặc mất tín hiệu |
| `fake_emotion_node` | | `/detected_emotion` | Giả lập khi chưa có webcam |

Bản tin: `{"emotion": "happy", "confidence": 0.87, "face": true, "stamp": 1730000000.1}`;
`emotion` là một trong `happy sad neutral angry surprise fear none`.

Hiển thị thời gian thực: khung quanh khuôn mặt kèm nhãn và phần trăm, sáu thanh điểm số, và dòng
`Action: HAPPY -> curve left` khi biểu cảm đã ổn định. Nhãn viết tiếng Anh vì phông OpenCV không vẽ
được tiếng Việt có dấu.

### Chống nhiễu và an toàn

- Khung hình không thấy mặt, độ tin cậy dưới `min_confidence` (0,45) hoặc kết quả là Disgust đều
  bỏ phiếu "none". Một biểu cảm chỉ được công bố khi thắng ≥ 3/5 lần phân tích gần nhất.
- `emotion_behavior_node` chỉ kích hoạt khi thấy cùng biểu cảm ≥ 3 bản tin liên tiếp, mỗi lần giữ
  biểu cảm chỉ kích hoạt một lần, và cách nhau ≥ 0,5 s.
- Không nhận được `/detected_emotion` trong 2 s (webcam hoặc node nhận diện chết) thì robot dừng.
- Vận tốc bị chặn: tối đa 0,25 m/s và 1,2 rad/s; tham số vượt ngưỡng làm node không khởi động.
- Mất mặt trong lúc robot đang chạy không dừng robot (quỹ đạo vốn ngắn); chỉ Neutral hoặc mất tín hiệu
  mới dừng.

### Tham số

`emotion_recognition_node`: `backend` (`deepface`|`fer`), `detector_backend` (`opencv`),
`camera_index`, `min_confidence`, `vote_window`/`vote_min`, `analyze_interval_s` (0,15),
`show_preview`, `mirror`.

`emotion_behavior_node`: `curve_linear`, `curve_angular`, `curve_duration`, `back_speed`,
`back_duration`, `forward_speed`, `forward_duration`, `spin_speed`, `spin_turns`,
`required_consecutive`, `min_trigger_interval`, `retrigger_s`, `signal_timeout`, `use_stamped`.

## Kiểm thử

```bash
cd tb4_emotion_control && python3 -m pytest test -q
```

22 bài test phủ phần logic không cần ROS: chuyển điểm DeepFace (phần trăm) và FER (0-1) về cùng thang,
quỹ đạo từng biểu cảm (hướng cung, lùi/tiến, xoay đúng 2π), giới hạn an toàn, bỏ phiếu và chống kích
hoạt lặp, phần vẽ kết quả.

## Hạn chế

- **Chưa chạy với DeepFace/FER, webcam và Gazebo thật** (đã kiểm tra các node bằng bản giả của chúng).
  Cần thử trên máy có ROS 2 và webcam; độ chính xác biểu cảm phụ thuộc ánh sáng và góc mặt.
- DeepFace chạy bằng CPU khoảng vài lần phân tích mỗi giây; độ trễ từ lúc đổi nét mặt đến lúc robot
  động khoảng 0,5-1 s do bỏ phiếu.
- Quỹ đạo là **vòng hở theo thời gian**: góc xoay và quãng đường phụ thuộc robot chạy đúng vận tốc
  lệnh (trên Gazebo tốc độ thực thấp hơn 1x có thể làm xoay chưa đủ một vòng). Muốn chính xác hơn cần
  phản hồi từ `/odom`.
- Chỉ phân tích khuôn mặt lớn nhất trong khung hình.
