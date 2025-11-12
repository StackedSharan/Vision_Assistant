import cv2
import os
import shutil

# --- Configuration ---
# The folder where you stored your recorded landmark videos.
VIDEO_SOURCE_FOLDER = 'landmark_videos'
# The folder where the script will save the image frames. This will be created.
OUTPUT_DATASET_FOLDER = 'landmark_dataset'
# How many frames to skip between saves.
# A value of 10 means it saves a frame roughly 3 times per second for a 30fps video.
# Adjust this if you get too many or too few frames.
FRAME_SKIP = 10

# --- Main Script ---

def extract_frames():
    """
    Processes all videos in the source folder, extracts frames, and saves them
    into a structured dataset folder.
    """
    print("--- Starting Frame Extraction Process ---")

    # 1. Check if the video source folder exists
    if not os.path.exists(VIDEO_SOURCE_FOLDER):
        print(f"Error: The source folder '{VIDEO_SOURCE_FOLDER}' was not found.")
        print("Please make sure you have created it and placed your videos inside.")
        return

    # 2. Create the main output dataset folder
    # If it already exists, delete it and its contents to start fresh
    if os.path.exists(OUTPUT_DATASET_FOLDER):
        print(f"'{OUTPUT_DATASET_FOLDER}' already exists. Deleting it to create a fresh dataset.")
        shutil.rmtree(OUTPUT_DATASET_FOLDER)
    
    os.makedirs(OUTPUT_DATASET_FOLDER)
    print(f"Successfully created main dataset folder: '{OUTPUT_DATASET_FOLDER}'")

    # 3. Get a list of all video files in the source folder
    try:
        video_files = [f for f in os.listdir(VIDEO_SOURCE_FOLDER) if f.lower().endswith(('.mp4', '.mov', '.avi'))]
    except Exception as e:
        print(f"Error reading the video source folder: {e}")
        return

    if not video_files:
        print(f"Warning: No video files (.mp4, .mov, .avi) found in '{VIDEO_SOURCE_FOLDER}'.")
        return

    # 4. Loop through each video file and process it
    for video_filename in video_files:
        # Get the landmark name from the filename (e.g., "library.mp4" -> "library")
        landmark_name = os.path.splitext(video_filename)[0]
        
        # Create a specific subfolder for this landmark's frames
        landmark_folder_path = os.path.join(OUTPUT_DATASET_FOLDER, landmark_name)
        os.makedirs(landmark_folder_path)
        
        print(f"\nProcessing video: '{video_filename}' for landmark: '{landmark_name}'")

        # Construct the full path to the video file
        video_path = os.path.join(VIDEO_SOURCE_FOLDER, video_filename)
        
        try:
            # Open the video file
            video_capture = cv2.VideoCapture(video_path)
            if not video_capture.isOpened():
                print(f"  Error: Could not open video file {video_filename}")
                continue # Skip to the next video

            frame_count = 0
            saved_frame_count = 0

            # Read frames from the video until it's finished
            while True:
                success, frame = video_capture.read()
                
                if not success:
                    break # End of video
                
                # Check if this frame should be saved based on the FRAME_SKIP value
                if frame_count % FRAME_SKIP == 0:
                    # Construct the output image filename
                    image_filename = f"{landmark_name}_frame_{saved_frame_count}.jpg"
                    image_path = os.path.join(landmark_folder_path, image_filename)
                    
                    # Save the frame as a JPG file
                    cv2.imwrite(image_path, frame)
                    saved_frame_count += 1
                
                frame_count += 1

            # Release the video file handle
            video_capture.release()
            print(f"  Finished. Saved {saved_frame_count} frames to '{landmark_folder_path}'")

        except Exception as e:
            print(f"  An unexpected error occurred while processing {video_filename}: {e}")

    print("\n--- Frame Extraction Complete ---")
    print(f"Your dataset is now ready in the '{OUTPUT_DATASET_FOLDER}' folder.")


# This makes the script runnable from the command line
if __name__ == '__main__':
    extract_frames()