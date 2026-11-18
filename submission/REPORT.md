# Báo cáo Day 09 — <Ngô Ngọc Trường>, <2A202603329>

> Xoá mọi `TODO(học viên)` và dòng gợi ý. Mỗi ý trả lời bằng **số lấy từ `submission/reports/`**, kèm mẫu số. Cả báo cáo ~1–2 trang.

## 1. Kết luận trước
TODO(học viên): pipeline kết luận **Release / Hold / Rework**? Bao nhiêu ảnh vào, bao nhiêu ảnh ra dataset? Lý do chính (1–3 câu).

## 2. Lỗi và phân việc
Lấy từ `02_error_list_v1` (gom theo mã lỗi). Cột "ai sửa": **máy** (autofix) hay **người** (hàng đợi); chỉ ghi những mã có mặt trong lô của bạn.

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| TODO(học viên) | | | |

TODO(học viên): vì sao `05_review_queue.csv` xếp ảnh đầu hàng như vậy? Với ngân sách 80 ảnh, người xem được bao nhiêu lỗi ngữ nghĩa?

## 3. Calibration (2 ngưỡng)
| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | TODO(học viên) | | |
| `second_opinion.conf` | 0.25 | TODO(học viên) | | |

TODO(học viên): **một chỗ calibration có thể đánh lừa bạn**, kèm bằng chứng từ dữ liệu của bạn (vd. mở xem vài cặp ảnh bị cho là trùng; số ảnh bị loại ở bước 1 có hợp lý không?).

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
TODO(học viên): (a) chứng minh gate chặn đúng: chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb` (không có người duyệt nên ảnh thiếu file nhãn còn nguyên), chỉ ra kết luận **Rework**, mã thoát 20 và việc **không xuất** dataset. (Đừng sửa tay `work/run/ds`: pipeline dựng lại thư mục này từ raw mỗi lần chạy.) (b) ≥ 2 điểm mù có bằng chứng (box lỏng nhẹ, nhầm lớp mà model lớn cũng nhầm, ảnh trùng biến đổi mạnh…).

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Chưa train: ghi "chưa chạy" và lý do, rồi bỏ qua phần còn lại của mục này. Nếu đã train: dán bảng từ `submission/results/comparison.md` (model, epoch, seed, số ảnh train mỗi biến thể).

TODO(học viên): chênh mAP50 (clean − raw) so với **độ lệch chuẩn giữa các seed**; kết luận **trung thực** (nằm trong nhiễu thì nói là chưa kết luận được); ≥ 2 giả thuyết giải thích (ảnh trùng/rò rỉ test trong `raw`, nhãn máy còn lại trong `clean`, test chỉ 100 ảnh…) và cách kiểm.

## 6. Quyết định và ghi chú AI
TODO(học viên): (a) quyết định cuối; nếu Hold/Rework cần làm gì để thành Release? (b) Dùng AI viết code? Ghi 3 dòng: prompt chính, cách bạn kiểm code AI, 1 lần AI sai. Không dùng: ghi "không dùng".

### (Thưởng +2) CVAT: lọc box nhỏ `width < 20`

**Thiết lập.** CVAT tự host (`localhost:8080`), project `AutoQC-Pipeline` tạo từ `cvat/labels.json` (4 nhãn `car, person, truck, bus` đúng thứ tự id, thuộc tính `can_review`). Task `day09-cvat-filter-top20-queue` gồm **20 ảnh đầu `05_review_queue.csv`**, lấy từ `work/run/ds/images/` sau khi chạy `python -m pipeline.run --no-review`: nhãn ở trạng thái **sau autofix, trước người duyệt** (nếu chạy đủ, `human_review_sim` đã chép nhãn tham chiếu đè lên 80 ảnh đầu hàng đợi). Nhãn import dạng YOLO 1.1: **111 box** = đúng tổng số dòng nhãn của 20 ảnh; 4 ảnh `NEEDS_LABEL` (img_0031, img_0053, img_0126, img_0135) không có box.

**Lọc** trong màn hình job: *Filters → Objects → Add rule → `Width < 20`* (nút Not tắt) → Submit. Kết quả: **10 box / 4 ảnh** (chi tiết: `work/cvat/cvat_filter_width_lt20.csv`).

| Ảnh | Box khớp `width < 20` (rộng × cao, px) | Pipeline báo `BOX_TINY`? |
|---|---|---|
| img_0020 | 4 person: 16,4×33,2 · 19,5×54,3 · 16,8×55,3 · 15,0×50,7 | không |
| img_0030 | 4 person: 18,1×76,1 · **9,8×84,3** · 19,5×59,4 · 18,6×56,4 | **có, 1 box** (dòng 9) |
| img_0067 | 1 person: 14,8×42,0 | không |
| img_0210 | 1 car: 16,6×22,6 | không |

**Đối chiếu với pipeline.** Chỉ **1/10** box CVAT lọc ra trùng với `BOX_TINY` (img_0030 dòng 9, rộng 9,8 px); ngược lại `BOX_TINY` duy nhất trong 20 ảnh này đều nằm trong kết quả CVAT. Lệch vì hai quy tắc khác nhau: pipeline báo khi **cạnh ngắn < 12 px** (`label_format.min_box_px`), slide/CVAT lọc **chiều rộng < 20 px**. 9 box còn lại là người đứng xa / sau kính xe buýt: hẹp (15–19,5 px) nhưng cao 33–84 px, nên với pipeline không phải box "quá nhỏ" — đây là vật thật, không nên xoá hàng loạt bằng *Remove filtered shapes*. Ngưỡng 12 px là quy tắc dự án (không có đáp án để calibrate), CVAT ở đây là công cụ để **người xem** những ca biên mà quy tắc của máy cố ý bỏ qua.

**`can_review`.** Người gán bật `can_review = true` cho box họ **không chắc** (vật bị che khuất, quá nhỏ, mơ hồ giữa car/truck/bus) để người duyệt lọc riêng bằng `attr["can_review"]==true`; pipeline dùng thông tin tương tự ở **hàng đợi duyệt** (`05_review_queue.csv`): các cảnh báo `POSSIBLE_*` của `second_opinion` (kèm `conf` của model) và `BOX_TINY` được cộng trọng số để đẩy ảnh "đáng nghi" lên trước cho người xem.

*Ảnh chụp bộ lọc:* `submission/cvat_filter_width_lt20.png`
