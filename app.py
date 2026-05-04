from flask import Flask, render_template, Response, jsonify
import cv2
from ultralytics import YOLO
import logging # <-- Naya add kiya logs band karne ke liye
import numpy as np
import torch

# Fix for PyTorch 2.6 weights_only=True default UnpicklingError
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
torch.serialization.add_safe_globals([
    "ultralytics.nn.tasks.DetectionModel",
    "torch.nn.modules.container.Sequential"
])
import ultralytics
# override torch.load to use weights_only=False globally for ultralytics if needed
__original_load = torch.load
def load_override(*args, **kwargs):
    if "weights_only" not in kwargs:
        kwargs["weights_only"] = False
    return __original_load(*args, **kwargs)
torch.load = load_override

app = Flask(__name__)

# Flask ke default terminal logs ko chup karana taaki sirf AI commands dikhein
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

print("Loading AeroBrain AI Model...")
model = YOLO('yolov8n.pt')

FRAME_CENTER_X = 320
FRAME_CENTER_Y = 240
DEADZONE = 50

# Global variables
current_yaw = "CENTERED"
current_pitch = "HOLD"

def generate_frames():
    global current_yaw, current_pitch
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while True:
        success, frame = cap.read()
        if success:
            results = model(frame, imgsz=640, conf=0.4, verbose=False)
            person_detected = False

            for r in results:
                boxes = r.boxes
                for box in boxes:
                    if int(box.cls[0]) == 0: 
                        person_detected = True
                        x1, y1, x2, y2 = int(box.xyxy[0][0]), int(box.xyxy[0][1]), int(box.xyxy[0][2]), int(box.xyxy[0][3])
                        
                        center_x = int((x1 + x2) / 2)
                        center_y = int((y1 + y2) / 2)
                        area = (x2 - x1) * (y2 - y1)

                        # Logic calculations
                        error_x = center_x - FRAME_CENTER_X
                        if error_x > DEADZONE:
                            current_yaw = "YAW RIGHT"
                        elif error_x < -DEADZONE:
                            current_yaw = "YAW LEFT"
                        else:
                            current_yaw = "CENTERED"

                        if area < 40000:
                            current_pitch = "FORWARD"
                        elif area > 90000:
                            current_pitch = "BACKWARD"
                        else:
                            current_pitch = "HOLD DISTANCE"

                        # ---> YAHAN TERMINAL MEIN PRINT HOGA <---
                        print(f"🎯 AI COMMAND -> [ {current_yaw} ]  |  [ MOVE {current_pitch} ]  |  Area: {area}")

                        # Drawing UI
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
                        cv2.line(frame, (FRAME_CENTER_X, 0), (FRAME_CENTER_X, 480), (255, 255, 255), 1)
                        cv2.line(frame, (0, FRAME_CENTER_Y), (640, FRAME_CENTER_Y), (255, 255, 255), 1)

            if not person_detected:
                current_yaw = "SEARCHING"
                current_pitch = "SEARCHING"
        else:
            person_detected = False
            current_yaw = "NO CAMERA"
            current_pitch = "NO CAMERA"
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "NO CAMERA", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/telemetry')
def telemetry():
    return jsonify({"yaw": current_yaw, "pitch": current_pitch})

if __name__ == "__main__":
    print("Starting AeroBrain Mission Control...")
    print("🚀 Server started! Open this URL in your web browser: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)