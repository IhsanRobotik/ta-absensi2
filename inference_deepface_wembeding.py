import os
import cv2
import numpy as np
from deepface import DeepFace
import serial
import time
import requests

# --- Configuration Constants ---
DETECTOR = "opencv"              # Face detector backend (e.g., "opencv", "retinaface")
ENFORCE = False                  # Set to True to raise exception if no face is detected
DB_PATH = "./dataset"            # Path to the directory containing known face images
URL = "http://192.168.1.37:81/stream" # IP Camera Stream URL

# Arduino serial configuration
ARDUINO_PORT = "COM3"  # Change this to your Arduino port
BAUD_RATE = 9600

# Initialize Arduino serial connection
arduino = None
try:
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Wait for Arduino to initialize
    print(f"[*] Arduino connected on {ARDUINO_PORT}")
except serial.SerialException as e:
    print(f"[!] Error: Could not connect to Arduino on {ARDUINO_PORT}. {e}")
    print("[*] Continuing without Arduino support.")


def set_resolution(url: str, index: int=8, verbose: bool=False):
    """Sets the resolution of the ESP32-CAM (assuming standard ESP32-CAM API)."""
    if verbose:
        resolutions = "10: UXGA(1600x1200)\n9: SXGA(1280x1024)\n8: XGA(1024x768)\n7: SVGA(800x600)\n6: VGA(640x480)\n5: CIF(400x296)\n4: QVGA(320x240)\n3: HQVGA(240x176)\n0: QQVGA(160x120)"
        print("Available resolutions:\n{}".format(resolutions))

    if index in [10, 9, 8, 7, 6, 5, 4, 3, 0]:
        try:
            requests.get(url.replace("/stream", "/control") + "?var=framesize&val={}".format(index), timeout=5)
            print(f"[*] Resolution set to index {index}")
        except requests.exceptions.RequestException as e:
            print(f"[!] Failed to set resolution at {url}: {e}")
    else:
        print("[!] Wrong resolution index specified.")

def send_to_arduino(name):
    """Sends the recognized name to the connected Arduino."""
    if arduino and arduino.is_open:
        try:
            data_to_send = f"{name}\n"
            arduino.write(data_to_send.encode('utf-8'))
            arduino.flush()
            # print(f"[>] Sent to Arduino: {name}") # Optional: Debug output
        except serial.SerialException as e:
            print(f"[!] Error: Failed to send data to Arduino. {e}")

def person_name_from_identity(identity_path, db_root):
    """
    Extracts the person's name label from the DeepFace 'identity' path.
    Assumes person label is the folder name inside db_root.
    """
    if not isinstance(identity_path, str) or identity_path.strip() == "":
        return "Unknown"

    # Normalize path separators
    norm_path = os.path.normpath(identity_path)

    # Get the immediate parent directory name
    parent = os.path.basename(os.path.dirname(norm_path))
    
    # Get the stem (filename without extension)
    stem = os.path.splitext(os.path.basename(norm_path))[0]

    db_root_norm = os.path.normpath(db_root)
    
    # Check if the parent is the root of the database or empty, if so, use filename stem
    if parent == "" or parent == os.path.basename(db_root_norm):
        return stem
    
    return parent


# --- Main Logic ---

# 1. Set camera resolution
set_resolution(URL, index=8) # Set to SVGA(800x600) for better performance

# 2. Initialize video capture
cap = cv2.VideoCapture(URL)
if not cap.isOpened():
    # For IP cameras, sometimes a higher buffer size is needed.
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 
    raise RuntimeError(f"[!] Camera stream not available at {URL}. Check connectivity.")

print("[*] Face recognition stream started. Press 'q' to quit.")

while True:
    # Flush buffer (optional, can help with laggy streams)
    for _ in range(2):  
        cap.grab()
    
    # Process the latest frame
    ret, frame = cap.read()
    
    if not ret:
        print("[!] Error: Failed to grab frame. Reconnecting or check stream.")
        time.sleep(0.5)
        continue

    person_name = "Unknown"
    
    try:
        # DeepFace.find returns a list of dataframes (one per detected face)
        # It will implicitly try to detect faces first.
        # Using "VGG-Face" as the model, which is common for recognition.
        dfs = DeepFace.find(
            img_path=frame,
            db_path=DB_PATH,
            model_name="VGG-Face", 
            detector_backend=DETECTOR,
            enforce_detection=ENFORCE,
            align=True,
            # Set distance threshold for matching. Default is 0.40 for VGG-Face/cosine.
            threshold=0.40 
        )

        for df in dfs:
            if not df.empty:
                # Take the best match (first row in the sorted dataframe)
                best_match = df.iloc[0]
                identity_path = best_match['identity']
                
                person_name = person_name_from_identity(identity_path, DB_PATH)
                
                # Extract facial area (bounding box) for visualization
                x, y, w, h = int(best_match['source_x']), int(best_match['source_y']), int(best_match['source_w']), int(best_match['source_h'])
                
                # Draw bounding box (Green for recognized)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    person_name,
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 255, 0),
                    2,
                )

                # Send the identified name to Arduino
                send_to_arduino(person_name)
                
    except ValueError as e:
        # This block catches the ValueError raised by DeepFace when enforce_detection=True 
        # and no face is detected, but since ENFORCE is False, this is mostly for debugging.
        if "Face could not be detected" in str(e):
            person_name = "No Face"
        else:
            # Handle other potential DeepFace errors
            print(f"[!] DeepFace Error: {e}")

    except Exception as e:
        print(f"[!] General Error during processing: {e}")

    # Display the frame
    cv2.imshow("Face Recognition Stream", frame)

    # Break loop on 'q' press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
if arduino and arduino.is_open:
    arduino.close()
    print("[*] Arduino connection closed.")
