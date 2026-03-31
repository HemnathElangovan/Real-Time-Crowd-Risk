# detector.py — YOLOv11n person detector
from ultralytics import YOLO
import numpy as np
import config

class CrowdDetector:
    def __init__(self):
        print("[Detector] Loading YOLOv11n...")
        self.model = YOLO(config.MODEL_PATH)
        print("[Detector] Ready.")

    def detect(self, frame: np.ndarray) -> list:
        results = self.model(
            frame,
            classes=[0],
            conf=config.CONFIDENCE_THRESHOLD,
            iou=config.IOU_THRESHOLD,
            verbose=False,
        )[0]

        persons = []
        if results.boxes is None:
            return persons
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf = float(box.conf[0])
            persons.append({
                "bbox": [x1, y1, x2, y2],
                "conf": round(conf, 2),
                "cx":   (x1 + x2) // 2,
                "cy":   (y1 + y2) // 2,
            })
        return persons
