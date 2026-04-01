# train_yolo.py
from ultralytics import YOLO
import torch

def main():
    print("🏁 Starting YOLO training...")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    # Load a pre-trained YOLOv8 model
    # 'n' for nano (fastest), 's' for small, 'm' for medium, 'l' for large
    model = YOLO('yolov8n.pt')  
    
    # Train the model
    results = model.train(
        data='data.yaml',          # path to data.yaml
        epochs=100,                # number of training epochs
        imgsz=640,                 # input image size
        batch=16,                  # batch size (reduce if you run out of memory)
        name='yolov8n_35class',    # name of the training run
        device=0,                   # GPU device (0 for first GPU, 'cpu' for CPU)
        patience=20,                # epochs to wait for no improvement to stop
        save=True,                  # save checkpoints
        save_period=10,             # save checkpoint every 10 epochs
        cache=True,                 # cache images for faster training
        workers=8,                  # number of data loading workers
        project='models',           # directory to save results
        exist_ok=True,               # overwrite existing project folder
        pretrained=True,             # use pretrained weights
        optimizer='auto',             # optimizer
        verbose=True                 # print verbose output
    )
    
    print("✅ Training complete!")
    print("Model saved in: models/yolov8n_35class/weights/best.pt")

if __name__ == "__main__":
    main()