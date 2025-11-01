# import face_recognition
import cv2
import pickle
import os
import requests
import time
import serial

FACES_DIR = "faces"
ENCODINGS_FILE = "encodings.pkl"
MODEL = "hog"
URL = "http://192.168.1.37:81/stream"
# URL = 1

# Arduino serial configuration
ARDUINO_PORT = "COM3"  # Change to your Arduino port (e.g., "/dev/ttyUSB0" on Linux)
BAUD_RATE = 9600

# print(f"[*] Loading encodings from '{ENCODINGS_FILE}'...")
# if not os.path.exists(ENCODINGS_FILE):
#     print(f"[!] Error: Encodings file not found. Please run train.py first.")
#     exit()

# with open(ENCODINGS_FILE, "rb") as f:
#     data = pickle.load(f)

# known_encodings = data["encodings"]
# known_names = data["names"]

# # Initialize Arduino serial connection
# try:
#     arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
#     time.sleep(2)  # Wait for Arduino to initialize
#     print(f"[*] Arduino connected on {ARDUINO_PORT}")
# except serial.SerialException:
#     print(f"[!] Error: Could not connect to Arduino on {ARDUINO_PORT}")
#     arduino = None

# print("[*] Starting video stream...")

def set_resolution(url: str, index: int=1, verbose: bool=False):
    try:
        if verbose:
            resolutions = "10: UXGA(1600x1200)\n9: SXGA(1280x1024)\n8: XGA(1024x768)\n7: SVGA(800x600)\n6: VGA(640x480)\n5: CIF(400x296)\n4: QVGA(320x240)\n3: HQVGA(240x176)\n0: QQVGA(160x120)"
            print("available resolutions\n{}".format(resolutions))
        if index in [10, 9, 8, 7, 6, 5, 4, 3, 0]:
            requests.get(url + "/control?var=framesize&val={}".format(index))
        else:
            print("Wrong index")
    except:
        print("SET_RESOLUTION: something went wrong")

def send_to_arduino(name):
    if arduino:
        try:
            arduino.write(f"{name}\n".encode())
            arduino.flush()
        except serial.SerialException:
            print("[!] Error: Failed to send data to Arduino")

set_resolution(URL, index=8)

# Initialize capture with proper settings
cap = cv2.VideoCapture(URL)
if not cap.isOpened():
    print("[!] Error: Could not open webcam.")
    exit()

# Set buffer to minimize frame delay
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FPS, 30)

print("[*] Press 'q' to quit.")

last_sent_name = ""

while True:
    for _ in range(2):  # Fixed number instead of buffer size
        cap.grab()
    
    # Process the latest frame
    ret, frame = cap.read()
    if not ret:
        print("[!] Error: Failed to grab frame.")
        time.sleep(0.1)
        continue
    
    # # Process every frame (no frame skipping)
    # face_locations = face_recognition.face_locations(frame, model=MODEL)
    # face_encodings = face_recognition.face_encodings(frame, face_locations)
    
    # current_name = "Unknown"
    
    # for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
    #     matches = face_recognition.compare_faces(known_encodings, face_encoding)
    #     name = "Unknown"
        
    #     if True in matches:
    #         first_match_index = matches.index(True)
    #         name = known_names[first_match_index]
        
    #     current_name = name
        
    #     cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
    #     cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
    #     font = cv2.FONT_HERSHEY_DUPLEX
    #     cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
    #     print(name)
    
    # # Send name to Arduino only when it changes
    # if current_name != last_sent_name:
    #     send_to_arduino(current_name)
    #     last_sent_name = current_name
    
    cv2.imshow('Video', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()
print("[*] Video stream stopped.")