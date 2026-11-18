"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict  # noqa: F401

import yaml  # noqa: F401

from ..common import ERROR, parse_yolo_line  # noqa: F401

DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
CLIP_CODES = {"BOX_OUT_OF_IMAGE"}
REMOVE_CODES = {"DUP_IMAGE_EXACT", "DUP_IMAGE_NEAR", "LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def _fmt(v):
    return f"{v:.6f}".rstrip("0").rstrip(".") or "0"


def _clip(text):
    """Cắt box về [0,1]. Trả dòng mới, hoặc None nếu box không còn diện tích / không parse được."""
    try:
        c, cx, cy, w, h = parse_yolo_line(text)
    except ValueError:
        return None
    x1, y1 = max(0.0, cx - w / 2), max(0.0, cy - h / 2)
    x2, y2 = min(1.0, cx + w / 2), min(1.0, cy + h / 2)
    nw, nh = x2 - x1, y2 - y1
    if nw <= 1e-9 or nh <= 1e-9:
        return None
    return " ".join([str(c), _fmt((x1 + x2) / 2), _fmt((y1 + y2) / 2), _fmt(nw), _fmt(nh)])


def _remove_image(ds, stem):
    """Xoá ảnh + nhãn khỏi ds. Trả True nếu thực sự xoá được gì đó."""
    done = False
    img = ds.image_path(stem)
    if img is not None and img.exists():
        img.unlink()
        done = True
    lab = ds.label_path(stem)
    if lab.exists():
        lab.unlink()
        done = True
    return done


def _rename_classes(ds, cfg):
    old = ds.yaml_names()
    want = {i: n for i, n in enumerate(cfg["classes"])}
    if old == want:
        return None
    d = {}
    if ds.yaml_path.exists():
        d = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) or {}
    d["names"] = want
    d["nc"] = len(want)
    ds.yaml_path.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return {"image": "data.yaml", "line": None, "action": "rename_classes",
            "before": str([old[k] for k in sorted(old)]), "after": str(cfg["classes"])}


def fix(ds, issues, cfg):
    errors = [i for i in issues if i.severity == ERROR]
    fixes = []

    # 1) Ảnh phải loại bỏ (làm trước: các issue dòng của ảnh đó sẽ bị bỏ qua)
    removed = set()
    for i in errors:
        if i.code in REMOVE_CODES and i.image not in removed:
            removed.add(i.image)
            if _remove_image(ds, i.image):
                fixes.append({"image": i.image, "line": None, "action": "remove_image",
                              "before": i.code, "after": "đã xoá ảnh + nhãn"})

    # 2) data.yaml
    if any(i.code == "BAD_CLASS_NAME" for i in errors):
        f = _rename_classes(ds, cfg)
        if f:
            fixes.append(f)

    # 3) Ảnh thiếu nhãn: KHÔNG bịa nhãn, chuyển người gán
    flagged = set()
    for i in errors:
        if i.code == "MISSING_LABEL_FILE" and i.image not in removed and i.image not in flagged:
            flagged.add(i.image)
            if ds.image_path(i.image) is not None and not ds.label_path(i.image).exists():
                fixes.append({"image": i.image, "line": None, "action": "needs_label",
                              "before": "(không có file)", "after": "chuyển người gán"})

    # 4) Lỗi theo dòng: gom theo file, ghi lại MỘT lần (số dòng là số GỐC)
    per_file = defaultdict(lambda: defaultdict(set))          # stem -> line -> {codes}
    for i in errors:
        if i.line is not None and (i.code in DROP_CODES or i.code in CLIP_CODES) and i.image not in removed:
            per_file[i.image][int(i.line)].add(i.code)

    for stem in sorted(per_file):
        lp = ds.label_path(stem)
        if not lp.exists():
            continue
        raw = lp.read_text(encoding="utf-8", errors="replace").splitlines()
        out, changed = [], False
        for no, text in enumerate(raw, 1):
            codes = per_file[stem].get(no)
            if not codes or not text.strip():
                out.append(text)
                continue
            if codes & DROP_CODES:                                 # xoá dòng thắng, không clip thêm
                fixes.append({"image": stem, "line": no, "action": "drop_line", "before": text, "after": ""})
                changed = True
                continue
            new = _clip(text)
            if new is None:                                       # cắt xong không còn diện tích -> xoá
                fixes.append({"image": stem, "line": no, "action": "drop_line", "before": text, "after": ""})
                changed = True
            elif new != text:
                fixes.append({"image": stem, "line": no, "action": "clip_box", "before": text, "after": new})
                out.append(new)
                changed = True
            else:
                out.append(text)
        if changed:
            lp.write_text("".join(l + "\n" for l in out), encoding="utf-8")
    return fixes
