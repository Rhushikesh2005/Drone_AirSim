"""
AeroBrain Configuration File
Centralized settings for vision, flight, and performance tuning
"""

# ============================================================================
# VISION & DETECTION SETTINGS
# ============================================================================
YOLO_MODEL = 'yolov8n.pt'          # Model: yolov8n, yolov8s, yolov8m, yolov8l
YOLO_CONFIDENCE = 0.4              # Detection confidence threshold (0.0-1.0)
YOLO_IOU = 0.45                    # IOU threshold for NMS
YOLO_IMGSZ = 640                   # Input image size for YOLO
DETECT_CLASS = 0                   # Class 0 = Person (COCO dataset)

# Multi-class detection (if you want multiple object types)
DETECT_CLASSES = {
    0: "person",
    # 1: "bicycle",
    # 2: "car",
    # etc.
}

# Frame settings
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_CENTER_X = int(FRAME_WIDTH / 2)
FRAME_CENTER_Y = int(FRAME_HEIGHT / 2)
CLEAR_CAMERA_OVERLAYS = False      # Toggle HUD and detection overlays

# ============================================================================
# DRONE CONTROL SETTINGS
# ============================================================================
# DeadZone - prevents jittering (in pixels from center)
YAW_DEADZONE = 50
PITCH_DEADZONE = 30

# Takeoff and manual control defaults
TAKEOFF_ALTITUDE = 7.0            # Default takeoff altitude (meters)
MANUAL_THROTTLE_FACTOR = 1.0      # Manual altitude control responsiveness

# Distance thresholds (area in pixels²)
DISTANCE_TOO_FAR = 40000          # Drone moves forward
DISTANCE_PERFECT = (40000, 90000) # Drone holds distance
DISTANCE_TOO_CLOSE = 90000        # Drone moves backward

# Movement intensity
YAW_MAX_SPEED = 30.0               # Degrees per second
FORWARD_MAX_SPEED = 5.0            # Meters per second (Manual & AI)
ALTITUDE_STEP_SPEED = 1.5          # Speed of altitude adjustment
MANUAL_CONTROL_SMOOTHING = 0.85    # Damping factor (0.0=instant stop, 1.0=no decay)

# ============================================================================
# PERFORMANCE OPTIMIZATION
# ============================================================================
FRAME_SKIP = 1                     # Process every Nth frame (1 = process all)
USE_ASYNC_INFERENCE = False        # Enable async YOLO (experimental)
LOG_FPS = True                     # Log FPS statistics
LOG_DETECTIONS = True              # Log all detections to console
SAVE_DEBUG_FRAMES = False          # Save annotated frames to disk
DEBUG_FRAME_DIR = "debug_frames"   # Directory for debug frames

# ============================================================================
# FLASK WEB DASHBOARD SETTINGS
# ============================================================================
FLASK_HOST = '0.0.0.0'             # Accessible from any IP
FLASK_PORT = 5000                  # Web dashboard port
FLASK_DEBUG = False                # Disable debug mode in production
TELEMETRY_UPDATE_RATE = 200        # ms between telemetry updates

# ============================================================================
# LOGGING & MONITORING
# ============================================================================
LOG_LEVEL = "INFO"                 # DEBUG, INFO, WARNING, ERROR
LOG_TO_FILE = True                 # Save logs to file
LOG_FILE = "aerobrain.log"         # Log file path
ENABLE_STATISTICS = True           # Collect performance stats
STATS_PRINT_INTERVAL = 30          # Print stats every N seconds

# ============================================================================
# AIRSIM CONNECTION SETTINGS
# ============================================================================
AIRSIM_HOST = "127.0.0.1"          # AirSim server address
AIRSIM_PORT = 41451                # AirSim port (default)
AIRSIM_TIMEOUT = 5                 # Connection timeout (seconds)
AIRSIM_VEHICLE_NAME = "Drone1"     # Vehicle name in AirSim

# ============================================================================
# ADVANCED FEATURES
# ============================================================================
# State-based control (IDLE, SEARCHING, TRACKING, LANDING)
USE_STATE_MACHINE = True           # Enable state-based control
SEARCH_PATTERN = "spiral"          # spiral, grid, random
AUTO_LAND_ON_LOSS = True           # Auto-land if target lost for N seconds
TARGET_LOSS_TIMEOUT = 10           # Seconds before auto-land triggers

# Detection smoothing (reduce jitter)
USE_DETECTION_SMOOTHING = True     # Smooth detection box over time
SMOOTHING_FACTOR = 0.3             # 0.0-1.0 (higher = smoother but slower)

# Tracking features
ENABLE_TRACKING = True             # Track objects across frames
MAX_TRACKED_OBJECTS = 10            # Max objects to track simultaneously

# ============================================================================
# SAFETY SETTINGS
# ============================================================================
MAX_FLIGHT_TIME = 5000              # Max flight time (seconds)
MIN_BATTERY_PERCENT = 10           # Min battery before landing
EMERGENCY_LANDING_ALTITUDE = 0.5   # Land if below this altitude (meters)
GEOFENCE_RADIUS = 500              # Max distance from origin (meters)
