import streamlit as st
from ultralytics import YOLO
import numpy as np
from PIL import Image

# Load model
model = YOLO("best.pt")

st.title("Water Quality Detection System 💧")
st.write("Upload an image to detect pollution")

uploaded_file = st.file_uploader("Choose an image", type=["jpg", "png", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    img = np.array(image)
    results = model.predict(source=img, conf=0.3, verbose=False)
    result = results[0]

    if result.boxes is not None and len(result.boxes) > 0:
        top_box = max(result.boxes, key=lambda b: float(b.conf))
        cls_id = int(top_box.cls)
        conf = float(top_box.conf)

        st.success(f"Detected Class: {cls_id} (Confidence: {conf:.2f})")

        annotated = result.plot()
        st.image(annotated, caption="Detection Result")
    else:
        st.warning("No pollutant detected")
