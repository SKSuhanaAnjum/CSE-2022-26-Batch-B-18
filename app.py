
from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
from ultralytics import YOLO
import os
import cv2
from PIL import Image
from werkzeug.utils import secure_filename
import subprocess
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from threading import Thread
import base64
import io
import traceback
import ssl
import mysql.connector

# ───── Flask Setup ─────
app = Flask(__name__)
app.secret_key = "super-secret-key-123"

# MySQL connection setup
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    port="3306",
    database='plastic'
)
mycursor = mydb.cursor()

#MySQL query functions
def executionquery(query, values):
    mycursor.execute(query, values)
    mydb.commit()

def retrivequery1(query, values):
    mycursor.execute(query, values)
    return mycursor.fetchall()

def retrivequery2(query):
    mycursor.execute(query)
    return mycursor.fetchall()

# ───── Email Alert System ─────
last_alert_time = 0
ALERT_COOLDOWN = 60  # seconds

def send_alert_email(to_email, behavior, annotated_path=None):
    """Send an email alert with prediction and optionally attach annotated image"""
    global last_alert_time
    current_time = time.time()
    if current_time - last_alert_time < ALERT_COOLDOWN:
        print(f"[INFO] Email skipped due to cooldown ({ALERT_COOLDOWN-(current_time-last_alert_time):.0f}s left)")
        return
    last_alert_time = current_time

    sender_email = "cse.takeoff@gmail.com"
    sender_password = "digkagfgyxcjltup"  # Use Gmail App Password

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = f"ALERT: {behavior} Detected!"

        body = f"""
POLLUTANT SAFETY ALERT
Detected : {behavior}
Time     : {time.strftime('%d-%m-%Y %H:%M:%S')}
User     : {to_email}

Stay alert & stay safe!
— Pollutant Monitoring System
        """
        msg.attach(MIMEText(body, 'plain'))

        # Attach annotated image if available
        if annotated_path and os.path.exists(annotated_path):
            with open(annotated_path, "rb") as f:
                mime = MIMEBase('image', 'jpeg', filename=os.path.basename(annotated_path))
                mime.set_payload(f.read())
                encoders.encode_base64(mime)
                mime.add_header('Content-Disposition', 'attachment', filename=os.path.basename(annotated_path))
                msg.attach(mime)

        # Send email via SSL
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())

        print(f"[INFO] Email sent successfully to {to_email}")

    except Exception as e:
        print("[ERROR] Email sending failed!")
        traceback.print_exc()

# ───── YOLO Setup ─────
MODEL_PATH = "best.pt"
try:
    model = YOLO(MODEL_PATH)
    print("[INFO] YOLOv9 model loaded successfully.")
except Exception as e:
    print("[ERROR] Failed to load YOLO model:", e)
    model = None

class_map = {
    0: "Background", 1: "Acid Pollution", 2: "Dead Animals Pollution",
    3: "Eutrophication Pollution", 4: "Fish", 5: "Oil Pollution",
    6: "Plastic Pollution", 7: "bottle", 8: "cardboard", 9: "glass",
    10: "leaf", 11: "metal", 12: "paper", 13: "plastic", 14: "pmb",
    15: "sld", 16: "slh", 17: "trash_plastic", 18: "water", 19: "waterbottle"
}

def is_pollution_class(class_id: int) -> bool:
    non_pollution = {0, 4, 8, 9, 10, 11, 12, 18}
    return class_id not in non_pollution

# ───── Upload Folder ─────
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ───── Routes ─────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirmpassword = request.form.get('confirmpassword', '')

        if not all([name, email, password]):
            return render_template('register.html', message="All fields are required!")

        if password != confirmpassword:
            return render_template('register.html', message="Passwords do not match!")

        emails = [row[0].lower() for row in retrivequery2("SELECT email FROM users")]
        if email in emails:
            return render_template('register.html', message="Email already registered!")

        executionquery("INSERT INTO users (name, email, password) VALUES (%s,%s,%s)", (name, email, password))
        return render_template('login.html', message="Registration successful. Please login.")

    return render_template('register.html')

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = retrivequery1("SELECT email, password FROM users WHERE email=%s", (email,))
        if not user:
            return render_template('login.html', message="Email not found!")

        stored_email, stored_pw = user[0]
        if password != stored_pw:
            return render_template('login.html', message="Incorrect password!")

        session['user_email'] = stored_email
        return redirect("/home")

    return render_template('login.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
    prediction = None
    image_url = None
    annotated_url = None
    user_email = session.get('user_email')

    if request.method == 'POST' and model is not None:
        upload_path = None
        filename = None

        # Webcam capture (base64)
        if 'image' in request.form and request.form['image'].startswith('data:image'):
            try:
                image_data = request.form['image'].split(',')[1]
                image_bytes = base64.b64decode(image_data)
                img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
                filename = f"webcam_{int(time.time())}.jpg"
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                img.save(upload_path)
            except Exception as e:
                print("[ERROR] Webcam image decode:", e)

        # File upload
        elif 'image' in request.files:
            file = request.files['image']
            if file.filename:
                filename = secure_filename(file.filename)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(upload_path)

        # Prediction
        if upload_path and os.path.exists(upload_path):
            try:
                image = cv2.imread(upload_path)
                if image is None:
                    raise ValueError("Could not read image")

                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = model.predict(source=rgb_image, conf=0.3, save=False, verbose=False)
                result = results[0]

                if result.boxes is not None and len(result.boxes) > 0:
                    top_box = max(result.boxes, key=lambda b: float(b.conf))
                    cls_id = int(top_box.cls)
                    conf = float(top_box.conf)
                    class_name = class_map.get(cls_id, f"Class_{cls_id}")
                    prediction = f"{class_name} ({conf:.2f})"

                    # Annotated image path
                    annotated_img = result.plot()
                    annotated_filename = f"annotated_{filename}"
                    annotated_path = os.path.join(app.config['UPLOAD_FOLDER'], annotated_filename)
                    cv2.imwrite(annotated_path, cv2.cvtColor(annotated_img, cv2.COLOR_RGB2BGR))

                    image_url = url_for('static', filename=f'uploads/{filename}')
                    annotated_url = url_for('static', filename=f'uploads/{annotated_filename}')

                    # Email alert in thread (with image attachment)
                    if user_email and is_pollution_class(cls_id):
                        Thread(target=send_alert_email, args=(user_email, class_name, annotated_path), daemon=True).start()
                else:
                    prediction = "No pollutant detected"
                    annotated_path = None

            except Exception as e:
                print("[ERROR] Prediction failed:", e)
                traceback.print_exc()
                prediction = "Error during analysis"

    return render_template('home.html',
                           uploaded_image_url=image_url,
                           annotated_image_url=annotated_url,
                           prediction=prediction)

@app.route('/open_webcam', methods=['GET', 'POST'])
def open_webcam():
    if request.method == 'POST':
        try:
            subprocess.Popen(['python', 'live.py'])
        except Exception as e:
            print("[ERROR] Failed to open webcam script:", e)
    return redirect(url_for('home'))

# ───── Run Flask ─────
if __name__ == '__main__':
    app.run(debug=True)

