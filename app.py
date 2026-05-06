
from flask import Flask, render_template, Response, jsonify, request
import cv2
from ultralytics import YOLO
import logging

app = Flask(__name__)

# Flask ke internal messages ko mute karna taaki terminal clean rahe
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

print("🚀 Loading AeroBrain Autopilot System...")
model = YOLO('yolov8n.pt')

# --- CONFIGURATION ---
ZONE_LEFT_LIMIT = 213 
ZONE_RIGHT_LIMIT = 426  
FRAME_CENTER_X = 320    
WARNING_AREA = 60000    
CRITICAL_AREA = 120000  

# Global Variables
current_yaw = "PATH CLEAR = 0.0°"
current_pitch = "CRUISE FORWARD ⬆️"
video_source = 0  # 0 = Camera, 'testing_video.mp4' = Test Video

def generate_frames():
    global current_yaw, current_pitch, video_source
    
    while True:
        # Har baar loop mein cap ko refresh karenge agar source change hota hai
        cap = cv2.VideoCapture(video_source)
        
        while True:
            success, frame = cap.read()
            
            if not success:
                if video_source != 0: # Agar video hai toh restart karo
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    break

            frame = cv2.resize(frame, (640, 480))
            results = model(frame, imgsz=640, conf=0.4, verbose=False)
            
            primary_threat_box = None
            largest_area = 0
            threat_name = "NONE"

            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    area = (x2 - x1) * (y2 - y1)
                    
                    if area > WARNING_AREA and area > largest_area:
                        largest_area = area
                        primary_threat_box = box
                        threat_name = model.names[int(box.cls[0])].upper()

            if primary_threat_box:
                x1, y1, x2, y2 = map(int, primary_threat_box.xyxy[0])
                center_x = (x1 + x2) // 2
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                cv2.putText(frame, f"OBSTACLE: {threat_name}", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                degrees_per_pixel = 60 / 640
                if largest_area > CRITICAL_AREA:
                    current_pitch = "EMERGENCY REVERSE ⬇️"
                    current_yaw = "SHARP EVADE LEFT ⬅️ 60.0°" if center_x > FRAME_CENTER_X else "SHARP EVADE RIGHT ➔ 60.0°"
                else:
                    current_pitch = "HOLD / SLOW DOWN ="
                    if center_x > FRAME_CENTER_X:
                        current_yaw = f"EVADE LEFT ⬅️ {round((FRAME_CENTER_X - (x1 - 40)) * degrees_per_pixel, 1)}°"
                    else:
                        current_yaw = f"EVADE RIGHT ➔ {round(((x2 + 40) - FRAME_CENTER_X) * degrees_per_pixel, 1)}°"
                
                # Terminal Log
                print(f"🚨 AVOIDANCE: [ {threat_name} ] -> {current_yaw} | {current_pitch}")
            else:
                current_yaw = "PATH CLEAR = 0.0°"
                current_pitch = "CRUISE FORWARD ⬆️"

            # UI Lines
            cv2.line(frame, (ZONE_LEFT_LIMIT, 0), (ZONE_LEFT_LIMIT, 480), (255, 255, 0), 1)
            cv2.line(frame, (ZONE_RIGHT_LIMIT, 0), (ZONE_RIGHT_LIMIT, 480), (255, 255, 0), 1)

            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        cap.release()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/set_source/<int:mode>')
def set_source(mode):
    global video_source
    video_source = 'testing_video.mp4' if mode == 1 else 0
    print(f"🔄 SWITCHING MODE: {'TEST VIDEO' if mode == 1 else 'LIVE CAMERA'}")
    return jsonify({"status": "success"})

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/telemetry')
def telemetry():
    return jsonify({"yaw": current_yaw, "pitch": current_pitch})

# --- YE HAI URL WALA CORRECT BLOCK ---
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚁 AEROBRAIN MISSION CONTROL IS STARTING...")
    print("🌐 DASHBOARD URL: http://127.0.0.1:5000")
    print("💡 Tip: Press CTRL + Click on the link above")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
