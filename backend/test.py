from ultralytics import YOLO
m = YOLO("best1.pt")
print(m.task)        # detect / classify / segment
print(m.names)       # class names
print(m.overrides.get("imgsz"))