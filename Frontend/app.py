from flask import Flask, render_template, request, redirect, url_for, session
import os
import base64
import io
from PIL import Image
from werkzeug.utils import secure_filename
import time

# ───── Flask Setup ─────
app = Flask(__name__)
app.secret_key = "super-secret-key-123"

# ───── Upload Folder ─────
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ───── Routes ─────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
    prediction = None
    image_url = None

    if request.method == 'POST':
        upload_path = None
        filename = None

        # Webcam capture
        if 'image' in request.form and request.form['image'].startswith('data:image'):
            try:
                image_data = request.form['image'].split(',')[1]
                image_bytes = base64.b64decode(image_data)
                img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
                filename = f"webcam_{int(time.time())}.jpg"
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                img.save(upload_path)
            except Exception as e:
                print("Error:", e)

        # File upload
        elif 'image' in request.files:
            file = request.files['image']
            if file.filename:
                filename = secure_filename(file.filename)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(upload_path)

        # Dummy prediction (since YOLO removed)
        if upload_path:
            prediction = "Pollution detected (Demo Mode)"
            image_url = url_for('static', filename=f'uploads/{filename}')

    return render_template('home.html',
                           uploaded_image_url=image_url,
                           prediction=prediction)

# ───── Run Flask ─────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)