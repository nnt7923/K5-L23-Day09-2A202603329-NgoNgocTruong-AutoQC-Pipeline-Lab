"""BƯỚC 4 — Cửa chặn: quyết định Release / Hold / Rework.   ★

Test:  pytest tests/test_gate.py -q

Cây quyết định Day 07 (slide Day 09: "Lỗi bắt buộc chặn pipeline; lỗi cảnh báo chuyển người xem"):

  còn ≥ 1 lỗi bắt buộc (severity ERROR)                          -> "Rework"
  không còn lỗi bắt buộc, nhưng tỉ lệ ẢNH còn cảnh báo
      >= cfg["gate"]["warn_ratio_hold"]                          -> "Hold"
  còn lại                                                        -> "Release"

Tỉ lệ cảnh báo = (số ẢNH khác nhau có ≥ 1 cảnh báo) / (tổng số ảnh).  Chú ý:
- chỉ đếm issue có `image` nằm trong `image_stems` (bỏ "<dataset>", "data.yaml");
- bỏ qua ảnh nằm trong `reviewed` (người đã xem, cảnh báo của ảnh đó coi như đã xử lý) — nhưng LỖI BẮT BUỘC thì không bao giờ được bỏ qua;
- mẫu số là số ảnh, không phải số issue.

Trả về dict: decision, n_errors, n_warn_images, n_images, warn_ratio (làm tròn 4 chữ số), reasons (list[str], giải thích bằng tiếng Việt, có số liệu).
"""
from ..common import ERROR, WARN  # noqa: F401


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    stems = set(image_stems)
    reviewed = set(reviewed)
    hold_at = cfg["gate"]["warn_ratio_hold"]

    errors = [i for i in issues if i.severity == ERROR]          # lỗi bắt buộc: KHÔNG bao giờ bỏ qua
    warn_images = {i.image for i in issues
                   if i.severity == WARN and i.image in stems and i.image not in reviewed}
    n_images = len(stems)
    ratio = round(len(warn_images) / n_images, 4) if n_images else 0.0

    reasons = []
    if errors:
        decision = "Rework"
        by_code = {}
        for i in errors:
            by_code[i.code] = by_code.get(i.code, 0) + 1
        detail = ", ".join(f"{k}: {v}" for k, v in sorted(by_code.items()))
        reasons.append(f"Còn {len(errors)} lỗi bắt buộc ({detail}) -> phải sửa lại, không xuất dataset.")
    elif ratio >= hold_at:
        decision = "Hold"
        reasons.append(f"Không còn lỗi bắt buộc, nhưng {len(warn_images)}/{n_images} ảnh ({ratio:.1%}) còn cảnh báo "
                       f"chưa được người duyệt, >= ngưỡng {hold_at:.0%} -> giữ lại chờ duyệt.")
    else:
        decision = "Release"
        reasons.append(f"Không còn lỗi bắt buộc; {len(warn_images)}/{n_images} ảnh ({ratio:.1%}) còn cảnh báo chưa duyệt, "
                       f"< ngưỡng {hold_at:.0%} -> phát hành.")
    if reviewed:
        reasons.append(f"{len(reviewed & stems)} ảnh đã được người duyệt (cảnh báo của các ảnh này coi như đã xử lý).")

    return {
        "decision": decision,
        "n_errors": len(errors),
        "n_warn_images": len(warn_images),
        "n_images": n_images,
        "warn_ratio": ratio,
        "reasons": reasons,
    }
