from flask import Flask, render_template, Response, jsonify
import cv2
from ultralytics import YOLO
import logging

app = Flask(__name__)

# Flask logs mute karna
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

print("Loading AeroBrain AI (Target Tracking Enabled)...")
model = YOLO('yolov8n.pt')

# Screen ko 3 hisson mein baatne ke liye points
ZONE_LEFT_LIMIT = 213   
ZONE_RIGHT_LIMIT = 426  
FRAME_CENTER_X = 320    

WARNING_AREA = 40000    # Ab khatra jaldi detect hoga
CRITICAL_AREA = 250000  # Panic sirf tab hoga jab object poori screen gher le

current_yaw = "PATH CLEAR = 0.0°"
current_pitch = "CRUISE FORWARD ⬆"
current_target_name = "NONE"

def generate_frames():
    global current_yaw, current_pitch, current_target_name
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) 
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while True:
        success, frame = cap.read()
        if not success:
            break

        # 🌟 MAGIC HAPPENS HERE: model(frame) ki jagah hum model.track() use kar rahe hain
        # persist=True ka matlab hai AI purane objects ki ID yaad rakhega!
        results = model.track(frame, persist=True, imgsz=640, conf=0.4, verbose=False)
        
        primary_threat_box = None
        largest_area = 0
        threat_name = "NONE"

        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = int(box.xyxy[0][0]), int(box.xyxy[0][1]), int(box.xyxy[0][2]), int(box.xyxy[0][3])
                area = (x2 - x1) * (y2 - y1)
                
                if area > WARNING_AREA and area > largest_area:
                    largest_area = area
                    primary_threat_box = box
                    class_name = model.names[int(box.cls[0])].upper()
                    
                    # 🌟 NAYA FEATURE: ID nikalna
                    if box.id is not None:
                        # Agar ID assign ho gayi hai, toh usko naam ke sath jod do
                        track_id = int(box.id[0])
                        threat_name = f"{class_name} #{track_id}"
                    else:
                        # Shuruwaati frame mein kabhi-kabhi ID nahi hoti
                        threat_name = f"{class_name} #?"

        if primary_threat_box:
            x1, y1, x2, y2 = int(primary_threat_box.xyxy[0][0]), int(primary_threat_box.xyxy[0][1]), int(primary_threat_box.xyxy[0][2]), int(primary_threat_box.xyxy[0][3])
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            current_target_name = threat_name

            # Box aur uske upar Object ka unique ID print karna
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.putText(frame, f"OBSTACLE: {threat_name}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.circle(frame, (center_x, center_y), 8, (0, 0, 255), -1)

            # RASTA NIKALNE KA LOGIC
            degrees_per_pixel = 60 / 640

            if largest_area > CRITICAL_AREA:
                current_pitch = "EMERGENCY REVERSE ⬇"
                if center_x > FRAME_CENTER_X:
                    current_yaw = "SHARP EVADE LEFT  ⬅ 60.0°"
                else:
                    current_yaw = "SHARP EVADE RIGHT ➔ 60.0°"
            else:
                current_pitch = "HOLD / SLOW DOWN ="
                if center_x > FRAME_CENTER_X:
                    pixels_to_turn = FRAME_CENTER_X - (x1 - 40)
                    turn_angle = round(max(0, pixels_to_turn * degrees_per_pixel), 1)
                    current_yaw = f"EVADE LEFT  ⬅ {turn_angle}°"
                else:
                    pixels_to_turn = (x2 + 40) - FRAME_CENTER_X
                    turn_angle = round(max(0, pixels_to_turn * degrees_per_pixel), 1)
                    current_yaw = f"EVADE RIGHT ➔ {turn_angle}°"
            
            print(f"🚨 AVOIDANCE: [ {threat_name} ] -> {current_yaw} | {current_pitch}")

        else:
            current_target_name = "NONE"
            current_yaw = "PATH CLEAR = 0.0°"
            current_pitch = "CRUISE FORWARD ⬆"
            # Terminal logs
            print("✅ PATH CLEAR -> CRUISE FORWARD") 

        cv2.line(frame, (ZONE_LEFT_LIMIT, 0), (ZONE_LEFT_LIMIT, 480), (255, 255, 0), 1)
        cv2.line(frame, (ZONE_RIGHT_LIMIT, 0), (ZONE_RIGHT_LIMIT, 480), (255, 255, 0), 1)
        cv2.putText(frame, "LEFT", (50, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        cv2.putText(frame, "CENTER", (280, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        cv2.putText(frame, "RIGHT", (500, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

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
    print("🚀 Starting AeroBrain with MEMORY & TRACKING...")
    print("🌐 CLICK HERE TO OPEN DASHBOARD: http://127.0.0.1:5000")
    print("-" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)