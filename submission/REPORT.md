# Báo cáo Day 09 — Ngô Ngọc Trường, 2A202603329

## 1. Kết luận trước
**HOLD** (mã thoát 10). 224 ảnh vào → bước nhận loại 22 → **202 ảnh** vào QC và ra `submission/export/clean_v1/` dưới dạng **bản nháp** (chưa phát hành).
Sau autofix + người duyệt (mô phỏng, 80/80 ảnh ngân sách) còn **0 lỗi bắt buộc**, nhưng **38/202 ảnh (18,8%)** còn cảnh báo chưa ai duyệt, ≥ ngưỡng 10% của cổng → Hold. Nguyên nhân chính: hàng đợi duyệt 125 ảnh > ngân sách 80 ảnh.

## 2. Lỗi và phân việc
Lấy từ `02_error_list_v1` (trước khi sửa; mẫu số: 224 ảnh ở bước nhận, 202 ảnh ở QC nhãn).

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `CORRUPT_IMAGE` | 2 ảnh | máy (loại ở bước nhận) | không mở được → không dùng được |
| `BAD_SIZE` | 3 ảnh | máy (loại) | cạnh ngắn < 250 px, quy tắc dự án |
| `DUP_IMAGE_EXACT` | 8 ảnh | máy (loại) | trùng byte (md5), chắc chắn |
| `DUP_IMAGE_NEAR` | 4 ảnh | máy (loại) | phash ≤ 12, đã mở xem từng cặp (§3) |
| `LEAK_TEST` | 5 ảnh | máy (loại) | trùng ảnh test → metric đẹp giả |
| `BAD_FORMAT` | 3 dòng / 3 ảnh | máy (`drop_line`) | thiếu cột / `nan`: không thể đoán giá trị |
| `BAD_CLASS_ID` | 6 dòng / 6 ảnh | máy (`drop_line`) | id ngoài 0..3, không biết lớp đúng |
| `BOX_ZERO` | 4 dòng / 4 ảnh | máy (`drop_line`) | box rộng/cao 0 không có nghĩa |
| `DUP_BOX` | 7 dòng / 7 ảnh | máy (`drop_line`) | cùng lớp, IoU > 0,9 với dòng trước |
| `BOX_OUT_OF_IMAGE` | 8 dòng / 8 ảnh | máy (`clip_box`) | cắt về [0,1], giữ lớp |
| `BAD_CLASS_NAME` | 2 lỗi / `data.yaml` | máy (`rename_classes`) | tên lớp viết hoa sai, ghi lại theo `cfg` |
| `MISSING_LABEL_FILE` | 6 ảnh | **người** (`needs_label`) | máy không được bịa nhãn |
| `EMPTY_LABEL` | 12 ảnh (15 sau autofix) | người | ảnh nền hay thiếu nhãn? 3 file thành rỗng sau khi xoá dòng hỏng |
| `BOX_TINY` / `BOX_HUGE` | 6 dòng / 4 ảnh · 3 ảnh | người | quy tắc dự án, có thể là vật thật |
| `CLASS_RARE` | 4 (cấp dataset) | máy gián tiếp | sinh ra từ id lạ (93, 4, −1); hết sau `drop_line` |
| `POSSIBLE_MISSING` | 53 / 52 ảnh | người | model thấy vật mà nhãn không có |
| `POSSIBLE_WRONG_CLASS` | 18 / 18 ảnh | người | car↔truck↔bus: cần mắt người |
| `POSSIBLE_LOOSE_BOX` | 28 / 24 ảnh | người | box lệch/lỏng so với model |
| `POSSIBLE_FALSE_POS` | 29 / 27 ảnh | người | box nhãn không khớp vật nào model thấy |

Máy sửa **35 thay đổi** (`03_fixes.csv`: 20 `drop_line`, 8 `clip_box`, 1 `rename_classes`, 6 `needs_label`); 22 ảnh bị loại ở bước nhận (`01_intake.csv`).

**Hàng đợi** (`05_review_queue.csv`, 125 ảnh) xếp theo điểm = Σ trọng số mã × (1 + conf của model). Đầu hàng là img_0020 (`FIXED_DROP_LINE` + `POSSIBLE_MISSING` + `POSSIBLE_WRONG_CLASS`), tiếp theo là 6 ảnh `NEEDS_LABEL` (trọng số 10, vị trí 2–7) vì thiếu nhãn là lỗi bắt buộc chặn cổng. Với ngân sách 80 ảnh, người duyệt được **74/103 ảnh** có cảnh báo ngữ nghĩa (`POSSIBLE_*`) ở `04_error_list_v2`; 29 ảnh có cảnh báo ngữ nghĩa còn lại không ai xem.

## 3. Calibration (2 ngưỡng)
Số trên calib (39 ảnh, `submission/calibration/calibration_report.md`) và trên raw (chạy pipeline với từng giá trị).

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | **12** | `DUP_IMAGE_NEAR` 1,00 / 0,50 → **1,00 / 0,67**; `DUP_IMAGE_EXACT` giữ 1,00 / 1,00 | Lỗi bắt buộc → ảnh bị **xoá**, nên ưu tiên precision. 4–14 cùng điểm trên calib; trên raw 12 bắt thêm 2 cặp trùng thật (dist 6: đổi sáng; dist 10: cắt) + 1 rò rỉ test (img_0221 ↔ test_009), mở xem cả 4 đều đúng. 16 có recall calib cao hơn (0,83) nhưng gộp nhầm ảnh khác (bên dưới). |
| `second_opinion.conf` | 0.25 | **0.6** | `WRONG_CLASS` 0,56/0,83 → **0,62/0,83**; `MISSING` 0,50/1,00 → **0,57/1,00**; `LOOSE_BOX` 0,29/0,40 → 0,20/0,20; `FALSE_POS` 0,31/1,00 (không đổi, dùng `fp_conf`) | Cảnh báo cho người: giữ recall `MISSING`/`WRONG_CLASS` (lỗi lọt vào dataset là giá cao), tăng precision để bớt báo động giả. 0,6 là giá trị cao nhất còn `MISSING` recall 1,00. Giá phải trả: `LOOSE_BOX` recall tụt. Trên raw: hàng đợi 143 → 125 ảnh, ảnh còn cảnh báo 28,7% → 18,8%. |

**Chỗ calibration đánh lừa.** (1) `phash_dist = 16` có F1 cao nhất trên calib (`DUP_IMAGE_NEAR` 1,00 / 0,83 / 0,91, precision vẫn 1,00), nhưng trên raw số ảnh bị loại ở bước nhận nhảy 22 → 31, và mở xem thì có cặp **khác hẳn nhau**: img_0011 (tennis) ↔ img_0008 (trượt tuyết), img_0177 (lướt sóng) ↔ img_0113 (người ngồi bàn); `LEAK_TEST` nhầm img_0013 (laptop) ↔ test_087 (bóng chày), img_0038 ↔ test_002 (bánh cưới). Calib chỉ có 6 cặp gần trùng nên không thấy được báo động giả này. (2) `conf = 0.8` cho cổng **Release** (16/202 = 7,9%) nhưng `MISSING` recall trên calib tụt còn 0,75: hàng đợi nhỏ vì checker mù hơn, là Release giả → không chọn.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
**(a) Gate chặn đúng.** `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb` (không có người duyệt): kết luận **REWORK — "Còn 6 lỗi bắt buộc (MISSING_LABEL_FILE: 6)"** (img_0031, img_0053, img_0126, img_0135, img_0170, img_0219), **mã thoát 20**, log "KHÔNG xuất: còn lỗi bắt buộc", và thư mục `work/exp_nb` **không được tạo**. Autofix không tạo file nhãn rỗng cho các ảnh này, nên lỗi không bị "che" mà phải có người gán.

**(b) Điểm mù.**
1. **Ảnh trùng biến đổi mạnh:** trên calib, ở ngưỡng đã chọn vẫn sót 2/6 cặp gần trùng (recall 0,67); nâng ngưỡng để bắt thì gộp nhầm ảnh khác (§3). Không ngưỡng phash nào bắt hết.
2. **Box lỏng nhẹ:** `POSSIBLE_LOOSE_BOX` recall chỉ 0,20 (1/5) trên calib ở `conf = 0.6`; box phình vừa phải vẫn có IoU ≥ 0,5 với model nên không bị cờ.
3. **Ý kiến thứ hai có nhiễu và có thể sai cùng chiều với nhãn:** sau khi người thay bằng nhãn đúng, **25 ảnh đã duyệt** vẫn còn `POSSIBLE_*` ở `07_error_list_v3` → model lệch với cả nhãn người (báo động giả). Ngược lại, nếu model cũng nhầm car↔truck như người gán thì không có cờ: calib còn 1/6 `WRONG_CLASS` bị sót.
4. **Box nhỏ theo quy tắc:** `BOX_TINY` dùng cạnh ngắn < 12 px; CVAT lọc `width < 20` ra 10 box nhưng pipeline chỉ cờ 1 (phần CVAT bên dưới).

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Colab T4, `yolo26n.pt`, 20 epoch, imgsz 640, batch 16, seed 0 và 1; cùng val (`gold_val`, 40 ảnh) và test (`data/test`, 100 ảnh). `clean` = `submission/export/clean_v1` (manifest sha1 `fc0b091…`, kết luận Hold → bản nháp). Bảng do `scripts/summarize_results.py` sinh (`submission/results/comparison.md`):

| biến thể | #ảnh train | số seed | mAP50 (TB ± độ lệch) | mAP50-95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 202 | 2 | 0.701 ± 0.025 | 0.487 ± 0.008 | 0.759 ± 0.003 | 0.625 ± 0.019 |

AP50 theo lớp (TB 2 seed): car 0,738 (clean) vs 0,738 (raw) · person 0,823 vs 0,822 · bus 0,703 vs 0,695 · **truck 0,538 vs 0,648**.

**Kết luận (trung thực): chưa kết luận được.** Chênh mAP50 (clean − raw) = **−0,025**, bằng đúng độ lệch giữa 2 seed của `clean` (±0,025); hai seed của `clean` cách nhau 0,035 (0,718 vs 0,683). Với 2 seed, độ lệch chuẩn ước lượng rất thô, nên **không** nói được clean tốt hơn, cũng không chắc nó kém hơn. Toàn bộ khoảng chênh đến từ lớp **truck** (car/person/bus gần như bằng nhau).

**Giả thuyết và cách kiểm:**
1. **`raw` bị thổi phồng do rò rỉ test:** pipeline bắt 5 ảnh `LEAK_TEST` trong raw (img_0049 ↔ test_033, img_0101 ↔ test_039, img_0167 ↔ test_044, img_0174 ↔ test_085, img_0221 ↔ test_009) và 12 ảnh trùng trong nội bộ raw; `clean` đã loại chúng. *Kiểm:* đánh giá lại hai model trên test **bỏ 5 ảnh trên** (95 ảnh) xem khoảng cách có đổi chiều không.
2. **Lớp truck quá ít mẫu nên rất nhiễu:** test chỉ có 24 box truck; AP50 truck của chính `clean` dao động 0,590 ↔ 0,486 giữa 2 seed (Δ 0,10). *Kiểm:* chạy thêm seed (≥ 5) và báo khoảng tin cậy theo lớp.
3. **Nhãn trong `clean` lẫn hai "phong cách":** 80 ảnh được thay bằng nhãn người (mô phỏng), còn lại là nhãn máy sau autofix; số box truck tăng 32 → 41 trong khi car giảm 122 → 101 (sửa car↔truck), nhưng 38 ảnh còn cảnh báo chưa duyệt (trong đó còn 3 `POSSIBLE_WRONG_CLASS`). Ranh giới car/truck có thể không nhất quán hơn trước. *Kiểm:* thêm biến thể `oracle` (cùng ảnh, toàn nhãn người) làm chặn trên; xem confusion matrix car↔truck của hai model.
4. **Ít ảnh hơn:** clean train 202 ảnh so với 224 (−10%); trong raw, Ultralytics cũng tự bỏ ảnh hỏng/nhãn hỏng, nên số ảnh "thật" của raw thấp hơn 224. *Kiểm:* đọc cảnh báo Ultralytics ở bước 6 của notebook.

**Việc tiếp theo:** chạy thêm seed + biến thể `oracle`, đánh giá trên test đã bỏ ảnh rò rỉ; duyệt nốt 38 ảnh còn cảnh báo rồi train lại. Chưa đủ bằng chứng để nói pipeline làm model tốt hơn; điều chắc chắn là `clean` không còn ảnh rò rỉ test, nên con số của nó **đáng tin hơn**.

## 6. Quyết định và ghi chú AI
**(a) Quyết định: HOLD.** Không phát hành; `clean_v1` chỉ dùng làm bản nháp để thí nghiệm train. Điều kiện để thành **Release**: người duyệt thêm ít nhất **18** trong 38 ảnh còn cảnh báo (để còn ≤ 20/202 < 10%), hoặc tăng ngân sách duyệt cho hết 125 ảnh hàng đợi. **Không** đổi `second_opinion.conf` lên 0,8 chỉ để qua cổng (Release giả, §3).

**(b) Dùng AI (Claude):**
- *Prompt chính:* "Viết 4 module theo GUIDE.md đến khi pytest xanh" (kèm docstring của từng stub), sau đó nhờ chạy calibrate/pipeline.
- *Cách kiểm:* chạy `pytest` (79/79 xanh), đọc lại code theo bảng trong docstring (thứ tự quyết định của `second_opinion`, gom dòng theo file trong `autofix`); chạy `make run` và đối chiếu số trong báo cáo với `08_summary.json`; mở xem bằng mắt các cặp ảnh bị cho là trùng/rò rỉ trước khi chốt `phash_dist`; kiểm `git status` để chắc `data/raw` không bị sửa.
- *Một lần AI sai:* khi chuẩn bị task CVAT, AI gợi ý chọn các ảnh có `BOX_TINY` thay vì "20 ảnh đầu `05_review_queue.csv`" như `docs/CVAT_FILTER.md`, và định lấy nhãn từ lần chạy đầy đủ — lúc đó người duyệt mô phỏng đã chép nhãn đúng đè lên 80 ảnh đầu hàng đợi, nên CVAT sẽ không thấy lỗi. Đã sửa: lấy theo hàng đợi và chạy `--no-review`.

### (Thưởng +2) CVAT: lọc box nhỏ `width < 20`

**Thiết lập.** CVAT tự host (`localhost:8080`), project `AutoQC-Pipeline` tạo từ `cvat/labels.json` (4 nhãn `car, person, truck, bus` đúng thứ tự id, thuộc tính `can_review`). Task `day09-cvat-filter-top20-queue` gồm **20 ảnh đầu `05_review_queue.csv`**, lấy từ `work/run/ds/images/` sau khi chạy `python -m pipeline.run --no-review` **với ngưỡng khởi đầu** (`phash_dist=2`, `conf=0.25`, trước Bước 3; sau calibrate, top-20 hàng đợi mới trùng 11/20 ảnh với tập này): nhãn ở trạng thái **sau autofix, trước người duyệt** (nếu chạy đủ, `human_review_sim` đã chép nhãn tham chiếu đè lên 80 ảnh đầu hàng đợi). Nhãn import dạng YOLO 1.1: **111 box** = đúng tổng số dòng nhãn của 20 ảnh; 4 ảnh `NEEDS_LABEL` (img_0031, img_0053, img_0126, img_0135) không có box.

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
