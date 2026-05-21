"""
AeroBrain Utilities - Performance monitoring, statistics, and helpers
"""

import time
import logging
from collections import deque
from datetime import datetime
import config

class FPSCounter:
    """Real-time FPS tracking"""
    def __init__(self, window_size=30):
        self.times = deque(maxlen=window_size)
        self.last_time = time.time()
    
    def tick(self):
        now = time.time()
        self.times.append(now - self.last_time)
        self.last_time = now
    
    @property
    def fps(self):
        if len(self.times) < 2:
            return 0
        return len(self.times) / sum(self.times)
    
    @property
    def avg_frame_time(self):
        if not self.times:
            return 0
        return (sum(self.times) / len(self.times)) * 1000  # ms

class DetectionSmoother:
    """Smooth bounding box coordinates over time"""
    def __init__(self, factor=0.3):
        self.factor = factor  # 0.0 = no smoothing, 1.0 = complete smoothing
        self.prev_box = None
    
    def smooth(self, box):
        """Smooth box coordinates: [x1, y1, x2, y2]"""
        if self.prev_box is None:
            self.prev_box = box
            return box
        
        smoothed = [
            int(self.factor * self.prev_box[i] + (1 - self.factor) * box[i])
            for i in range(4)
        ]
        self.prev_box = smoothed
        return smoothed

class ObjectTracker:
    """Simple centroid-based object tracking"""
    def __init__(self, max_distance=100, max_disappeared=30):
        self.objects = {}
        self.next_id = 0
        self.max_distance = max_distance
        self.max_disappeared = max_disappeared
        self.disappeared = {}
    
    def update(self, boxes):
        """Update tracker with new detections"""
        if len(boxes) == 0:
            self.disappeared.clear()
            self.objects.clear()
            return self.objects
        
        # Calculate centroids
        centroids = []
        for x1, y1, x2, y2 in boxes:
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            centroids.append((cx, cy))
        
        # Simple nearest-neighbor matching
        matched = set()
        for obj_id, prev_centroid in list(self.objects.items()):
            min_dist = float('inf')
            best_idx = -1
            
            for idx, centroid in enumerate(centroids):
                if idx in matched:
                    continue
                dist = ((centroid[0] - prev_centroid[0])**2 + 
                       (centroid[1] - prev_centroid[1])**2)**0.5
                if dist < min_dist and dist < self.max_distance:
                    min_dist = dist
                    best_idx = idx
            
            if best_idx != -1:
                self.objects[obj_id] = centroids[best_idx]
                self.disappeared[obj_id] = 0
                matched.add(best_idx)
            else:
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    del self.objects[obj_id]
                    del self.disappeared[obj_id]
        
        # Register new objects
        for idx, centroid in enumerate(centroids):
            if idx not in matched:
                self.objects[self.next_id] = centroid
                self.disappeared[self.next_id] = 0
                self.next_id += 1
        
        return self.objects

class Statistics:
    """Collect and report performance statistics"""
    def __init__(self):
        self.start_time = time.time()
        self.frame_count = 0
        self.detection_count = 0
        self.total_inference_time = 0
        self.last_report = time.time()
    
    def record_frame(self, num_detections=0, inference_time=0):
        self.frame_count += 1
        self.detection_count += num_detections
        self.total_inference_time += inference_time
    
    def report(self, force=False):
        now = time.time()
        elapsed = now - self.last_report
        
        if force or elapsed >= config.STATS_PRINT_INTERVAL:
            uptime = now - self.start_time
            avg_inference = (self.total_inference_time / self.frame_count * 1000 
                           if self.frame_count > 0 else 0)
            
            print("\n" + "="*60)
            print(f"📊 STATISTICS (uptime: {int(uptime)}s)")
            print("="*60)
            print(f"   Frames processed: {self.frame_count}")
            print(f"   Total detections: {self.detection_count}")
            print(f"   Avg inference time: {avg_inference:.1f}ms")
            print(f"   Avg FPS: {self.frame_count / uptime:.1f}")
            print("="*60 + "\n")
            
            self.last_report = now

def setup_logging():
    """Configure logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Console handler with UTF-8 encoding for emoji support
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=log_format,
        encoding='utf-8'
    )
    
    # File handler
    if config.LOG_TO_FILE:
        file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)
    
    return logging.getLogger('AeroBrain')

class StateMachine:
    """Simple state machine for drone control"""
    IDLE = "IDLE"
    SEARCHING = "SEARCHING"
    TRACKING = "TRACKING"
    LANDING = "LANDING"
    
    def __init__(self):
        self.state = self.IDLE
        self.state_time = time.time()
    
    def get_time_in_state(self):
        return time.time() - self.state_time
    
    def set_state(self, new_state):
        if self.state != new_state:
            self.state = new_state
            self.state_time = time.time()
            return True
        return False
