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

app = Flask(__name__, static_folder='vue/dist')
CORS(app)

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

def encode_image_url(img):
    image_bytes = io.BytesIO()
    img.save(image_bytes, format='JPEG')  # or format='JPEG' etc.
    image_bytes = image_bytes.getvalue()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    image_url = f"data:image/jpeg;base64,{base64_image}"
    return image_url

@app.route("/get_transformed_image", methods=["POST"])
def rt_get_transformed_image():
    data = request.get_json()
    image = decode_image_url(data["imageUrl"])

    corners = data['points']
    dist = lambda c1, c2 : ( ((c1['x'] - c2['x'])*image.width)**2 + ((c1['y'] - c2['y'])*image.height)**2 ) ** .5
    approx_width = int((dist(corners[0], corners[1]) + dist(corners[2], corners[3]))/2)
    approx_height = int((dist(corners[0], corners[3]) + dist(corners[1], corners[2]))/2)
    # ratio = (dist(corners[0], corners[1]) + dist(corners[2], corners[3])) / (dist(corners[0], corners[3]) + dist(corners[1], corners[2]))
    corners_tuple = tuple(sum([[u['x']*image.width, u['y']*image.height] for u in [corners[i] for i in (0,3,2,1)]], []))

    img2 = image.transform((approx_width, approx_height), Image.Transform.QUAD, corners_tuple)

    img2.save("crop.png", "png")

    rows = extract_rows(img2)

    return { 
        #"imageUrl": encode_image_url(img2)
        "images": [encode_image_url(img) for img in rows]
    }


if __name__ == "__main__":
    app.run(host='localhost', port=5000, debug=True)