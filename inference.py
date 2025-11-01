import cv2
import pickle
import os
import requests
import time

FACES_DIR = "dataset/Richard"
ENCODINGS_FILE = "encodings.pkl"
MODEL = "hog"
URL = "http://192.168.1.28:81/stream"

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

os.makedirs(FACES_DIR, exist_ok=True)

set_resolution(URL, index=8)

cap = cv2.VideoCapture(URL)
if not cap.isOpened():
    print("[!] Error: Could not open webcam.")
    exit()

cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FPS, 30)

print("[*] Press 'c' to capture, 'q' to quit.")

counter = 0

while True:
    for _ in range(2):
        cap.grab()
    
    ret, frame = cap.read()
    if not ret:
        print("[!] Error: Failed to grab frame.")
        time.sleep(0.1)
        continue
    
    cv2.imshow('Video', frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('c'):
        filename = os.path.join(FACES_DIR, f"frame_{counter}.jpg")
        cv2.imwrite(filename, frame)
        print(f"[+] Saved {filename}")
        counter += 1

cap.release()
cv2.destroyAllWindows()
print("[*] Video stream stopped.")
