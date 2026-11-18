"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).

| code             | severity | khi nào                                                                  |
|------------------|----------|--------------------------------------------------------------------------|
| BAD_FORMAT       | ERROR    | không đúng 5 cột số (dùng `parse_yolo_line`, bắt `ValueError`)           |
| BAD_CLASS_ID     | ERROR    | id lớp ngoài 0..len(ds.classes)-1                                        |
| BOX_ZERO         | ERROR    | w <= 0 hoặc h <= 0                                                       |
| BOX_OUT_OF_IMAGE | ERROR    | mép box vượt [0,1] quá `cfg["label_format"]["overflow_tol"]`; extra={"overflow": mức tràn} |
| DUP_BOX          | ERROR    | cùng lớp với một dòng TRƯỚC ĐÓ và IoU > `dup_box_iou`; báo ở dòng SAU    |
| BOX_TINY         | WARN     | cạnh ngắn của box (px) < `min_box_px`  (cần `ds.image_size(stem)`)       |
| BOX_HUGE         | WARN     | w*h > `max_box_frac`                                                     |

Gợi ý
- Mép trái = x - w/2, mép phải = x + w/2 (xem câu hỏi "dòng YOLO nào lỗi?" trong slide).
- Một dòng hỏng (BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO) thì `continue`, đừng kiểm tiếp hình học của dòng đó.
- Dòng thiếu cột làm script của slide dừng giữa chừng: đây là lý do phải `try/except`.
- `iou_xywh(a, b)` có sẵn trong common.py.
- Ngưỡng nằm trong `cfg["label_format"]` — đừng viết cứng số vào code.
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line  # noqa: F401

NAME = "label_format"


def _edges(cx, cy, w, h):
    return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2


def run(ds, cfg):
    lf = cfg["label_format"]
    tol, min_px = lf["overflow_tol"], lf["min_box_px"]
    max_frac, dup_iou = lf["max_box_frac"], lf["dup_box_iou"]
    n_cls = len(ds.classes)
    issues = []

    for lp in ds.label_files():
        stem = lp.stem
        lines = ds.read_label_lines(stem) or []
        size = ds.image_size(stem) if ds.image_path(stem) else None
        seen = []                                   # (line_no, box) các dòng hợp lệ trước đó

        for no, text in lines:
            # 1) cú pháp
            try:
                c, cx, cy, w, h = parse_yolo_line(text)
            except ValueError as e:
                issues.append(Issue(NAME, ERROR, "BAD_FORMAT", stem, f"dòng không đúng 5 cột số: {e}", no,
                                    {"text": text.strip()[:80]}))
                continue
            # 2) id lớp
            if not 0 <= c < n_cls:
                issues.append(Issue(NAME, ERROR, "BAD_CLASS_ID", stem, f"id lớp {c} ngoài 0..{n_cls - 1}", no, {"class_id": c}))
                continue
            # 3) kích thước
            if w <= 0 or h <= 0:
                issues.append(Issue(NAME, ERROR, "BOX_ZERO", stem, f"box rộng/cao <= 0 (w={w}, h={h})", no))
                continue
            # 4) tràn ảnh
            x1, y1, x2, y2 = _edges(cx, cy, w, h)
            overflow = max(0.0 - x1, 0.0 - y1, x2 - 1.0, y2 - 1.0, 0.0)
            if overflow > tol:
                issues.append(Issue(NAME, ERROR, "BOX_OUT_OF_IMAGE", stem, f"box tràn ảnh {overflow:.4f}", no,
                                    {"overflow": round(overflow, 6)}))
            # 5) box lặp (cùng lớp với dòng TRƯỚC, IoU > ngưỡng) -> báo ở dòng sau
            box = (cx, cy, w, h)
            for prev_no, (pc, pbox) in seen:
                if pc == c:
                    iou = iou_xywh(box, pbox)
                    if iou > dup_iou:
                        issues.append(Issue(NAME, ERROR, "DUP_BOX", stem, f"trùng box dòng {prev_no} (IoU {iou:.2f})", no,
                                            {"dup_of": prev_no, "iou": round(iou, 4)}))
                        break
            seen.append((no, (c, box)))
            # 6) cảnh báo kích thước
            if size:
                W, H = size
                short = min(w * W, h * H)
                if short < min_px:
                    issues.append(Issue(NAME, WARN, "BOX_TINY", stem, f"cạnh ngắn {short:.1f}px < {min_px}px", no,
                                        {"short_px": round(short, 2)}))
            if w * h > max_frac:
                issues.append(Issue(NAME, WARN, "BOX_HUGE", stem, f"box phủ {w * h:.0%} ảnh", no, {"area_frac": round(w * h, 4)}))
    return issues
