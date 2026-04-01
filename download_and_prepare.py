# download_and_prepare.py
import opendatasets as od
import zipfile
import os
import shutil
from sklearn.model_selection import train_test_split
import random

print("🚀 Downloading dataset from Kaggle...")
# Download the dataset (you'll need to input your Kaggle username/key once)
dataset_url = "https://www.kaggle.com/datasets/samuelayman/object-detection"
od.download(dataset_url)

print("✅ Download complete. Extracting and organizing...")
# Extract the main zip
with zipfile.ZipFile("object-detection.zip", 'r') as zip_ref:
    zip_ref.extractall("temp_dataset/")

# The dataset has 4 batches. We'll combine them.
os.makedirs("data/images/train", exist_ok=True)
os.makedirs("data/images/val", exist_ok=True)
os.makedirs("data/labels/train", exist_ok=True)
os.makedirs("data/labels/val", exist_ok=True)

all_images = []
# Find all images and their corresponding label files
for batch in ["Batch 1", "Batch 2", "Batch 3", "Batch 4"]:
    batch_path = f"temp_dataset/final batches/{batch}"
    if os.path.exists(batch_path):
        # Assuming structure inside each batch: images/ and labels/
        img_dir = os.path.join(batch_path, "images")
        lbl_dir = os.path.join(batch_path, "labels")
        
        if os.path.exists(img_dir):
            for img_file in os.listdir(img_dir):
                if img_file.endswith(('.jpg', '.jpeg', '.png')):
                    base_name = os.path.splitext(img_file)[0]
                    # Check if corresponding label exists
                    lbl_file = os.path.join(lbl_dir, base_name + ".txt")
                    if os.path.exists(lbl_file):
                        all_images.append((os.path.join(img_dir, img_file), lbl_file))

print(f"Found {len(all_images)} images with labels.")

# Split into train (80%) and val (20%)
random.shuffle(all_images)
split_idx = int(len(all_images) * 0.8)
train_files = all_images[:split_idx]
val_files = all_images[split_idx:]

# Copy files to the YOLO structure
print("Copying training files...")
for img_path, lbl_path in train_files:
    shutil.copy(img_path, "data/images/train/")
    shutil.copy(lbl_path, "data/labels/train/")

print("Copying validation files...")
for img_path, lbl_path in val_files:
    shutil.copy(img_path, "data/images/val/")
    shutil.copy(lbl_path, "data/labels/val/")

# Clean up temp files
shutil.rmtree("temp_dataset")
os.remove("object-detection.zip")

print("🎉 Dataset preparation complete!")
print(f"Train images: {len(train_files)}, Val images: {len(val_files)}")