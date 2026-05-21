import cv2
import numpy as np
import airsim
from ultralytics import YOLO
import os
import sys
import time
import logging

# Import configuration and utilities
import config
from utils import FPSCounter, DetectionSmoother, ObjectTracker, Statistics, setup_logging, StateMachine

# Setup logging
logger = setup_logging()

# AI Model Load
logger.info("Loading AeroBrain AI Model...")
try:
    if not os.path.exists(config.YOLO_MODEL):
        logger.error(f"YOLO model not found: {config.YOLO_MODEL}")
        sys.exit(1)
    model = YOLO(config.YOLO_MODEL)
    logger.info(f"[OK] YOLO Model loaded: {config.YOLO_MODEL}")
    logger.info(f"[OK] Available classes: {list(model.names.values())}")
except Exception as e:
    logger.error(f"FATAL: Failed to load YOLO model: {e}")
    sys.exit(1)

# Initialize utilities
fps_counter = FPSCounter()
smoother = DetectionSmoother(factor=config.SMOOTHING_FACTOR)
tracker = ObjectTracker() if config.ENABLE_TRACKING else None
stats = Statistics()
state_machine = StateMachine() if config.USE_STATE_MACHINE else None
frame_skip_counter = 0

def main():
    client = None
    try:
        logger.info("=" * 60)
        logger.info("🚁 AeroBrain Drone AI System Starting...")
        logger.info("=" * 60)
        logger.info("Connecting to AirSim Virtual Drone...")
        logger.info(f"Target: {config.AIRSIM_HOST}:{config.AIRSIM_PORT}")
        
        # 1. Connect to AirSim
        try:
            logger.info("Attempting to create MultirotorClient...")
            client = airsim.MultirotorClient()
            logger.info("Confirming connection...")
            client.confirmConnection()
            logger.info("[OK] Successfully connected to AirSim")
        except Exception as e:
            logger.error(f"❌ Cannot connect to AirSim: {e}")
            logger.error(f"Connection error type: {type(e).__name__}")
            logger.error("\n⚠️  TROUBLESHOOTING:")
            logger.error("  1. Make sure AirSim simulator is running")
            logger.error("  2. Check that the IP address and port are correct")
            logger.error("  3. Verify firewall settings")
            logger.error("  4. Try: python -c \"import airsim; print('AirSim module OK')\"")
            return
        
        try:
            logger.info("Enabling API control...")
            client.enableApiControl(True)
            logger.info("Arming motors...")
            client.armDisarm(True)
            logger.info("[OK] Motors armed successfully")
        except Exception as e:
            logger.error(f"❌ Failed to arm drone: {e}")
            logger.error(f"Arming error type: {type(e).__name__}")
            return

        logger.info("--- TAKING OFF ---")
        try:
            # Get drone state before takeoff
            drone_state = client.getMultirotorState()
            logger.info(f"Drone altitude before takeoff: {drone_state.kinematics_estimated.position.z_val:.2f}m")
            
            logger.info("Executing takeoff command...")
            takeoff_task = client.takeoffAsync()
            takeoff_task.join()  # AirSim join() doesn't support 'timeout'
            
            # Verify takeoff success
            time.sleep(2)  # Give it a moment to gain altitude
            drone_state_after = client.getMultirotorState()
            alt_after = drone_state_after.kinematics_estimated.position.z_val
            logger.info(f"Drone altitude after takeoff: {alt_after:.2f}m")
            
            if abs(alt_after) < 1.0: # Altitude is negative Z in AirSim
                logger.warning("Drone might not have gained enough altitude.")
            
            logger.info("[OK] Drone took off successfully")
        except Exception as e:
            logger.error(f"❌ TAKEOFF FAILED: {e}")
            logger.error(f"Takeoff exception type: {type(e).__name__}")
            logger.error("\n⚠️  TROUBLESHOOTING:")
            logger.error("  1. Make sure AirSim simulator is running")
            logger.error("  2. Ensure the drone is on the ground (not already flying)")
            logger.error("  3. Check for insufficient clearance above ground")
            logger.error("  4. Verify motors armed successfully")
            
            # Try to recover
            try:
                logger.info("Attempting emergency landing...")
                client.landAsync().join()
                client.armDisarm(False)
                client.enableApiControl(False)
            except:
                pass
            return
        
        logger.info(">>> Drone is hovering. Initiating AI Vision... <<<")

        # 2. Main AI Loop
        loop_count = 0
        while True:
            frame_start_time = time.time()
            
            try:
                # Frame skip for performance
                frame_skip_counter_val = loop_count % config.FRAME_SKIP
                if frame_skip_counter_val != 0:
                    loop_count += 1
                    continue
                
                # Get image from AirSim
                inference_start = time.time()
                responses = client.simGetImages([
                    airsim.ImageRequest("0", airsim.ImageType.Scene, False, False)
                ])
                
                if not responses:
                    logger.warning("No image response from AirSim")
                    loop_count += 1
                    continue
                
                # Convert AirSim image
                response = responses[0]
                img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8) 
                frame = img1d.reshape(response.height, response.width, 3)
                frame = cv2.resize(frame, (config.FRAME_WIDTH, config.FRAME_HEIGHT))

                # Run YOLO inference
                try:
                    results = model(frame, conf=config.YOLO_CONFIDENCE, imgsz=config.YOLO_IMGSZ, verbose=False)
                    inference_time = time.time() - inference_start
                except Exception as e:
                    logger.warning(f"YOLO inference failed: {e}")
                    loop_count += 1
                    continue
        
                person_detected = False
                best_box = None
                best_class_name = None
                largest_area = 0
                all_detections = []  # Store all detections for display

                # Process detections - DETECT ALL CLASSES
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        try:
                            class_id = int(box.cls[0])
                            class_name = model.names[class_id]
                            confidence = float(box.conf[0])
                            x1, y1, x2, y2 = int(box.xyxy[0][0]), int(box.xyxy[0][1]), int(box.xyxy[0][2]), int(box.xyxy[0][3])
                            area = (x2 - x1) * (y2 - y1)
                            
                            # Log all detections
                            logger.info(f"Detected: {class_name} (ID: {class_id}, Conf: {confidence:.2f}, Area: {area})")
                            
                            # Store detection info
                            all_detections.append({
                                'class_id': class_id,
                                'class_name': class_name,
                                'confidence': confidence,
                                'box': [x1, y1, x2, y2],
                                'area': area
                            })
                            
                            # Track the largest detected object for drone control
                            if area > largest_area:
                                largest_area = area
                                best_box = [x1, y1, x2, y2]
                                best_class_name = class_name
                                person_detected = True
                        except Exception as e:
                            logger.warning(f"Box processing error: {e}")
                            continue

                # Update state machine
                if config.USE_STATE_MACHINE:
                    if person_detected:
                        state_machine.set_state(StateMachine.TRACKING)
                    else:
                        if state_machine.get_time_in_state() > config.AUTO_LAND_ON_LOSS:
                            state_machine.set_state(StateMachine.LANDING)
                        else:
                            state_machine.set_state(StateMachine.SEARCHING)

                # Apply smoothing
                if person_detected and best_box and config.USE_DETECTION_SMOOTHING:
                    best_box = smoother.smooth(best_box)

                # Update tracker                if config.ENABLE_TRACKING and person_detected and best_box:
                    tracked_objects = tracker.update([best_box])
                else:
                    tracker.update([])

                # Generate drone commands and send movement to drone
                command_info = ""
                if person_detected and best_box:
                    x1, y1, x2, y2 = best_box
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    area = largest_area

                    # YAW (Left/Right) - Rotate to center target horizontally
                    error_x = center_x - config.FRAME_CENTER_X
                    yaw_rate = 0  # degrees per second
                    if error_x > config.YAW_DEADZONE:
                        yaw_rate = 15  # Rotate right
                        yaw_cmd = f"YAW RIGHT ➔ {min(config.YAW_MAX_ANGLE, abs(error_x * 60 / config.FRAME_WIDTH)):.1f}°"
                    elif error_x < -config.YAW_DEADZONE:
                        yaw_rate = -15  # Rotate left
                        yaw_cmd = f"YAW LEFT ⬅ {min(config.YAW_MAX_ANGLE, abs(error_x * 60 / config.FRAME_WIDTH)):.1f}°"
                    else:
                        yaw_rate = 0
                        yaw_cmd = "CENTERED ="

                    # PITCH (Forward/Backward) - Move to maintain distance
                    vx = 0  # Forward/backward velocity
                    if area < config.DISTANCE_TOO_FAR:
                        vx = 2.0  # Move forward faster
                        pitch_cmd = "MOVE FORWARD ⬆⬆"
                    elif area > config.DISTANCE_TOO_CLOSE:
                        vx = -1.0  # Move backward
                        pitch_cmd = "MOVE BACKWARD ⬇"
                    else:
                        vx = 0.5  # Slight forward to maintain
                        pitch_cmd = "HOLD DISTANCE ="

                    command_info = f"🎯 TARGET ({best_class_name}) | {yaw_cmd} | {pitch_cmd} | Area: {area}"
                    
                    # Send movement commands to drone
                    try:
                        # Move forward/backward while rotating to face target
                        client.moveByVelocityAsync(vx, 0, 0, 1)  # (forward, right, down, duration)
                        if yaw_rate != 0:
                            client.rotateByYawRateAsync(yaw_rate, 0.5)
                    except Exception as e:
                        logger.warning(f"Failed to send movement command: {e}")
                    
                    # Draw primary target on frame
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
                    cv2.putText(frame, f"{best_class_name} ({area})", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                else:
                    command_info = "🔍 SEARCHING FOR OBJECTS"
                    # Stop moving when searching
                    try:
                        client.moveByVelocityAsync(0, 0, 0, 0.1)
                    except Exception as e:
                        logger.warning(f"Failed to stop drone: {e}")

                # Draw all detected objects on frame
                for detection in all_detections:
                    if detection['box'] != best_box:  # Don't redraw the main target
                        x1, y1, x2, y2 = detection['box']
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 1)  # Blue for non-primary detections
                        cv2.putText(frame, f"{detection['class_name']}", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

                # Draw UI elements
                cv2.line(frame, (config.FRAME_CENTER_X, 0), (config.FRAME_CENTER_X, config.FRAME_HEIGHT), (255, 255, 255), 1)
                cv2.line(frame, (0, config.FRAME_CENTER_Y), (config.FRAME_WIDTH, config.FRAME_CENTER_Y), (255, 255, 255), 1)
                
                # Add status text
                fps_val = fps_counter.fps
                state_text = state_machine.state if config.USE_STATE_MACHINE else "ACTIVE"
                num_detections = len(all_detections)
                status = f"FPS: {fps_val:.1f} | State: {state_text} | Detections: {num_detections}"
                cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                if config.LOG_DETECTIONS:
                    logger.info(command_info)

                # Display frame
                cv2.imshow("AeroBrain Target System (AirSim)", frame)

                # Save debug frame if enabled
                if config.SAVE_DEBUG_FRAMES:
                    os.makedirs(config.DEBUG_FRAME_DIR, exist_ok=True)
                    cv2.imwrite(f"{config.DEBUG_FRAME_DIR}/frame_{loop_count:06d}.png", frame)

                # Record statistics
                stats.record_frame(num_detections=len(all_detections), inference_time=inference_time)
                stats.report()

                # Check for exit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("Landing and shutting down...")
                    break
                
                # Update FPS
                fps_counter.tick()
                loop_count += 1

            except KeyboardInterrupt:
                logger.warning("INTERRUPTED: Landing drone...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(1)
                loop_count += 1
                continue
                
    except Exception as e:
        logger.error(f"FATAL: {e}")
    finally:
        # Graceful shutdown
        try:
            if client is not None:
                logger.info("Landing drone...")
                client.landAsync().join()
                time.sleep(2)
                client.armDisarm(False)
                client.enableApiControl(False)
                logger.info("✅ Drone safely landed and disarmed")
        except Exception as e:
            logger.warning(f"Shutdown warning: {e}")
        finally:
            cv2.destroyAllWindows()
            logger.info("🏁 Shutdown complete")
            stats.report(force=True)

if __name__ == "__main__":
    main()