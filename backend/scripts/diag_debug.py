# Run from backend/:  python scripts/diag_debug.py test_images/leaf1.jpg potato
import sys
from pathlib import Path
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent
img = sys.argv[1]
crop = (sys.argv[2] if len(sys.argv) > 2 else "").lower()
crop = {"capsicum": "pepper"}.get(crop, crop)

det = YOLO(str(ROOT / "weights" / "best.onnx"), task="detect")
r = det.predict(img, conf=0.05, imgsz=640, verbose=False)[0]
H, W = r.orig_shape
print("DETECTOR best.onnx (conf >= 0.05):")
rows = sorted(zip(r.boxes.conf.tolist(), r.boxes.cls.tolist(), r.boxes.xyxy.tolist()), reverse=True)
for conf, c, (x1, y1, x2, y2) in rows[:8]:
    print(f"  {r.names[int(c)]:36s} {conf:.2f}  box = {(x2-x1)*(y2-y1)/(W*H):.0%} of image")
if not rows:
    print("  (nothing)")

clf = ROOT / "agent" / "model" / "classifier.onnx"
if clf.exists():
    m = YOLO(str(clf), task="classify")
    p = m.predict(img, imgsz=224, verbose=False)[0]
    pr = p.probs.data.tolist()
    ranked = sorted(((pr[i], p.names[i]) for i in range(len(pr))), reverse=True)
    print("\nCLASSIFIER overall top 5:", [(n, round(s, 2)) for s, n in ranked[:5]])
    if crop:
        keep = [(s, n) for s, n in ranked if n.lower().startswith(crop)]
        mass = sum(s for s, _ in keep)
        print(f"  probability mass on '{crop}': {mass:.2f}; within crop:",
              [(n, round(s / (mass or 1), 2)) for s, n in keep[:4]])