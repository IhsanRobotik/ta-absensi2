import requests

api_key = "721550bd67f7f1e4c73c29434784cfde"
url = "https://api.imgbb.com/1/upload"
six = "dataset\Ecah_Dwi_Petriyanti\IMG-20250923-WA0156.jpg"

def send_image(image_path):
    with open(image_path, "rb") as f:
        payload = {
            "key": api_key,
        }
        files = {
            "image": f,
        }
        r = requests.post(url, data=payload, files=files)
        return r

r = send_image(six)
print(r.json())
