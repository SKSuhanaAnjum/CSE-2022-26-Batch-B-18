import cv2
from ultralytics import YOLO
import numpy as np

# Load YOLOv8 model
model = YOLO('best.pt')

# Class ID to Label mapping
class_map = {
    0: "Backgroud",
    1: "Acid Pollution",
    2: "Dead Animals Pollution",
    3: "Eutrophication Pollution",
    4: "Fish",
    5: "Oil Pollution",
    6: "Plastic Pollution",
    7: "bottle",
    8: "cardboard",
    9: "glass",
    10: "leaf",
    11: "metal",
    12: "paper",
    13: "plastic",
    14: "pmb",
    15: "sld",
    16: "slh",
    17: "trash_plastic",
    18: "water",
    19: "waterbottle"  
   
    
}
# Open webcam
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Convert frame to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Run prediction
    results = model.predict(source=rgb_frame, conf=0.3, save=False, verbose=False)
    result = results[0]
    annotated_frame = result.plot()

    # Draw class labels with confidence
    if result.boxes is not None and len(result.boxes) > 0:
        for box in result.boxes:
            cls_id = int(box.cls.cpu())
            conf = float(box.conf.cpu().numpy()[0])
            label = f"{class_map.get(cls_id, 'Unknown')} {conf:.2f}"
            x1, y1, x2, y2 = map(int, box.xyxy.cpu().numpy()[0])
            cv2.putText(annotated_frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Show annotated frame
    cv2.imshow("Polutant Detection", annotated_frame)

    # Exit on 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()


