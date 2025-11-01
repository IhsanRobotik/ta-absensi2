import gspread
from google.oauth2.service_account import Credentials
import requests

api_key = "721550bd67f7f1e4c73c29434784cfde"
url = "https://api.imgbb.com/1/upload"
six = "dataset\Ecah_Dwi_Petriyanti\IMG-20250923-WA0156.jpg"

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)

sheet_id = "1IOJTcMtxEJ_o0zDsFOvzwDVLLym_yjTa0ZlIURp6404"
workbook = client.open_by_key(sheet_id)
sheet = workbook.sheet1

import cv2
import base64
import requests

def send_frame(frame):
    # encode frame to JPEG
    _, buffer = cv2.imencode(".jpg", frame)
    # convert to base64 string
    encoded = base64.b64encode(buffer).decode("utf-8")
    payload = {
        "key": api_key,
        "image": encoded,
    }
    r = requests.post(url, data=payload)
    return r.json()

def send_image(image_path):
    with open(image_path, "rb") as f:
        payload = {
            "key": api_key,
        }
        files = {
            "image": f,
        }
        r = requests.post(url, data=payload, files=files)
        return r.json()   # convert to dict


# resp = send_image(six)

# link = resp["data"]["url"]  
# # print(resp)
# formula = f'=IMAGE("{link}")'
# print(formula)
# sheet.update_acell("A1", formula)
