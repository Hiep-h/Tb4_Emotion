# TB4 Emotion Control

Bài thực hành: nhận diện biểu cảm khuôn mặt qua webcam và điều khiển TurtleBot di chuyển theo quỹ đạo
tương ứng, thông qua ROS 2 và topic `/cmd_vel`.

```
Webcam ─► YuNet (tìm mặt) ─► FER+ (biểu cảm) ─► bỏ phiếu ─► /detected_emotion ─► emotion_behavior_node ─► /cmd_vel
              └─► cửa sổ hiển thị: khung mặt, điểm 6 biểu cảm, trạng thái robot
```

## Biểu cảm → hành động

| Biểu cảm | Hành động | Thông số mặc định |
|---|---|---|
| Happy | Quỹ đạo cong sang **trái** | 0,12 m/s + 0,5 rad/s trong 4 s: cung bán kính 0,24 m, quay 2 rad (~115°) |
| Sad | Quỹ đạo cong sang **phải** | như trên, ngược chiều |
| Neutral | **Dừng** tại chỗ | không di chuyển |
| Angry | **Lùi** nhẹ | -0,10 m/s trong 1,5 s (~0,15 m) |
| Surprise | **Xoay một vòng** tại chỗ | 0,8 rad/s trong 2π/0,8 ≈ 7,85 s |
| Fear | **Tiến** nhẹ | 0,10 m/s trong 1,5 s (~0,15 m) |

Disgust và contempt (model có thêm) được coi là "không quyết định", robot không làm gì.

**Cách quỹ đạo chạy:** mỗi biểu cảm kích hoạt một quỹ đạo có thời hạn và nó **chạy trọn vẹn**. Trong lúc
đang chạy, biểu cảm mới hoặc mặt nhấp nháy bị bỏ qua (không cắt, không khởi động lại). Chạy xong nghỉ
1 s; nếu bạn vẫn giữ biểu cảm thì quỹ đạo lặp lại. Muốn Neutral cũng cắt quỹ đạo đang chạy, đặt
`neutral_interrupts:=true` cho `emotion_behavior_node`.

## Cài đặt

Ubuntu 22.04, ROS 2 Humble, webcam.

```bash
# 1. Đặt package vào workspace
cd ~/ros2_ws/src && git clone https://github.com/Hiep-h/Tb4_Emotion.git && cd Tb4_Emotion

# 2. Thư viện nhẹ (không cần TensorFlow)
pip install --default-timeout=120 --retries 10 -r requirements.txt

# 3. Tải 2 model nhỏ về ~/.tb4_emotion (35 MB + 0,2 MB). Tự thử lại và tiếp tục phần đã tải khi đứt mạng
bash scripts/download_models.sh

# 4. Build
cd ~/ros2_ws && colcon build --packages-select tb4_emotion_control
source install/setup.bash
```

Lưu ý khi cài:
- **NumPy phải là 1.x.** `opencv-python` 4.12 trở lên đòi NumPy 2, mà NumPy 2 làm hỏng scipy/pandas của
  hệ thống và `cv_bridge` của ROS 2 Humble (lỗi `compiled using NumPy 1.x cannot be run in NumPy 2`).
  Vì vậy ghim NumPy < 2 và OpenCV 4.11. Nếu lỡ cài bản mới:
  `pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python opencv-contrib-python-headless`
  rồi `pip install -r requirements.txt`.
- `scripts/download_models.sh` kiểm tra SHA-256; chạy lại bao nhiêu lần cũng được.
- Backend DeepFace/FER vẫn dùng được (`backend:=deepface`) nhưng cần TensorFlow, nặng hơn và tìm mặt kém
  hơn (xem bên dưới). Cách cài ở cuối `requirements.txt`.

## Chạy

Terminal 1, TurtleBot 4 trong Gazebo (theo các bài thực hành trước), ví dụ:

```bash
ros2 launch turtlebot4_ignition_bringup turtlebot4_ignition.launch.py
```

Terminal 2:

```bash
source ~/ros2_ws/install/setup.bash
ros2 launch tb4_emotion_control emotion_control.launch.py use_sim_time:=true
```

**Phím trong cửa sổ webcam:**

| Phím | Tác dụng |
|---|---|
| `SPACE` | Bật/tắt robot. **Mặc định TẮT** để an toàn; nhận diện vẫn chạy. Dòng trạng thái ghi `ROBOT TAT - nhan SPACE de bat` |
| `s` | Dừng chuyển động đang chạy |
| `q` / `Esc` | Thoát |

Muốn robot bật ngay khi khởi động: thêm `start_enabled:=true`.

**Cửa sổ hiển thị:** khung quanh khuôn mặt (màu theo biểu cảm) kèm nhãn và phần trăm, cột điểm 6 biểu cảm
bên phải, thanh trạng thái phía trên (biểu cảm đã xác nhận và hành động robot đang chạy, còn mấy giây), và
FPS/thời gian suy luận ở dưới. Nhãn viết tiếng Việt không dấu vì phông OpenCV không vẽ được dấu.

Tùy chọn launch: `backend:=onnx|deepface|fer`, `camera_index:=1`, `show_preview:=false`,
`start_enabled:=true`, `use_stamped:=true` (nếu `/cmd_vel` là `TwistStamped`, ROS 2 Jazzy trở lên).

**Khi chạy với Gazebo hãy thêm `use_sim_time:=true`.** Gazebo hiếm khi chạy đúng 100% tốc độ thời gian
thực (xem phần trăm ở góc dưới cửa sổ Gazebo). Nếu chỉ 30% mà node đếm giờ theo đồng hồ thật thì quỹ đạo bị
cụt. Với `use_sim_time:=true` quỹ đạo tính theo đồng hồ mô phỏng nên robot đi đủ, chỉ chậm hơn ngoài đời.

Kiểm tra riêng phần robot khi chưa có webcam: `fake:=true` phát lần lượt cả 6 biểu cảm (mỗi biểu cảm
10 s). Xem `ros2 topic echo /cmd_vel`.

### Gazebo bị kẹt / cửa sổ đen "not responding"

World mặc định `warehouse` tải model từ Internet (Fuel) nên mạng yếu sẽ treo. Dùng world trống:

```bash
python3 scripts/make_empty_world.py        # sinh ~/empty.sdf từ warehouse.sdf đã cài, bỏ model Fuel
sudo cp ~/empty.sdf /opt/ros/humble/share/turtlebot4_ignition_bringup/worlds/empty.sdf
ros2 launch turtlebot4_ignition_bringup turtlebot4_ignition.launch.py world:=empty
```

World trống cũng tránh để robot đi cung vào tường (world `maze` có tường sát robot). Mô phỏng hay chạy chậm,
nên đóng bớt ứng dụng khác khi chạy.

## Thành phần

| Node | Vào | Ra | Vai trò |
|---|---|---|---|
| `emotion_recognition_node` | Webcam, `/emotion_robot_state` | `/detected_emotion` (JSON) | Tìm mặt + phân loại biểu cảm ở luồng riêng, bỏ phiếu, vẽ cửa sổ, nhận phím |
| `emotion_behavior_node` | `/detected_emotion` | `/cmd_vel`, `/emotion_robot_state` | Kích hoạt quỹ đạo, bật/tắt, dừng, dừng khi mất tín hiệu |
| `fake_emotion_node` | | `/detected_emotion` | Giả lập khi chưa có webcam |

Bản tin: `{"emotion": "happy", "confidence": 0.87, "face": true, "enabled": true, "stop_id": 0, "stamp": 1730000000.1}`;
`emotion` là một trong `happy sad neutral angry surprise fear none`.

### Vì sao dùng YuNet + FER+

Trên video thử của chính người làm (47 khung, mỗi 2 giây), bộ tìm mặt Haar của OpenCV (cũng là bộ mặc định của
DeepFace) chỉ thấy mặt người dùng ở 34/47 khung, hay mất khi mặt gần camera, hơi nghiêng hoặc đang nói, và
thỉnh thoảng bắt nhầm mặt người ngồi phía sau. YuNet thấy ở 46/47 khung. FER+ cho nhãn phù hợp với nét mặt
thật (happy lúc cười, surprise lúc há miệng). Đó là một video của một người, không phải thang đo chính thức.

### Chống nhiễu và an toàn

- **Chỉ xét mặt đủ lớn:** mặt rộng dưới 15% khung hình (`min_face_ratio`) bị bỏ, nên người ngồi phía sau không
  điều khiển robot.
- Độ tin cậy dưới `min_confidence` (0,40), không thấy mặt, hoặc disgust/contempt đều bỏ phiếu "none"; biểu
  cảm chỉ được công bố khi thắng ≥ 3/5 lần phân tích gần nhất, rồi `emotion_behavior_node` cần thấy ≥ 3 bản tin
  liên tiếp.
- Robot **tắt** khi khởi động; chỉ chạy sau khi bấm `SPACE`.
- Không nhận được `/detected_emotion` trong 2 s (webcam hoặc node chết) thì robot dừng.
- Vận tốc bị chặn: tối đa 0,25 m/s và 1,2 rad/s; tham số vượt ngưỡng làm node không khởi động.

### Tham số

`emotion_recognition_node`: `backend` (`onnx`|`deepface`|`fer`), `model_path`, `camera_index`,
`min_confidence`, `min_face_ratio`, `vote_window`/`vote_min`, `analyze_interval_s` (0,15), `show_preview`,
`mirror`, `start_enabled`.

`emotion_behavior_node`: `curve_linear`, `curve_angular`, `curve_duration`, `back_speed`, `back_duration`,
`forward_speed`, `forward_duration`, `spin_speed`, `spin_turns`, `required_consecutive`,
`min_trigger_interval`, `cooldown_s`, `retrigger_s`, `neutral_interrupts`, `signal_timeout`, `use_stamped`.

## Mẹo để nhận đúng

- Ngồi cách camera 0,5-1 m, mặt chính diện, đủ sáng. Mặt chiếm gần hết khung hình vẫn nhận được nhưng nên lùi
  ra một chút.
- Làm biểu cảm rõ và giữ khoảng 1 giây. Fear và Surprise dễ lẫn nhau (cả hai há miệng, mở to mắt); Angry và
  Sad cần nét mặt rõ. Nếu khó nhận, hạ `min_confidence` xuống 0,30.
- Nếu người ngồi sau vẫn bị bắt, tăng `min_face_ratio` (ví dụ 0,20).

## Kiểm thử

```bash
cd tb4_emotion_control && python3 -m pytest test -q
```

29 bài test phủ phần logic không cần ROS: chuyển điểm các backend về cùng thang, thứ tự nhãn của FER+, chọn
mặt lớn nhất, bỏ mặt nhỏ, quỹ đạo từng biểu cảm (hướng cung, lùi/tiến, xoay đúng 2π), giới hạn an toàn, bỏ
phiếu và chống kích hoạt lặp, phần vẽ kết quả.

## Hạn chế

- Quỹ đạo là **vòng hở theo thời gian**: góc xoay và quãng đường phụ thuộc robot chạy đúng vận tốc lệnh.
  Muốn chính xác hơn cần phản hồi từ `/odom`.
- Độ chính xác biểu cảm phụ thuộc ánh sáng, góc mặt và người dùng; FER+ được huấn luyện trên ảnh xám 64×64
  nên hay nhầm giữa vài cặp biểu cảm. Chưa có số đo chính thức trên nhiều người.
- Chỉ phân tích khuôn mặt lớn nhất trong khung hình.
