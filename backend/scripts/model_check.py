# Run from backend/: python scripts/onnx_predict.py [optional_image_path]
import sys
from pathlib import Path
import cv2
from ultralytics import YOLO

# Directory setup
ROOT = Path(__file__).resolve().parent.parent
ONNX_PATH = ROOT / "weights" / "best.onnx"
TEST_IMAGES_DIR = ROOT / "test_images"
OUT_DIR = ROOT / "test_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def run_onnx_inference():
    if not ONNX_PATH.exists():
        sys.exit(f"Error: ONNX file not found at {ONNX_PATH}")

    # Load ONNX model directly
    model = YOLO(str(ONNX_PATH), task="detect")

    # Get input image(s)
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    if len(sys.argv) > 1:
        images = [Path(sys.argv[1])]
    else:
        images = sorted(p for p in TEST_IMAGES_DIR.glob("*") if p.suffix.lower() in exts)

    if not images:
        sys.exit(f"No test images found in {TEST_IMAGES_DIR}")

    print(f"Running ONNX inference on {len(images)} image(s)...")

    for img_path in images:
        # Run prediction
        results = model.predict(str(img_path), conf=0.25, imgsz=640, verbose=False)[0]

        print(f"\nImage: {img_path.name}")
        if len(results.boxes) == 0:
            print("  No objects detected.")
        else:
            for box in results.boxes:
                cls_id = int(box.cls[0])
                class_name = model.names[cls_id]
                confidence = float(box.conf[0])
                print(f"  • {class_name}: {confidence * 100:.1f}%")

        # Save annotated image
        output_path = OUT_DIR / f"{img_path.stem}_onnx_annotated.jpg"
        cv2.imwrite(str(output_path), results.plot())
        print(f"  Saved visual: {output_path.relative_to(ROOT)}")

if __name__ == "__main__":
    run_onnx_inference()