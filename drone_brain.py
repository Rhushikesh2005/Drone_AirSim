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
from drone_control import DroneController, track_target_with_velocity

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

# Validate configuration
logger.info("Validating configuration...")
if config.TAKEOFF_ALTITUDE < 2.0:
    logger.error(f"❌ INVALID CONFIG: TAKEOFF_ALTITUDE ({config.TAKEOFF_ALTITUDE}m) must be at least 2.0m for safe flight")
    logger.error("⚠️  Update TAKEOFF_ALTITUDE in config.py to >= 2.0")
    sys.exit(1)
logger.info(f"[OK] Takeoff altitude validated: {config.TAKEOFF_ALTITUDE}m")

# Initialize utilities
fps_counter = FPSCounter()
smoother = DetectionSmoother(factor=config.SMOOTHING_FACTOR)
tracker = ObjectTracker() if config.ENABLE_TRACKING else None
stats = Statistics()
state_machine = StateMachine() if config.USE_STATE_MACHINE else None
frame_skip_counter = 0

# Flight mode variables
current_mode = "AI"  # "AI" or "Manual"
manual_pitch = 0.0   # Forward/backward velocity
manual_roll = 0.0    # Left/right velocity
manual_yaw_rate = 0.0  # Yaw rotation rate
manual_throttle = 0.0  # Vertical velocity (Z axis)

# Patrol Mode variables
patrol_state = "ROTATING"  # "ROTATING" or "MOVING_FORWARD"
patrol_start_time = time.time()
last_patrol_forward_start = 0.0

def process_manual_input(key):
    """Process keyboard input for manual flight control"""
    global manual_pitch, manual_roll, manual_yaw_rate, manual_throttle
    
    speed_factor = 1.0  # Velocity command magnitude
    yaw_factor = 15.0   # Yaw rotation rate
    throttle_factor = config.MANUAL_THROTTLE_FACTOR  # Vertical speed
    
    if key == ord('w'):  # Pitch forward
        manual_pitch = speed_factor
    elif key == ord('s'):  # Pitch backward
        manual_pitch = -speed_factor
    elif key == ord('a'):  # Roll left
        manual_roll = -speed_factor
    elif key == ord('d'):  # Roll right
        manual_roll = speed_factor
    elif key == ord('q'):  # Yaw left
        manual_yaw_rate = -yaw_factor
    elif key == ord('e'):  # Yaw right
        manual_yaw_rate = yaw_factor
    elif key == ord('r'):  # Altitude up
        manual_throttle = -throttle_factor  # Negative Z = up in AirSim
    elif key == ord('f'):  # Altitude down
        manual_throttle = throttle_factor   # Positive Z = down in AirSim

def main():
    global current_mode, manual_pitch, manual_roll, manual_yaw_rate, manual_throttle
    global patrol_state, patrol_start_time, last_patrol_forward_start
    controller = None
    try:
        logger.info("=" * 60)
        logger.info("🚁 AeroBrain Drone AI System Starting...")
        logger.info("=" * 60)
        logger.info("Connecting to AirSim Virtual Drone...")
        logger.info(f"Target: {config.AIRSIM_HOST}:{config.AIRSIM_PORT}")
        
        # 1. Connect to AirSim
        try:
            logger.info("Attempting to create DroneController...")
            controller = DroneController(host=config.AIRSIM_HOST, port=config.AIRSIM_PORT)
            if not controller.connect():
                logger.error("❌ Cannot connect to AirSim")
                logger.error("\n⚠️  TROUBLESHOOTING:")
                logger.error("  1. Make sure AirSim simulator is running")
                logger.error("  2. Check that the IP address and port are correct")
                logger.error("  3. Verify firewall settings")
                logger.error("  4. Try: python -c \"import airsim; print('AirSim module OK')\"")
                return
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
            logger.info("Enabling API control and arming...")
            if not controller.arm_and_enable():
                logger.error("❌ Failed to arm drone")
                return
            logger.info("[OK] Motors armed successfully")
        except Exception as e:
            logger.error(f"❌ Failed to arm drone: {e}")
            logger.error(f"Arming error type: {type(e).__name__}")
            return

            logger.info("--- TAKING OFF ---")
        try:
            # Get drone state before takeoff
            alt_before = controller.get_altitude()
            logger.info(f"Drone altitude before takeoff: {alt_before:.2f}m")
            
            logger.info("Executing takeoff command...")
            if not controller.takeoff(altitude=config.TAKEOFF_ALTITUDE):
                logger.error("❌ TAKEOFF FAILED")
                logger.error("\n⚠️  TROUBLESHOOTING:")
                logger.error("  1. Make sure AirSim simulator is running")
                logger.error("  2. Ensure the drone is on the ground (not already flying)")
                logger.error("  3. Check for insufficient clearance above ground")
                logger.error("  4. Verify motors armed successfully")
                controller.safe_shutdown()
                return
            
            # Verify takeoff success
            alt_after = controller.get_altitude()
            logger.info(f"Drone altitude after takeoff: {alt_after:.2f}m")
            logger.info("[OK] Drone took off successfully")
        except Exception as e:
            logger.error(f"❌ TAKEOFF FAILED: {e}")
            logger.error(f"Takeoff exception type: {type(e).__name__}")
            controller.safe_shutdown()
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
                responses = controller.client.simGetImages([
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

                # Update tracker
                if config.ENABLE_TRACKING and person_detected and best_box:
                    tracked_objects = tracker.update([best_box])
                else:
                    tracker.update([])

                # Generate drone commands and send movement to drone
                command_info = ""
                if person_detected and best_box:
                    # Reset patrol variables when target is found
                    patrol_state = "ROTATING"
                    patrol_start_time = time.time()
                    
                    x1, y1, x2, y2 = best_box
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    area = largest_area

                    # Send movement commands to drone (only in AI mode)
                    if current_mode == "AI":
                        try:
                            # Use helper function for velocity tracking
                            command_info = track_target_with_velocity(
                                controller,
                                target_center_x=center_x,
                                target_center_y=center_y,
                                target_area=area,
                                frame_center_x=config.FRAME_CENTER_X,
                                frame_center_y=config.FRAME_CENTER_Y,
                                frame_width=config.FRAME_WIDTH,
                                frame_height=config.FRAME_HEIGHT,
                                desired_area=config.DISTANCE_TOO_FAR,
                                yaw_deadzone=config.YAW_DEADZONE,
                                distance_too_far=config.DISTANCE_TOO_FAR,
                                distance_too_close=config.DISTANCE_TOO_CLOSE
                            )
                            command_info = f"🎯 TARGET ({best_class_name}) | {command_info}"
                        except Exception as e:
                            logger.warning(f"Failed to send movement command: {e}")
                    
                    # Draw primary target on frame
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
                    cv2.putText(frame, f"{best_class_name} ({area})", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                else:
                    command_info = "🔍 SEARCHING FOR OBJECTS"
                    # Patrol logic (only in AI mode)
                    if current_mode == "AI":
                        current_time = time.time()
                        try:
                            if patrol_state == "ROTATING":
                                # 360 rotation at 30 deg/s = 12 seconds
                                if current_time - patrol_start_time >= 12.0:
                                    patrol_state = "MOVING_FORWARD"
                                    last_patrol_forward_start = current_time
                                    logger.info(">>> Patrol: Rotation complete. Moving forward... <<<")
                                else:
                                    controller.move_by_velocity_body_frame(forward=0, right=0, down=0, yaw_rate=30, duration=0.1)
                                    command_info = f"🔄 PATROL: ROTATING ({int((current_time - patrol_start_time)/12.0*100)}%)"
                            
                            elif patrol_state == "MOVING_FORWARD":
                                if current_time - last_patrol_forward_start >= 3.0:
                                    patrol_state = "ROTATING"
                                    patrol_start_time = current_time
                                    logger.info(">>> Patrol: Forward move complete. Rotating... <<<")
                                else:
                                    controller.move_by_velocity_body_frame(forward=2.0, right=0, down=0, yaw_rate=0, duration=0.1)
                                    command_info = f"🚀 PATROL: MOVING FORWARD ({int(3.0 - (current_time - last_patrol_forward_start))}s)"
                        except Exception as e:
                            logger.warning(f"Patrol command failed: {e}")

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
                mode_text = f"MODE: {current_mode}"
                # Read altitude from controller (meters, positive = up)
                try:
                    altitude = controller.get_altitude()
                    altitude_text = f"{altitude:.1f}m" if altitude is not None else "N/A"
                except Exception:
                    altitude_text = "ERR"
                status = f"FPS: {fps_val:.1f} | {mode_text} | State: {state_text} | Detections: {num_detections} | Alt: {altitude_text}"
                cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
                # Display manual control info if in Manual mode
                if current_mode == "Manual":
                    manual_info = f"Controls: W/S=Pitch A/D=Roll Q/E=Yaw R/F=Alt | P:{manual_pitch:.2f} R:{manual_roll:.2f} Y:{manual_yaw_rate:.1f}°/s"
                    cv2.putText(frame, manual_info, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
                
                # Display mode toggle hint
                hint_text = "Press 'M' to toggle mode"
                cv2.putText(frame, hint_text, (10, config.FRAME_HEIGHT - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

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

                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    logger.info("Landing and shutting down...")
                    break
                elif key == ord('m'):
                    # Toggle between AI and Manual mode
                    if current_mode == "AI":
                        current_mode = "Manual"
                        logger.info("🎮 SWITCHED TO MANUAL MODE")
                    else:
                        current_mode = "AI"
                        manual_pitch = 0.0
                        manual_roll = 0.0
                        manual_yaw_rate = 0.0
                        manual_throttle = 0.0
                        logger.info("🤖 SWITCHED TO AI MODE")
                elif current_mode == "Manual" and key != 255:
                    # Process manual flight inputs
                    process_manual_input(key)
                
                # Send manual control commands if in Manual mode
                if current_mode == "Manual":
                    try:
                        # Apply manual controls in body frame
                        if manual_pitch != 0 or manual_roll != 0 or manual_throttle != 0 or manual_yaw_rate != 0:
                            controller.move_by_velocity_body_frame(
                                forward=manual_pitch,
                                right=manual_roll,
                                down=manual_throttle,
                                yaw_rate=manual_yaw_rate,
                                duration=0.1
                            )
                        
                        # Decay controls gradually when no key is pressed
                        manual_pitch *= 0.9
                        manual_roll *= 0.9
                        manual_yaw_rate *= 0.9
                        manual_throttle *= 0.9
                    except Exception as e:
                        logger.warning(f"Failed to send manual control: {e}")
                
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
            if controller is not None:
                controller.safe_shutdown()
                logger.info("✅ Drone safely landed and disarmed")
        except Exception as e:
            logger.warning(f"Shutdown warning: {e}")
        finally:
            cv2.destroyAllWindows()
            logger.info("🏁 Shutdown complete")
            stats.report(force=True)

if __name__ == "__main__":
    main()