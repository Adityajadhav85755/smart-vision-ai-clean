import opendatasets as od
import zipfile
import os
import shutil

print("Downloading dataset from Kaggle...")
# Download the dataset
od.download("")

print("Extracting files...")
with zipfile.ZipFile("object-detection.zip", 'r') as zip_ref:
    zip_ref.extractall("temp_dataset")

# Create necessary folders
os.makedirs("data/images/train", exist_ok=True)
os.makedirs("data/images/val", exist_ok=True)
os.makedirs("data/labels/train", exist_ok=True)
os.makedirs("data/labels/val", exist_ok=True)

# Copy images to your data folder
for batch in ["Batch 1", "Batch 2", "Batch 3", "Batch 4"]:
    batch_path = f"temp_dataset/final batches/{batch}"
    if os.path.exists(batch_path):
        # Copy images
        img_dir = os.path.join(batch_path, "images")
        if os.path.exists(img_dir):
            for img in os.listdir(img_dir):
                if img.endswith(('.jpg', '.png', '.jpeg')):
                    shutil.copy(os.path.join(img_dir, img), "data/images/train/")
        
        # Copy labels
        lbl_dir = os.path.join(batch_path, "labels")
        if os.path.exists(lbl_dir):
            for lbl in os.listdir(lbl_dir):
                if lbl.endswith('.txt'):
                    shutil.copy(os.path.join(lbl_dir, lbl), "data/labels/train/")

# Clean up
shutil.rmtree("temp_dataset")
os.remove("object-detection.zip")

print("✅ Dataset downloaded and organized!")
print(f"Images in train: {len(os.listdir('data/images/train/'))}")