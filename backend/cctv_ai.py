from ultralytics import YOLO
import cv2

# ---------------- MODELS ----------------
helmet_model = YOLO("models/helmet.pt")

# COCO pretrained vehicle model
vehicle_model = YOLO("models/yolov8n.pt")

ambulance_model = YOLO("models/ambulance.pt")


def process_video(input_path, output_path="output.mp4"):

    cap = cv2.VideoCapture(input_path)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # ---------------- GLOBAL COUNTERS ----------------
    total_violations = 0
    total_vehicle_count = 0
    ambulance_detected = False

    while cap.isOpened():

        ret, frame = cap.read()
        if not ret:
            break

        display_frame = frame.copy()

        # =================================================
        # 1. HELMET DETECTION (VIOLATIONS)
        # =================================================
        helmet_results = helmet_model(display_frame, verbose=False)

        frame_violations = 0

        if helmet_results and helmet_results[0].boxes is not None:

            for box in helmet_results[0].boxes:

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls = int(box.cls[0])
                conf = float(box.conf[0])

                label = helmet_model.names[cls].lower()

                # violation logic (ONLY WITHOUT HELMET)
                if "without helmet" in label or "no helmet" in label:
                    frame_violations += 1
                    color = (0, 0, 255)
                else:
                    color = (0, 255, 0)

                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)

                cv2.putText(
                    display_frame,
                    f"{label} {conf:.2f}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2
                )

        total_violations += frame_violations

        # =================================================
        # 2. VEHICLE DETECTION (COCO MODEL FIXED)
        # =================================================
        vehicle_results = vehicle_model(display_frame, verbose=False)

        frame_vehicle_count = 0

        if vehicle_results and vehicle_results[0].boxes is not None:

            for box in vehicle_results[0].boxes:

                cls = int(box.cls[0])
                label = vehicle_model.names[cls].lower()

                # ONLY VEHICLES (COCO CLEAN FILTER)
                if label in ["car", "bus", "truck", "motorcycle"]:
                    frame_vehicle_count += 1

        total_vehicle_count += frame_vehicle_count

        # =================================================
        # 3. AMBULANCE DETECTION
        # =================================================
        ambulance_results = ambulance_model(display_frame, verbose=False)

        if ambulance_results and ambulance_results[0].boxes is not None:

            for box in ambulance_results[0].boxes:

                cls = int(box.cls[0])
                label = ambulance_model.names[cls].lower()

                if "ambulance" in label:
                    ambulance_detected = True

                    cv2.putText(
                        display_frame,
                        "AMBULANCE DETECTED!",
                        (50, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 0, 255),
                        3
                    )

        # =================================================
        # 4. OVERLAY UI
        # =================================================
        cv2.putText(display_frame, f"Vehicles: {frame_vehicle_count}", (30, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.putText(display_frame, f"Violations: {total_violations}", (30, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        out.write(display_frame)

    cap.release()
    out.release()

    # =================================================
    # 5. FINAL DENSITY CALCULATION
    # =================================================
    if total_vehicle_count >= 20:
        traffic_density = "HIGH"
    elif total_vehicle_count >= 8:
        traffic_density = "MEDIUM"
    else:
        traffic_density = "LOW"

    return {
        "violations": total_violations,
        "vehicle_count": total_vehicle_count,
        "vehicle_density": traffic_density,
        "traffic_density": traffic_density,
        "ambulance_alert": ambulance_detected,
        "video_url": output_path
    }
