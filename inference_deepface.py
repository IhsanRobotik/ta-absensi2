import os
import cv2
import numpy as np
import serial
import time
import requests
import threading
from deepface import DeepFace
import test_upimage_gsheet as up
import gspread
import queue

task_q = queue.Queue(maxsize=8)
last_name = None
inc = 0

# --- Configuration ---
DB_PATH = "./dataset"
DETECTOR = "opencv"
ENFORCE = False

# IP Camera Configuration (Assuming an ESP32-CAM or similar MJPEG stream)
URL = "http://192.168.1.28:81/stream" 

# Arduino serial configuration
ARDUINO_PORT = "COM21"
BAUD_RATE = 9600

# --- Utility Functions ---

def set_resolution(url: str, index: int, verbose: bool=False):
    try:
        if verbose:
            resolutions = "10: UXGA(1600x1200)\n9: SXGA(1280x1024)\n8: XGA(1024x768)\n7: SVGA(800x600)\n6: VGA(640x480)\n5: CIF(400x296)\n4: QVGA(320x240)\n3: HQVGA(240x176)\n0: QQVGA(160x120)"

        if index in [10, 9, 8, 7, 6, 5, 4, 3, 0]:
            requests.get(url + "/control?var=framesize&val={}".format(index))
        else:
            print("Wrong index")
    except:
        print("SET_RESOLUTION: something went wrong")


def send_to_arduino(name, arduino_connection):
    if arduino_connection:
        try:
            arduino_connection.write(f"{name}\n".encode())
            arduino_connection.flush()
        except serial.SerialException:
            print("[!] Error: Failed to send data to Arduino")

def person_name_from_identity(identity_path, db_root):
    if not isinstance(identity_path, str) or identity_path.strip() == "":
        return "unknown"
    norm = os.path.normpath(identity_path)
    parent = os.path.basename(os.path.dirname(norm))
    stem = os.path.splitext(os.path.basename(norm))[0]

    db_root_norm = os.path.normpath(db_root)
    db_root_basename = os.path.basename(db_root_norm) or db_root_norm

    if parent == "" or parent == db_root_basename or parent == os.path.basename(db_root_norm):
        return stem
    return parent

class ThreadingVideoStream:
    def __init__(self, src=0):
        self.stream = cv2.VideoCapture(src)
        if not self.stream.isOpened():
            raise RuntimeError(f"Camera not available at {src}")
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        (self.grabbed, self.frame) = self.stream.read()
        self.stopped = False
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True # Thread dies when main thread dies
        self.thread.start()

    def update(self):
        while True:
            if self.stopped:
                break
            (grabbed, frame) = self.stream.read()
            
            with self.lock:
                self.grabbed = grabbed
                self.frame = frame

        self.stream.release()

    def read(self):
        with self.lock:
            if self.frame is not None:
                return self.grabbed, self.frame.copy()
            return self.grabbed, None

    def stop(self):
        self.stopped = True
        self.thread.join()

def gsheet_worker(q, sheet):
    col = 0
    while True:
        item = q.get()
        if item is None:
            q.task_done()
            break
        frame, name = item
        try:
            resp = up.send_frame(frame)                    # upload
            link = resp["data"]["url"]
            col += 1
            cell1 = gspread.utils.rowcol_to_a1(col, 1)
            cell2 = gspread.utils.rowcol_to_a1(col, 2)
            formula = f'=IMAGE("{link}")'
            sheet.update_acell(cell1, formula)             # sheet updates
            sheet.update_acell(cell2, name)
        except Exception as e:
            print("[!] gsheet_worker error:", e)
        finally:
            q.task_done()

worker = threading.Thread(target=gsheet_worker, args=(task_q, up.sheet), daemon=True)
worker.start()

if __name__ == "__main__":
    arduino = None
    try:
        arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  
    except serial.SerialException:
        print(f"[!] Error: Could not connect to Arduino on {ARDUINO_PORT}")
    set_resolution(URL, index=9) 
    try:
        cap = ThreadingVideoStream(URL)
    except RuntimeError as e:
        exit()

    try:
        while True:
            ret, frame = cap.read()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30,30))
            
            if not ret or frame is None:
                time.sleep(0.01) # Wait briefly before checking again
                continue
            name = "unknown" # Default name
            
            if len(faces) > 0:
                dfs = DeepFace.find(
                    img_path=frame,
                    db_path=DB_PATH,
                    model_name="VGG-Face",
                    detector_backend=DETECTOR,
                    enforce_detection=ENFORCE,
                    threshold=0.40,
                    silent= True
                )
            else:
                dfs = None
            if isinstance(dfs, list) and len(dfs) > 0:
                for face_idx, df in enumerate(dfs):
                    if df is None or df.empty:
                        continue
                    best = df.iloc[0]
                    
                    x = int(best.get("source_x", 0))
                    y = int(best.get("source_y", 0))
                    w = int(best.get("source_w", 0))
                    h = int(best.get("source_h", 0))

                    identity_path = best.get("identity", "")
                    name = person_name_from_identity(identity_path, DB_PATH)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(
                        frame,
                        name,
                        (max(0, x), max(12, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA,
                    )
                    if name != last_name:
                        send_to_arduino(name,arduino)
                        try:
                            task_q.put_nowait((frame.copy(), name))
                            last_name = name
                        except queue.Full:
                            print("[!] task_q full — dropped frame")

            cv2.imshow("DeepFace Live", frame)
            
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    finally:
        cap.stop()
        cv2.destroyAllWindows()
        task_q.put(None)    # signal worker to exit
        worker.join()
        task_q.join()    
        if arduino:
            arduino.close()

