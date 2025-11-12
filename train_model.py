import tensorflow as tf
import os

# --- Configuration ---
# This section contains all the settings you might want to tweak.

# 1. Dataset Location
DATASET_PATH = 'landmark_dataset'

# 2. Model Configuration
IMG_HEIGHT = 224 # Image height in pixels
IMG_WIDTH = 224  # Image width in pixels
BATCH_SIZE = 32  # How many images to process at once
EPOCHS = 15      # How many times to go through the entire dataset. 
                 # Start with 15, you can increase this later for better accuracy.

# 3. Output File Names
SAVED_MODEL_NAME = 'landmark_recognizer.keras'
TFLITE_MODEL_NAME = 'model.tflite'
LABELS_FILE_NAME = 'labels.txt'

# --- Main Training Script ---

def main():
    print(f"--- Starting Model Training ---")
    print(f"TensorFlow Version: {tf.__version__}")

    # 1. Load the dataset from the folder structure
    # TensorFlow can automatically infer the classes (labels) from the subfolder names.
    print(f"Loading training data from: '{DATASET_PATH}'")
    
    # Create a dataset for training (80% of the images)
    train_dataset = tf.keras.utils.image_dataset_from_directory(
        DATASET_PATH,
        validation_split=0.2, # Reserve 20% of images for validation
        subset="training",
        seed=123,
        image_size=(IMG_HEIGHT, IMG_WIDTH),
        batch_size=BATCH_SIZE
    )

    # Create a dataset for validation (the 20% we reserved)
    validation_dataset = tf.keras.utils.image_dataset_from_directory(
        DATASET_PATH,
        validation_split=0.2,
        subset="validation",
        seed=123,
        image_size=(IMG_HEIGHT, IMG_WIDTH),
        batch_size=BATCH_SIZE
    )

    # Get the class names from the dataset folders (e.g., ['entrance', 'library'])
    class_names = train_dataset.class_names
    print(f"Found classes: {class_names}")

    # Configure the dataset for performance
    AUTOTUNE = tf.data.AUTOTUNE
    train_dataset = train_dataset.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
    validation_dataset = validation_dataset.cache().prefetch(buffer_size=AUTOTUNE)
    
    # 2. Build the model architecture
    # We use a pre-trained model (MobileNetV2) as a base for faster and better results.
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(IMG_HEIGHT, IMG_WIDTH, 3),
        include_top=False, # Don't include the final classification layer
        weights='imagenet' # Use weights pre-trained on the ImageNet dataset
    )
    base_model.trainable = False # Freeze the base model layers

    model = tf.keras.Sequential([
        # Add a layer to automatically normalize pixel values
        tf.keras.layers.Rescaling(1./255),
        # The pre-trained base model
        base_model,
        # Flatten the output to a 1D vector
        tf.keras.layers.GlobalAveragePooling2D(),
        # A dropout layer to prevent overfitting
        tf.keras.layers.Dropout(0.2),
        # The final decision layer with one output neuron for each class
        tf.keras.layers.Dense(len(class_names), activation='softmax')
    ])
    
    # 3. Compile the model
    # This prepares the model for training by setting the optimizer, loss function, and metrics.
    model.compile(
        optimizer='adam',
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=['accuracy']
    )
    
    print("\n--- Model Summary ---")
    model.summary()
    
    # 4. Train the model
    print(f"\n--- Training for {EPOCHS} epochs ---")
    history = model.fit(
        train_dataset,
        validation_data=validation_dataset,
        epochs=EPOCHS
    )
    
    print("\n--- Training Complete ---")
    
    # 5. Save the trained Keras model
    print(f"Saving Keras model to: {SAVED_MODEL_NAME}")
    model.save(SAVED_MODEL_NAME)
    
    # 6. Convert the model to TensorFlow Lite (Quantized)
    print(f"\n--- Converting to TensorFlow Lite ---")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT] # This enables quantization
    tflite_model = converter.convert()
    
    # Save the TFLite model to a file
    with open(TFLITE_MODEL_NAME, 'wb') as f:
        f.write(tflite_model)
    print(f"Successfully saved TFLite model to: {TFLITE_MODEL_NAME}")
        
    # 7. Create the labels file
    print(f"Saving labels to: {LABELS_FILE_NAME}")
    with open(LABELS_FILE_NAME, 'w') as f:
        for item in class_names:
            f.write(f"{item}\n")
    print("--- All Done! ---")


# This makes the script runnable from the command line
if __name__ == '__main__':
    main()