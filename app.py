from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import cv2
from ultralytics import YOLO
import math
import numpy as np
from flask import send_from_directory

app = Flask(__name__)
CORS(app)

# ---------------- MODELS ----------------
helmet_model = YOLO(r"C:\Users\jyosh\OneDrive\Desktop\helmet_project\runs\detect\train-4\weights\best.pt")
vehicle_model = YOLO("yolov8n.pt")
ambulance_model = YOLO(r"C:\Users\jyosh\Downloads\archive (1)\runs\detect\train\weights\best.pt")

video_path = "input.mp4"

# ---------------- GLOBAL STATS ----------------
violations = 0
vehicle_count = 0
ambulance_detected = False
processing_done = False

# ---------------- TRACKING DATA ----------------
tracked_vehicles = {}   # id: (cx, cy, counted)
line_y = 400            # change based on your video




@app.route('/analyze-road', methods=['POST'])
def analyze_road():

    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"})

    file = request.files['image']

    image_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)

    if img is None:
        return jsonify({"error": "Invalid image"})

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    edge_density = np.sum(edges > 0) / (img.shape[0] * img.shape[1])

    suggestions = []
    zone = "🟢 SAFE ZONE"

    if edge_density < 0.01:

        zone = "🟢 SAFE ZONE"

        suggestions = [
            "Straight road detected",
            "Normal monitoring sufficient",
            "Maintain existing road signs",
            "Routine inspection recommended",
            "Traffic flow appears safe"
        ]

    elif edge_density < 0.03:

        zone = "⚠️ MODERATE RISK ZONE"

        suggestions = [
            "Possible blind turn detected",
            "Install warning boards",
            "Add reflective road markers",
            "Improve night visibility",
            "Add speed limit signs",
            "Monitor accident records"
        ]

    elif edge_density < 0.06:

        zone = "🚧 HIGH RISK ZONE"

        suggestions = [
            "Complex junction likely",
            "Install speed breakers",
            "Add reflective lane markings",
            "Install warning boards",
            "Improve street lighting",
            "Deploy CCTV monitoring",
            "Optimize traffic signals",
            "Add pedestrian crossings"
        ]

    else:

        zone = "🚨 VERY HIGH RISK ZONE"

        suggestions = [
            "Accident-prone area detected",
            "Install safety barriers",
            "Deploy CCTV cameras",
            "Install flashing warning lights",
            "Add speed breakers",
            "Place danger warning boards",
            "Improve road markings",
            "Increase police patrols",
            "Create emergency response plan",
            "Conduct road safety audit"
        ]

    return jsonify({
        "edge_score": float(edge_density),
        "zone": zone,
        "suggestions": suggestions
    })


# ================= UPLOAD =================
@app.route('/upload', methods=['POST'])
def upload():
    global violations, vehicle_count, ambulance_detected, processing_done, video_path, tracked_vehicles

    file = request.files['video']
    file.save(video_path)

    violations = 0
    vehicle_count = 0
    ambulance_detected = False
    processing_done = False
    tracked_vehicles = {}

    return jsonify({"status": "uploaded"})


# ================= STREAM =================
def gen_frames():
    global violations, vehicle_count, ambulance_detected, processing_done, tracked_vehicles

    cap = cv2.VideoCapture(video_path)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # ---------------- VEHICLE DETECTION ----------------
        vehicle_results = vehicle_model(frame, verbose=False)

        current_centroids = []

        if vehicle_results and vehicle_results[0].boxes is not None:
            for box in vehicle_results[0].boxes:
                cls = int(box.cls[0])
                label = vehicle_model.names[cls].lower()

                if label in ["car", "bus", "truck", "motorcycle", "bicycle"]:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2

                    current_centroids.append((cx, cy))

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)

        # ---------------- TRACKING + COUNTING ----------------
        for cx, cy in current_centroids:

            matched = False

            for vid in list(tracked_vehicles.keys()):
                px, py, counted = tracked_vehicles[vid]

                distance = math.hypot(cx - px, cy - py)

                if distance < 40:  # tracking threshold
                    tracked_vehicles[vid] = (cx, cy, counted)

                    # COUNT ONLY ONCE WHEN CROSSING LINE
                    if not counted and cy > line_y:
                        vehicle_count += 1
                        tracked_vehicles[vid] = (cx, cy, True)

                    matched = True
                    break

            # new vehicle
            if not matched:
                new_id = len(tracked_vehicles) + 1
                tracked_vehicles[new_id] = (cx, cy, False)

        # ---------------- HELMET VIOLATIONS ----------------
        helmet_results = helmet_model(frame, verbose=False)

        frame_violation = 0

        if helmet_results and helmet_results[0].boxes is not None:
            for box in helmet_results[0].boxes:

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls = int(box.cls[0])
                conf = float(box.conf[0])

                label = helmet_model.names[cls].lower()

                if "without" in label or "no helmet" in label:
                    frame_violation += 1
                    color = (0, 0, 255)
                else:
                    color = (0, 255, 0)

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"{label} {conf:.2f}",
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, color, 2)

        violations = max(violations, frame_violation)

        # ---------------- AMBULANCE ----------------
        amb = ambulance_model(frame, verbose=False)

        if amb and amb[0].boxes is not None and len(amb[0].boxes) > 0:
            ambulance_detected = True

            cv2.putText(frame,
                        "AMBULANCE DETECTED",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 0, 255),
                        3)

        # ---------------- COUNT LINE ----------------
        cv2.line(frame, (0, line_y), (frame.shape[1], line_y), (0, 255, 0), 2)

        cv2.putText(frame, f"Vehicles: {vehicle_count}",
                    (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255, 255, 0),
                    2)

        # ---------------- STREAM ----------------
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

    if vehicle_count >= 15:
        traffic_density = "HIGH"
    elif vehicle_count >= 5:
        traffic_density = "MEDIUM"
    else:
        traffic_density = "LOW"

    return jsonify({
        "status": "DONE" if processing_done else "RUNNING",
        "violations": violations,
        "vehicle_count": vehicle_count,
        "traffic_density": traffic_density,
        "ambulance_alert": ambulance_detected
    })


# ================= HOME =================
@app.route('/')
def login():
    return send_from_directory("../", "login.html")


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory("../", filename)


if __name__ == "__main__":
    app.run(debug=False,host="0.0.0.0",port=10000)