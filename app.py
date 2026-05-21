from flask import Flask, render_template, Response, jsonify
import cv2
from ultralytics import YOLO
import logging
import os
import sys
import time
import threading
from collections import deque
import json

# Import configuration
import config
from utils import setup_logging, FPSCounter

app = Flask(__name__)
logger = setup_logging()

# Flask logs mute
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Initialize model and camera
model = None
cap = None
camera_lock = threading.Lock()

# Telemetry and statistics
telemetry_data = {
    "yaw": "INITIALIZING...",
    "pitch": "INITIALIZING...",
    "target": "NONE",
    "fps": 0.0,
    "detections": 0,
    "state": "IDLE",
    "confidence": 0.0,
    "area": 0
}

fps_counter = FPSCounter()
stats_lock = threading.Lock()

logger.info("🚀 Loading AeroBrain AI (Target Tracking Enabled)...")
try:
    # Check if model file exists
    if not os.path.exists(config.YOLO_MODEL):
        logger.error(f"YOLO model not found: {config.YOLO_MODEL}")
        sys.exit(1)
    
    model = YOLO(config.YOLO_MODEL)
    logger.info(f"[OK] YOLO Model loaded: {config.YOLO_MODEL}")
except Exception as e:
    logger.error(f"FATAL: Failed to load YOLO model: {e}")
    sys.exit(1)

def generate_frames():
    """Main video stream generator with advanced tracking"""
    global model, telemetry_data
    
    if model is None:
        logger.error("YOLO model not initialized")
        return
    
    try:
        with camera_lock:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cap.isOpened():
                logger.error("Cannot access camera (index 0)")
                return
            
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
            logger.info("✅ Camera connected successfully")

        frame_skip = 0
        detections_cumulative = 0

        while True:
            success, frame = cap.read()
            if not success:
                logger.warning("Failed to read frame from camera")
                break

            # Frame skip for performance
            frame_skip = (frame_skip + 1) % config.FRAME_SKIP
            if frame_skip != 0:
                continue

            # Run YOLO inference
            try:
                inference_start = time.time()
                results = model.track(
                    frame, 
                    persist=True, 
                    imgsz=config.YOLO_IMGSZ, 
                    conf=config.YOLO_CONFIDENCE, 
                    verbose=False
                )
                inference_time = (time.time() - inference_start) * 1000
            except Exception as e:
                logger.warning(f"YOLO inference failed: {e}")
                results = []

            primary_threat_box = None
            largest_area = 0
            threat_name = "NONE"
            num_detections = 0
            max_confidence = 0.0

            # Process detections
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    try:
                        x1, y1, x2, y2 = int(box.xyxy[0][0]), int(box.xyxy[0][1]), int(box.xyxy[0][2]), int(box.xyxy[0][3])
                        area = (x2 - x1) * (y2 - y1)
                        confidence = float(box.conf[0])
                        max_confidence = max(max_confidence, confidence)
                        num_detections += 1
                        
                        if area > config.DISTANCE_TOO_FAR and area > largest_area:
                            largest_area = area
                            primary_threat_box = box
                            class_name = model.names[int(box.cls[0])].upper()
                            
                            # Track ID
                            if box.id is not None:
                                track_id = int(box.id[0])
                                threat_name = f"{class_name} #{track_id}"
                            else:
                                threat_name = f"{class_name} #?"
                    except Exception as e:
                        logger.debug(f"Box processing error: {e}")
                        continue

            # Update telemetry
            with stats_lock:
                detections_cumulative += num_detections

            # Draw threats if detected
            if primary_threat_box:
                x1, y1, x2, y2 = int(primary_threat_box.xyxy[0][0]), int(primary_threat_box.xyxy[0][1]), int(primary_threat_box.xyxy[0][2]), int(primary_threat_box.xyxy[0][3])
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                
                with stats_lock:
                    telemetry_data["target"] = threat_name
                    telemetry_data["area"] = largest_area
                    telemetry_data["confidence"] = round(max_confidence, 3)

                # Avoidance logic
                degrees_per_pixel = 60 / config.FRAME_WIDTH

                if largest_area > config.DISTANCE_TOO_CLOSE:
                    with stats_lock:
                        telemetry_data["pitch"] = "⬇ EMERGENCY REVERSE"
                    if center_x > config.FRAME_CENTER_X:
                        with stats_lock:
                            telemetry_data["yaw"] = f"⬅ SHARP EVADE LEFT 60.0°"
                    else:
                        with stats_lock:
                            telemetry_data["yaw"] = f"➔ SHARP EVADE RIGHT 60.0°"
                    color = (0, 0, 255)  # Red - critical
                else:
                    with stats_lock:
                        telemetry_data["pitch"] = "= HOLD / SLOW DOWN"
                    if center_x > config.FRAME_CENTER_X:
                        pixels_to_turn = config.FRAME_CENTER_X - (x1 - 40)
                        turn_angle = round(max(0, pixels_to_turn * degrees_per_pixel), 1)
                        with stats_lock:
                            telemetry_data["yaw"] = f"⬅ EVADE LEFT {turn_angle}°"
                    else:
                        pixels_to_turn = (x2 + 40) - config.FRAME_CENTER_X
                        turn_angle = round(max(0, pixels_to_turn * degrees_per_pixel), 1)
                        with stats_lock:
                            telemetry_data["yaw"] = f"➔ EVADE RIGHT {turn_angle}°"
                    color = (255, 0, 0)  # Yellow - warning

                # Draw bounding box and info
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                cv2.putText(frame, f"{threat_name} [{max_confidence:.2f}]", (x1, y1 - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                cv2.circle(frame, (center_x, center_y), 8, color, -1)

                if config.LOG_DETECTIONS:
                    logger.info(f"🎯 [{threat_name}] {telemetry_data['yaw']} | {telemetry_data['pitch']} | Area: {largest_area}")

            else:
                with stats_lock:
                    telemetry_data["target"] = "NONE"
                    telemetry_data["yaw"] = "= PATH CLEAR 0.0°"
                    telemetry_data["pitch"] = "⬆ CRUISE FORWARD"
                    telemetry_data["area"] = 0
                    telemetry_data["confidence"] = 0.0

                if config.LOG_DETECTIONS:
                    logger.info("🔍 SEARCHING FOR TARGET...")

            # Draw zones and crosshair
            cv2.line(frame, (config.FRAME_CENTER_X, 0), (config.FRAME_CENTER_X, config.FRAME_HEIGHT), (255, 255, 255), 1)
            cv2.line(frame, (0, config.FRAME_CENTER_Y), (config.FRAME_WIDTH, config.FRAME_CENTER_Y), (255, 255, 255), 1)
            
            # Draw zone boundaries
            cv2.line(frame, (config.FRAME_WIDTH // 3, 0), (config.FRAME_WIDTH // 3, config.FRAME_HEIGHT), (100, 100, 100), 1)
            cv2.line(frame, (2 * config.FRAME_WIDTH // 3, 0), (2 * config.FRAME_WIDTH // 3, config.FRAME_HEIGHT), (100, 100, 100), 1)

            # Add status overlay
            fps_val = fps_counter.fps
            status = f"FPS: {fps_val:.1f} | Detections: {num_detections} | Inf: {inference_time:.1f}ms"
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            # Encode frame
            try:
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    logger.warning("Failed to encode frame to JPEG")
                    continue
                
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                fps_counter.tick()
            except Exception as e:
                logger.warning(f"Frame encoding error: {e}")
                continue

    except Exception as e:
        logger.error(f"Error in generate_frames: {e}")
    finally:
        if cap is not None:
            cap.release()
        logger.info("📹 Camera stream closed")

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming endpoint"""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/telemetry')
def telemetry():
    """Real-time telemetry endpoint"""
    try:
        with stats_lock:
            data = telemetry_data.copy()
        return jsonify(data)
    except Exception as e:
        logger.warning(f"Telemetry error: {e}")
        return jsonify({
            "yaw": "ERROR", 
            "pitch": "ERROR", 
            "target": "UNKNOWN",
            "fps": 0,
            "detections": 0,
            "state": "ERROR"
        })

@app.route('/stats')
def stats():
    """Detailed statistics endpoint"""
    try:
        with stats_lock:
            stats_data = {
                "fps": fps_counter.fps,
                "avg_frame_time": fps_counter.avg_frame_time,
                "current_detections": telemetry_data.get("detections", 0),
                "confidence": telemetry_data.get("confidence", 0)
            }
        return jsonify(stats_data)
    except Exception as e:
        logger.warning(f"Stats error: {e}")
        return jsonify({"error": str(e)})

@app.route('/config')
def get_config():
    """Get current configuration"""
    try:
        config_dict = {k: v for k, v in vars(config).items() if not k.startswith('_')}
        return jsonify(config_dict)
    except Exception as e:
        logger.warning(f"Config error: {e}")
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    if model is None:
        logger.error("FATAL: Cannot start Flask app without YOLO model")
        sys.exit(1)
    
    try:
        logger.info("="*70)
        logger.info("🚀 Starting AeroBrain AI Dashboard with TRACKING & MEMORY")
        logger.info("🌐 OPEN DASHBOARD: http://127.0.0.1:5000")
        logger.info("="*70)
        app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG, use_reloader=False)
    except Exception as e:
        logger.error(f"FATAL: Flask app crashed: {e}")
        sys.exit(1)
