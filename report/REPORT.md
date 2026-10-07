# Báo cáo Day 6: [ĐIỀN tên đề tài ngắn]

> Thay **mọi** ô có chữ ĐIỀN nằm trong ngoặc vuông bằng nội dung của bạn, xoá luôn cả dấu ngoặc vuông. Lệnh `python tools/check_submission.py` sẽ báo FAIL nếu còn sót bất kỳ chỗ nào.

- **Họ tên:** Nguyễn Hải Hoàng
- **MSSV:** 2A202602489
- **Lớp:** K4B
- **Link repo:** https://github.com/hoang9605/NguyenHaiHoang-2A202602489-Track4-Day21
- **Topic:** A — LiDAR-camera projection QA
- **Dataset:** data/synthetic (kiểm tra), data/kitti_mini (thí nghiệm chính)
- **Các frame đã dùng:** synthetic 000000–000004; toàn bộ 20 frame KITTI, danh sách sẽ lưu trong CSV thí nghiệm.

> Hãy viết ngắn: mỗi mục từ 3 đến 8 dòng, ưu tiên số liệu và hình ảnh.

## 1. Claim

Giả thuyết ban đầu (CP1): tăng độ lớn lệch yaw từ 0° đến 3° làm giảm tỷ lệ điểm của object chiếu vào box 2D tương ứng trên KITTI, trong khi tỷ lệ điểm trong FOV có thể ít thay đổi. Kiểm tra cả yaw âm và dương; giữ nguyên tập điểm được chọn bằng 3D GT và calibration gốc. Claim cuối cùng sẽ căn cứ vào kết quả chạy thật.

## 2. Evidence

Bảng hoặc plot số liệu, kèm ảnh/video demo. Ghi rõ đường dẫn file trong `results/`.

| Cấu hình / mức perturb | Metric 1 | Metric 2 | Ghi chú |
|---|---|---|---|
| [ĐIỀN] | | | |

![demo](../results/figures/[ĐIỀN].png)

## 3. Failure case

Frame **000001**, object **0 (Truck)**, độ sâu **69,44 m**: baseline có **70/70** điểm trong box; yaw **+3°** còn **0/70**. Ảnh dưới giữ nguyên điểm và box, chỉ đổi extrinsic.
Lỗi thuộc **Geometry**: phép quay sai đẩy điểm sang trái box; box vật xa nhỏ nên dễ mất toàn bộ overlap. FOV tổng vẫn gần như giữ nguyên, cho thấy giới hạn của **Metric** nếu chỉ theo dõi FOV.
Case được chọn sau thí nghiệm theo mức giảm hit lớn nhất trong nhóm baseline >=80%, không dùng để ước lượng tỷ lệ lỗi ngoài đời. Xem [phương pháp](METHOD.md) và [metadata](../results/visual_cases.json).

![failure](../results/figures/fail_01_yaw_drift.png)

## 4. Khuyến nghị nếu triển khai thật

Use-case cụ thể (ADAS / robot / drone), trade-off và bước tiếp theo.

[ĐIỀN]

## 5. Cách chạy lại

Các lệnh tái tạo lại toàn bộ kết quả từ repo sạch.

```bash
[ĐIỀN]
```

## 6. Khai báo sử dụng AI

Ghi rõ đã dùng công cụ AI nào, dùng vào việc gì, và bạn đã tự kiểm chứng kết quả đó bằng cách nào. Nếu không dùng AI, ghi "Không sử dụng". Xem quy định ở `RULES.md` mục 2.

| Công cụ | Dùng cho việc gì | Bạn đã kiểm chứng thế nào |
|---|---|---|
| [ĐIỀN] | | |
