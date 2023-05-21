from flask import Flask, send_from_directory, request
from flask_cors import CORS
import os
import base64
from PIL import Image, ImageOps
import numpy as np
import matplotlib, matplotlib.pyplot as plt
matplotlib.use("agg")
import io
import sys
sys.path.append(os.path.join(os.path.dirname(__file__),".."))
from rows import extract_rows
import sqlite3
import hashlib
from threading import Lock
import json
import traceback

USE_GPU = True
USE_PYTESSERACT = False # attention c'est naze

if not USE_PYTESSERACT:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    ocr_processor = TrOCRProcessor.from_pretrained('microsoft/trocr-large-printed')
    ocr_model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-large-printed')
    if USE_GPU:
        ocr_model = ocr_model.to("cuda:0")

import openai
openai.api_key = os.getenv("OPENAI_API_KEY")
from ast import literal_eval
import Levenshtein

def ocr(images):
    if USE_PYTESSERACT:
        import pytesseract
        return [pytesseract.image_to_string(img, lang="fra", config="--oem 3 --psm 7 -c thresholding_method=1") for img in images]
    else:
        _processed = ocr_processor(images=images, return_tensors="pt")
        if USE_GPU: _processed = _processed.to("cuda:0")
        pixel_values = _processed.pixel_values
        generated_ids = ocr_model.generate(pixel_values)
        generated_text = ocr_processor.batch_decode(generated_ids, skip_special_tokens=True)
        return generated_text

def ocr_to_items(text_rows):
    return
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
                {"role": "system", "content": "Entrée: lignes de texte d'un ticket de caisse reconnu par OCR (avec erreurs). Sortie: les noms des articles corrigés pour correspondre à des articles de supermarché français et leurs prix."},
                {"role": "user", "content": "['CANEMBER 20% PRESID.BTE 250G 1,74 11', 'PONME OOLDEN DELICIOUS', '0.728 K9 X 2.99 E/K9 2.18', ''>> CREMERIE L.S.'']"},
                {"role": "assistant", "content": "[('CAMEMBERT 20% PRESID', 1.74), ('POMME GOLDEN DELICIOUS', 2.18), ('CREMERIE L.S.')]"},
                {"role": "user", "content": str(text_rows)}
            ],
            max_tokens=512
        )
    
    gptMessage = response['choices'][0]['message']['content']
    try:
        gptItems = literal_eval(gptMessage)
    except Exception as e:
        print("ChatGPT raw output:", gptMessage)
        raise e
    return gptItems

def mapGptToImages(text_rows, gptItems):
    matched_rows = [None for _ in text_rows]
    to_be_mapped = set(range(len(text_rows)))
    for i, item in enumerate(gptItems):
        name = item[0]
        price = None
        try:
            price = float(item[1])
            name += " "+str(item[1])
        except:
            pass
        min_j = 0
        min_dist = None
        for j in to_be_mapped:
            d = Levenshtein.distance(name, text_rows[j])
            if min_dist is None or d < min_dist : min_j, min_dist = j, d
        to_be_mapped.discard(i) # necessarily j>i
        to_be_mapped.discard(min_j)
        matched_rows[min_j] = (item[0], price)
    return matched_rows

app = Flask(__name__, static_folder='vue/dist')
CORS(app)

class Database:
    def __init__(self, path=None):
        self.con = sqlite3.connect("db.sqlite3" if path is None else path, check_same_thread=False)
        self.cur = self.con.cursor()
        self.lock = Lock()
        try:
            self.cur.execute("CREATE TABLE IF NOT EXISTS main (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
        except Exception as e:
            print(e)
        self["bonjour"] = "sesmoi2"
        print(self["bonjour2"])
    
    def get(self, key, default=None):
        with self.lock:
            self.cur.execute("SELECT v FROM main WHERE k=?", (key,))
            rows = self.cur.fetchall()
            if len(rows) == 0: return default
            return rows[0][0]
    
    def set(self, key, value):
        with self.lock:
            self.cur.execute("INSERT INTO main (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v", (key, value))
            self.con.commit()
    
    def getobj(self, key, default=None):
        v = self.get(key, default=None)
        if v is None : return default
        return json.loads(v)
    
    def setobj(self, key, value):
        self.set(key, json.dumps(value))
    
    def __getitem__(self, key):
        v = self.get(key)
        if v is None: raise KeyError
        return v
    
    def __setitem__(self, key, value):
        self.set(key, value)
    
    def __contains__(self, key):
        return self.get(key) is not None

db = Database()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

def decode_image_url(b64):
    base64_image = b64.replace(' ', '+')
    base64_image = base64_image.split(",")[-1]  # remove the "data:image/jpeg;base64," part

    # now decode
    image_bytes = base64.b64decode(base64_image)

    # now create a PIL image from the byte array
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)

    return image

def encode_image_url(img:Image.Image):
    image_bytes = io.BytesIO()
    img.save(image_bytes, format='JPEG', quality=95)  # or format='JPEG' etc.
    image_bytes = image_bytes.getvalue()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    image_url = f"data:image/jpeg;base64,{base64_image}"
    return image_url

def make_exception(exc):
    print(exc)
    return {"status":"exception", "exception":str(exc)}

@app.errorhandler(Exception)
def handle_exception(e):
    exc = traceback.format_exc()
    return make_exception(exc)

@app.route("/get_transformed_image", methods=["POST"])
def rt_get_transformed_image():
    data = request.get_json()
    image = decode_image_url(data["imageUrl"]).convert("RGB")

    corners = data['points']
    dist = lambda c1, c2 : ( ((c1['x'] - c2['x'])*image.width)**2 + ((c1['y'] - c2['y'])*image.height)**2 ) ** .5
    approx_width = int((dist(corners[0], corners[1]) + dist(corners[2], corners[3]))/2)
    approx_height = int((dist(corners[0], corners[3]) + dist(corners[1], corners[2]))/2)
    # ratio = (dist(corners[0], corners[1]) + dist(corners[2], corners[3])) / (dist(corners[0], corners[3]) + dist(corners[1], corners[2]))
    corners_tuple = tuple(sum([[u['x']*image.width, u['y']*image.height] for u in [corners[i] for i in (0,3,2,1)]], []))

    img2 = image.transform((approx_width, approx_height), Image.Transform.QUAD, corners_tuple)

    img2.save("crop.png", "png")

    rows = extract_rows(img2)

    originalImageUrl = data["imageUrl"]
    croppedImageUrl = encode_image_url(img2)
    _hash = base64.b64encode(hashlib.sha1(croppedImageUrl.encode()).digest()).decode("utf-8")
    if "receipt_"+_hash in db:
        return make_exception("Receipt already in database, hash="+_hash)
    imageUrls = tuple(encode_image_url(img) for img in rows)

    db.setobj("receipt_"+_hash, {
        "originalImageUrl": originalImageUrl,
        "corners": corners,
        "croppedImageUrl": croppedImageUrl,
        "imageUrls": imageUrls
    })

    return { 
        #"imageUrl": encode_image_url(img2)
        "imageUrls": imageUrls,
        "hash": _hash
    }

@app.route("/get_receipt", methods=["GET"])
def rt_get_receipt():
    h = request.args["hash"]
    _json = db.get("receipt_"+h)
    if _json is None: return make_exception('Receipt does not exist')
    response = app.response_class(
        response=_json,
        mimetype='application/json'
    )
    return response

@app.route("/update_receipt", methods=["POST"])
def rt_update_receipt():
    data = request.get_json()
    receipt = db.getobj("receipt_"+request.args["hash"])
    if receipt is None: return make_exception("The receipt to be updated does not exist.")
    for k, v in data.items():
        receipt[k] = v
    db.setobj("receipt_"+request.args["hash"], receipt)
    return {"status": "success"}

@app.route("/request_ocr")
def rt_request_ocr():
    h = request.args["hash"]
    receipt = db.getobj("receipt_"+request.args["hash"])
    if receipt is None: return make_exception("The receipt to be updated does not exist.")
    print(receipt.keys())
    if "ocrRows" in receipt: return make_exception("OCR already done for this receipt.")
    images = [decode_image_url(url) for url in receipt["imageUrls"]]
    try:
        ocrRows = ocr(images)
        receipt["ocrRows"] = ocrRows
        print("OCR result:", str(ocrRows))
    except Exception as e:
        print("OCR failed: " + str(e))
        return make_exception("OCR failed: " + str(e))
    try:
        gptItems = ocr_to_items(ocrRows)
        receipt["gptItems"] = gptItems
        print("CHATGPT result:", gptItems)
    except Exception as e:
        print("ChatGPT failed: " + str(e))
        return make_exception("ChatGPT failed: " + str(e))

    matchedRows = mapGptToImages(ocrRows, gptItems)
    receipt["matchedRows"] = matchedRows

    db.setobj("receipt_"+request.args["hash"], receipt)
    return {"ocrRows": ocrRows, "gptItems": gptItems, "matchedRows": matchedRows}

if __name__ == "__main__":
    app.run(host='localhost', port=5000, debug=True)