import os
import requests
from PIL import Image
from io import BytesIO
import time

def download_dataset():
    """Download sample images for usable and non-usable materials"""
    
    # Sample image URLs for different materials
    sample_images = {
        'usable': [
            # Good wood planks
            'https://images.unsplash.com/photo-1579226905180-636b76d96082?w=400&h=400&fit=crop',
            # Intact bricks
            'https://images.unsplash.com/photo-1577223625818-75bc1f2ac0e5?w=400&h=400&fit=crop',
            # Good metal sheets
            'https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=400&h=400&fit=crop',
            # Clean glass
            'https://images.unsplash.com/photo-1536922246289-88c42f957773?w=400&h=400&fit=crop',
            # Good plastic
            'https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=400&h=400&fit=crop',
        ],
        'non_usable': [
            # Broken glass
            'https://images.unsplash.com/photo-1563453392212-326f5e854473?w=400&h=400&fit=crop',
            # Rusty metal
            'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=400&h=400&fit=crop',
            # Rotten wood
            'https://images.unsplash.com/photo-1549638441-b787d2e11f14?w=400&h=400&fit=crop',
            # Cracked concrete
            'https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=400&h=400&fit=crop',
            # Damaged plastic
            'https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=400&h=400&fit=crop',
        ]
    }
    
    # Create directories
    os.makedirs('data/raw/usable', exist_ok=True)
    os.makedirs('data/raw/non_usable', exist_ok=True)
    os.makedirs('data/processed/usable', exist_ok=True)
    os.makedirs('data/processed/non_usable', exist_ok=True)
    
    print("Downloading sample dataset...")
    
    for category, urls in sample_images.items():
        print(f"\nDownloading {category} images:")
        for i, url in enumerate(urls):
            try:
                response = requests.get(url)
                img = Image.open(BytesIO(response.content))
                
                # Save to raw folder
                img.save(f'data/raw/{category}/img_{i+1}.jpg')
                
                # Resize and save to processed folder
                img_resized = img.resize((224, 224))
                img_resized.save(f'data/processed/{category}/img_{i+1}.jpg')
                
                print(f"  ✓ Downloaded {category} image {i+1}")
                time.sleep(0.5)  # Be polite to servers
                
            except Exception as e:
                print(f"  ✗ Failed to download {category} image {i+1}: {e}")
    
    print("\n✅ Dataset downloaded successfully!")
    print("You can add your own images to data/raw/usable and data/raw/non_usable folders")

if __name__ == "__main__":
    download_dataset()