# test_model.py
from ultralytics import YOLO
import cv2
import glob
import os

# Load your trained model
model = YOLO('models/yolov8n_35class/weights/best.pt')

# Get a few validation images
val_images = glob.glob('data/images/val/*.jpg')[:5]  # test first 5

for img_path in val_images:
    print(f"\n🔍 Testing: {os.path.basename(img_path)}")
    
    # Run inference
    results = model(img_path)
    
    # Display results
    for r in results:
        boxes = r.boxes
        for box in boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            class_name = model.names[cls]
            print(f"   - Detected: {class_name} (confidence: {conf:.2f})")
    
    # Save the result image with bounding boxes
    result_img = results[0].plot()  # returns an image with detections plotted
    output_path = f"test_results/{os.path.basename(img_path)}"
    os.makedirs("test_results", exist_ok=True)
    cv2.imwrite(output_path, result_img)
    print(f"   ✅ Result saved to: {output_path}")