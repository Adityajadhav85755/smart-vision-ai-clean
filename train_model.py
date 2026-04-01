import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.model_selection import train_test_split
import cv2
import matplotlib.pyplot as plt

class MaterialClassifier:
    def __init__(self):
        self.model = None
        self.img_size = (224, 224)
        
    def load_data(self):
        """Load and preprocess images from data/processed folder"""
        usable_path = 'data/processed/usable'
        non_usable_path = 'data/processed/non_usable'
        
        images = []
        labels = []
        
        # Load usable materials (label 1)
        print("Loading usable materials...")
        for img_name in os.listdir(usable_path):
            if img_name.endswith(('.jpg', '.png', '.jpeg')):
                img_path = os.path.join(usable_path, img_name)
                img = cv2.imread(img_path)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = cv2.resize(img, self.img_size)
                images.append(img)
                labels.append(1)  # 1 for usable
                
        # Load non-usable materials (label 0)
        print("Loading non-usable materials...")
        for img_name in os.listdir(non_usable_path):
            if img_name.endswith(('.jpg', '.png', '.jpeg')):
                img_path = os.path.join(non_usable_path, img_name)
                img = cv2.imread(img_path)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = cv2.resize(img, self.img_size)
                images.append(img)
                labels.append(0)  # 0 for non-usable
        
        # Convert to numpy arrays
        X = np.array(images) / 255.0  # Normalize
        y = np.array(labels)
        
        print(f"Loaded {len(X)} images")
        print(f"Usable: {sum(y)}, Non-usable: {len(y)-sum(y)}")
        
        return train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    def create_model(self):
        """Create CNN model for material classification"""
        model = keras.Sequential([
            # Input layer
            layers.Input(shape=(224, 224, 3)),
            
            # First convolutional block
            layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
            layers.BatchNormalization(),
            layers.MaxPooling2D((2, 2)),
            
            # Second convolutional block
            layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
            layers.BatchNormalization(),
            layers.MaxPooling2D((2, 2)),
            
            # Third convolutional block
            layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
            layers.BatchNormalization(),
            layers.MaxPooling2D((2, 2)),
            
            # Fourth convolutional block
            layers.Conv2D(256, (3, 3), activation='relu', padding='same'),
            layers.BatchNormalization(),
            layers.MaxPooling2D((2, 2)),
            
            # Flatten and dense layers
            layers.Flatten(),
            layers.Dropout(0.5),
            layers.Dense(128, activation='relu'),
            layers.Dense(64, activation='relu'),
            
            # Output layer
            layers.Dense(1, activation='sigmoid')
        ])
        
        # Compile the model
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.0001),
            loss='binary_crossentropy',
            metrics=['accuracy', keras.metrics.Precision(), keras.metrics.Recall()]
        )
        
        return model
    
    def train(self, X_train, X_val, y_train, y_val, epochs=50):
        """Train the model with data augmentation"""
        
        # Data augmentation
        datagen = ImageDataGenerator(
            rotation_range=20,
            width_shift_range=0.2,
            height_shift_range=0.2,
            shear_range=0.2,
            zoom_range=0.2,
            horizontal_flip=True,
            fill_mode='nearest'
        )
        
        # Create model
        self.model = self.create_model()
        
        print("Model architecture:")
        self.model.summary()
        
        # Callbacks
        callbacks = [
            keras.callbacks.EarlyStopping(
                patience=10,
                restore_best_weights=True,
                monitor='val_accuracy'
            ),
            keras.callbacks.ReduceLROnPlateau(
                factor=0.5,
                patience=5,
                min_lr=0.00001
            )
        ]
        
        # Train the model
        print("\nStarting training...")
        history = self.model.fit(
            datagen.flow(X_train, y_train, batch_size=16),
            validation_data=(X_val, y_val),
            epochs=epochs,
            callbacks=callbacks,
            verbose=1
        )
        
        return history
    
    def evaluate(self, X_test, y_test):
        """Evaluate model performance"""
        if self.model:
            loss, accuracy, precision, recall = self.model.evaluate(X_test, y_test)
            print(f"\nTest Accuracy: {accuracy:.4f}")
            print(f"Test Precision: {precision:.4f}")
            print(f"Test Recall: {recall:.4f}")
            
            # Calculate F1-score
            f1 = 2 * (precision * recall) / (precision + recall)
            print(f"Test F1-Score: {f1:.4f}")
    
    def save_model(self, path='models/material_classifier.h5'):
        """Save trained model"""
        os.makedirs('models', exist_ok=True)
        self.model.save(path)
        print(f"\n✅ Model saved to {path}")
    
    def plot_training_history(self, history):
        """Plot training history"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        
        # Accuracy plot
        axes[0].plot(history.history['accuracy'], label='Training Accuracy')
        axes[0].plot(history.history['val_accuracy'], label='Validation Accuracy')
        axes[0].set_title('Model Accuracy')
        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('Accuracy')
        axes[0].legend()
        axes[0].grid(True)
        
        # Loss plot
        axes[1].plot(history.history['loss'], label='Training Loss')
        axes[1].plot(history.history['val_loss'], label='Validation Loss')
        axes[1].set_title('Model Loss')
        axes[1].set_xlabel('Epoch')
        axes[1].set_ylabel('Loss')
        axes[1].legend()
        axes[1].grid(True)
        
        plt.tight_layout()
        plt.savefig('models/training_history.png')
        plt.show()

def main():
    # Initialize classifier
    classifier = MaterialClassifier()
    
    # Load data
    print("Loading data...")
    X_train, X_test, y_train, y_test = classifier.load_data()
    
    # Train model
    print("\nTraining model...")
    history = classifier.train(X_train, X_test, y_train, y_test, epochs=30)
    
    # Evaluate model
    print("\nEvaluating model...")
    classifier.evaluate(X_test, y_test)
    
    # Save model
    classifier.save_model()
    
    # Plot training history
    classifier.plot_training_history(history)
    
    print("\n🎉 Training completed successfully!")

if __name__ == "__main__":
    main()