import os
import cv2
import numpy as np
import shutil

print("=" * 60)
print("SMART VISION AI - DATASET CREATOR")
print("=" * 60)
print("\nCreating synthetic dataset for training...")

# Create directories
os.makedirs('data/raw/usable', exist_ok=True)
os.makedirs('data/raw/non_usable', exist_ok=True)
os.makedirs('data/processed/usable', exist_ok=True)
os.makedirs('data/processed/non_usable', exist_ok=True)

print("✓ Created folder structure")

# Create sample images
print("\nCreating sample images...")
image_count = 20  # 10 usable + 10 non-usable

for i in range(image_count // 2):  # 10 images each
    try:
        # 1. USABLE MATERIALS (clean, organized patterns)
        # Good wood
        wood_img = np.ones((300, 400, 3), dtype=np.uint8) * 180
        wood_img[:, :, 0] = 100  # Blue channel
        wood_img[:, :, 1] = 150  # Green channel (makes brown)
        # Add wood grain
        for j in range(20):
            x = np.random.randint(0, 400)
            cv2.line(wood_img, (x, 0), (x, 300), (120, 130, 140), 2)
        
        # Good metal
        metal_img = np.ones((300, 400, 3), dtype=np.uint8) * 200
        # Add shiny spots
        for _ in range(30):
            x, y = np.random.randint(0, 400), np.random.randint(0, 300)
            cv2.circle(metal_img, (x, y), np.random.randint(2, 6), (255, 255, 255), -1)
        
        # Save usable materials
        cv2.imwrite(f'data/raw/usable/wood_{i+1}.jpg', wood_img)
        cv2.imwrite(f'data/raw/usable/metal_{i+1}.jpg', metal_img)
        
        # Resize and save to processed
        wood_resized = cv2.resize(wood_img, (224, 224))
        metal_resized = cv2.resize(metal_img, (224, 224))
        cv2.imwrite(f'data/processed/usable/wood_{i+1}.jpg', wood_resized)
        cv2.imwrite(f'data/processed/usable/metal_{i+1}.jpg', metal_resized)
        
        # 2. NON-USABLE MATERIALS (damaged, dirty patterns)
        # Broken glass
        glass_img = np.ones((300, 400, 3), dtype=np.uint8) * 220
        glass_img[:, :, 0] = 240  # Blue tint
        # Add cracks
        for _ in range(8):
            x1, y1 = np.random.randint(0, 400), np.random.randint(0, 300)
            x2, y2 = np.random.randint(0, 400), np.random.randint(0, 300)
            cv2.line(glass_img, (x1, y1), (x2, y2), (150, 150, 150), 3)
        
        # Rusty metal
        rusty_img = np.ones((300, 400, 3), dtype=np.uint8) * 100
        rusty_img[:, :, 2] = 80  # Red tint for rust
        # Add rust spots
        for _ in range(50):
            x, y = np.random.randint(0, 400), np.random.randint(0, 300)
            radius = np.random.randint(3, 10)
            color = (0, np.random.randint(30, 70), np.random.randint(80, 120))
            cv2.circle(rusty_img, (x, y), radius, color, -1)
        
        # Save non-usable materials
        cv2.imwrite(f'data/raw/non_usable/glass_{i+1}.jpg', glass_img)
        cv2.imwrite(f'data/raw/non_usable/rusty_{i+1}.jpg', rusty_img)
        
        # Resize and save to processed
        glass_resized = cv2.resize(glass_img, (224, 224))
        rusty_resized = cv2.resize(rusty_img, (224, 224))
        cv2.imwrite(f'data/processed/non_usable/glass_{i+1}.jpg', glass_resized)
        cv2.imwrite(f'data/processed/non_usable/rusty_{i+1}.jpg', rusty_resized)
        
        print(f"✓ Created batch {i+1}/10")
        
    except Exception as e:
        print(f"✗ Error in batch {i+1}: {e}")

# Count files
usable_count = len(os.listdir('data/raw/usable'))
non_usable_count = len(os.listdir('data/raw/non_usable'))

print("\n" + "=" * 60)
print("DATASET CREATION COMPLETE!")
print("=" * 60)
print(f"\n📊 Statistics:")
print(f"  Usable materials: {usable_count} images")
print(f"  Non-usable materials: {non_usable_count} images")
print(f"  Total: {usable_count + non_usable_count} images")

print("\n📁 Files created in:")
print(f"  Raw images: data/raw/")
print(f"  Processed images: data/processed/")

print("\n✅ Dataset is ready for training!")
print("\nNext step: Run 'python train_model.py' to train the AI model")
print("=" * 60)

# Show sample of created images
print("\n💡 Tip: You can add your own real images to these folders:")
print("  - Add good materials to: data/raw/usable/")
print("  - Add damaged materials to: data/raw/non_usable/")
print("Then run the training again for better accuracy!")