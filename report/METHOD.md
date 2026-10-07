# Phương pháp và cách đọc kết quả

## Phạm vi

Topic A, CPU, không train model. Dùng toàn bộ 20 frame KITTI được đề cung cấp.
Synthetic chỉ dùng kiểm tra công thức và data health. Ảnh có nguồn KITTI Vision
Benchmark Suite; dữ liệu chỉ dùng cho học tập/nghiên cứu phi thương mại.

## Phép chiếu

Điểm được biểu diễn theo hàng. `velo_to_cam` thêm cột 1 rồi nhân với
`calib.T_cam_velo.T`; ma trận này đã bao gồm `R0_rect`, không nhân lại rectification.
`cam_to_image` thêm cột 1, nhân `P2.T`, chia hai thành phần đầu cho thành phần thứ ba.
Độ sâu trả về là z trong camera, không phải khoảng cách Euclidean. Lọc NaN/Inf,
z <= 0.1 m, mẫu số gần 0 và pixel ngoài [0,W) × [0,H).

## Quần thể object và mẫu số cố định

- Chọn class Car, Van, Truck, Pedestrian, Cyclist; loại DontCare bằng loader có sẵn.
- Chỉ giữ box có kích thước dương, tâm phía trước camera, ít nhất 10 điểm LiDAR
  trong 3D box GT ở calibration gốc. Ngưỡng này loại object quá ít điểm nhưng tạo
  thiên lệch về object dễ quan sát; phải báo cả số object bị loại.
- KITTI ghi tâm ở đáy box, kích thước theo (h,w,l). Đưa điểm camera về hệ local
  của object bằng nghịch đảo rotation_y, kiểm tra x trong ±l/2, z trong ±w/2,
  y trong [-h,0]. Cố định danh sách chỉ số điểm này trước khi perturb.
- Không chọn lại điểm theo calibration sai; không loại object chỉ vì baseline
  khớp kém; không bỏ điểm khỏi mẫu số khi chúng rơi ra ngoài ảnh.

## Metric

1. **FOV %:** số điểm chiếu hợp lệ / tổng số điểm XYZ hữu hạn, cộng trên tất cả frame.
2. **Object hit % (micro):** tổng số điểm-object chiếu hợp lệ vào box 2D tương ứng /
   tổng số điểm-object được chọn ở calibration gốc. Một điểm thuộc hai box chồng
   nhau được tính trong mỗi cặp điểm-object; đây không phải số điểm duy nhất.
3. **Object hit % (macro):** trung bình không trọng số của tỷ lệ hit từng object.
   Micro dễ bị object gần, nhiều điểm chi phối; macro giúp nhìn ảnh hưởng tới object nhỏ.
4. **Pixel shift:** khoảng dịch chuyển 2D so với baseline trên giao các điểm còn
   chiếu được ở cả hai cấu hình; điểm mất FOV không có shift, nên không dùng chỉ số
   này thay cho hit %. Báo p50 theo frame trong CSV chi tiết.

Một điểm chiếu nằm trong rectangle chưa chắc đúng bề mặt vật thể: box có thể chứa
nền, che khuất hoặc cắt cụt. Metric là proxy kiểm tra calibration, không phải AP,
recall detector hoặc chứng minh ground truth hoàn hảo.

## Thí nghiệm có kiểm soát

Yaw quanh trục z LiDAR KITTI, đơn vị độ; calibration perturbed = Tr_velo_to_cam × D.
Giữ P2, R0_rect, ảnh, label, frame, class và điểm-object không đổi.
Chạy cả hai dấu để tránh kết luận chỉ dựa vào một hướng lệch. Không có sampling
hay thuật toán ngẫu nhiên; seed vẫn được ghi trong config để tái lập nếu mở rộng.
Các mức mặc định: -3, -2, -1, -0.5, 0, 0.5, 1, 2, 3 độ.

Khoảng cách trong bảng là độ sâu tâm đáy object `location[2]` trong camera, không
phải khoảng cách Euclidean từ LiDAR. Nhóm: dưới 15 m, 15–30 m, từ 30 m trở lên.
Không suy luận độ dịch pixel luôn tăng theo khoảng cách: với phép quay nhỏ, nó còn
phụ thuộc tiêu cự và góc nhìn; vật xa có box nhỏ nên cùng độ dịch có thể gây hại hơn.

## Hạn chế và failure selection

Kết quả cụ thể: 113 object đúng class/hình học được xét; 106 có ít nhất 10 điểm,
7 bị loại vì quá ít điểm. Có 59.636 cặp điểm-object cho mỗi mức yaw. Tại baseline,
micro = 66,90% nhưng macro = 92,89%. Đây không phải hai công thức mâu thuẫn:
xe gần bị cắt cụt chiếm nhiều điểm, ví dụ frame 000011 object 4 có 3.251 điểm,
chỉ 210 điểm trong FOV và 207 điểm trong box 2D (6,37%), truncated = 0,98.
Không loại case này sau khi thấy kết quả. Báo cả hai metric và giữ mẫu số như đã định.

Frame 000001 object 0 (Truck, camera depth 69,44 m) là failure được chọn:
70/70 điểm hit ở yaw 0°, 0/70 ở +3°. Sai lệch nằm ở lớp Geometry (extrinsic);
việc FOV toàn dataset gần như không thay đổi là giới hạn ở lớp Metric.
Nhóm xa >=30 m có 34 object: macro hit giảm từ 99,65% xuống 13,84% ở +3°;
đây là mô tả trên subset này, chưa tách được ảnh hưởng của class/occlusion/truncation.

Không dùng tập frame để vừa đặt vừa tuyên bố kiểm chứng ngưỡng cảnh báo tổng quát.
Failure minh hoạ được chọn sau benchmark: object có baseline hit >= 80%, còn ít
nhất 10 điểm, giảm hit lớn nhất ở yaw +3°. Đây là case có chủ đích để giải thích lỗi,
không phải ước lượng tần suất lỗi ngoài đời. Bảng tổng hợp vẫn bao gồm tất cả object
đủ điều kiện. Nếu có hòa, thứ tự frame/object trong dữ liệu quyết định.

## Câu hỏi tự kiểm tra trước vấn đáp

- Vì sao phải chuyển hệ tọa độ trước khi chiếu và chia cho s?
- Vì sao không dùng toàn bộ điểm rơi vào một box 2D làm điểm của object?
- Vì sao mẫu số phải giữ nguyên khi tăng yaw?
- Micro và macro khác nhau như thế nào?
- Vì sao FOV vẫn gần như giữ nguyên khi projection sai?
- Vì sao không được kết luận rằng yaw 1° luôn gây cùng một mức suy giảm trên mọi sensor?
- Những kiểm tra tự động nào đã chạy, và điều gì vẫn cần người học kiểm chứng?

Hướng trình bày ba phút: câu hỏi và dataset (30 giây), metric và kiểm soát
(45 giây), bảng/plot kết quả (45 giây), failure và giới hạn (40 giây), triển khai
và khai báo AI (20 giây). Người học cần tự chạy và hiểu code trước khi nộp.
