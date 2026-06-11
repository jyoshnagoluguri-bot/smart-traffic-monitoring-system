from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
import cv2
from ultralytics import YOLO
import math
import numpy as np
import os
import time

app = Flask(__name__)
CORS(app)

# ---------------- MODELS ----------------
helmet_model = YOLO("models/helmet.pt")
vehicle_model = YOLO("models/yolov8n.pt")
ambulance_model = YOLO("models/ambulance.pt")

video_path = "input.mp4"

# ---------------- GLOBALS ----------------
violations = 0
vehicle_count = 0
ambulance_detected = False
processing_done = False
tracked_vehicles = {}
line_y = 400


# ================= IMAGE ANALYSIS (UNCHANGED - SAFE) =================
@app.route('/analyze-road', methods=['POST'])
def analyze_road():

    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files['image']

    image_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)

    if img is None:
        return jsonify({"error": "Invalid image"}), 400

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    edge_density = np.sum(edges > 0) / (img.shape[0] * img.shape[1])

    if edge_density < 0.01:
        zone = "SAFE"
        suggestions = ["Normal road"]
    elif edge_density < 0.03:
        zone = "MODERATE"
        suggestions = ["Add warnings"]
    elif edge_density < 0.06:
        zone = "HIGH"
        suggestions = ["Improve safety"]
    else:
        zone = "VERY HIGH"
        suggestions = ["Critical area"]

    return jsonify({
        "edge_score": float(edge_density),
        "zone": zone,
        "suggestions": suggestions
    })


# ================= VIDEO UPLOAD FIX =================
@app.route('/upload', methods=['POST'])
def upload():
    global video_path, vehicle_count, violations, ambulance_detected, processing_done, tracked_vehicles

    file = request.files.get('video')

    if not file or file.filename == '':
        return jsonify({"error": "No video uploaded"}), 400

    video_path = "input.mp4"
    file.save(video_path)

    # reset system
    vehicle_count = 0
    violations = 0
    ambulance_detected = False
    processing_done = False
    tracked_vehicles = {}

    time.sleep(1)  # IMPORTANT for Render sync

    return jsonify({"status": "uploaded"})


# ================= STREAM (SAFE) =================
def gen_frames():

    global vehicle_count, violations, ambulance_detected, processing_done, tracked_vehicles

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("❌ Video not opened")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # VEHICLE DETECTION
        results = vehicle_model(frame, verbose=False)

        centroids = []

        if results and results[0].boxes is not None:
            for box in results[0].boxes:
                cls = int(box.cls[0])
                label = vehicle_model.names[cls].lower()

                if label in ["car", "bus", "truck", "motorcycle", "bicycle"]:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    centroids.append((cx, cy))

        # SIMPLE COUNT
        vehicle_count = len(centroids)

        # HELMET CHECK
        helmet_results = helmet_model(frame, verbose=False)

        violations = 0
        if helmet_results and helmet_results[0].boxes is not None:
            for box in helmet_results[0].boxes:
                label = helmet_model.names[int(box.cls[0])].lower()
                if "without" in label:
                    violations += 1

        # AMBULANCE
        amb = ambulance_model(frame, verbose=False)
        ambulance_detected = amb and len(amb[0].boxes) > 0

        # STREAM FRAME
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()
    processing_done = True


# ================= VIDEO =================
@app.route('/video')
def video():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# ================= RESULT =================
@app.route('/result')
def result():

    return jsonify({
        "violations": violations,
        "vehicle_count": vehicle_count,
        "traffic_density": "HIGH" if vehicle_count > 10 else "LOW",
        "ambulance_alert": ambulance_detected
    })


# ================= HOME =================
@app.route("/")
def home():
    return send_from_directory(".", "login.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)


# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("🚀 Running on port", port)
    app.run(host="0.0.0.0", port=port, debug=False)
