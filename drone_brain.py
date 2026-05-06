
import cv2
import asyncio
from ultralytics import YOLO
from mavsdk import System

# AI Model Load
print("Loading AeroBrain AI Model...")
model = YOLO('yolov8n.pt')

# Frame Settings
FRAME_CENTER_X = 320
FRAME_CENTER_Y = 240
DEADZONE = 50  # Thoda buffer taaki drone baar-baar na hile

# --- DRONE CONTROL TASK ---
# --- DRONE CONTROL TASK ---
async def run_drone():
    drone = System()
    print("\n[SYSTEM] Connecting to Virtual Drone...")
    
    # Mission Planner ka default UDP port 14550 hota hai
    await drone.connect(system_address="udp://:14550")
    
    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(">>> DRONE DISCOVERED AND CONNECTED! <<<")
            break

    print("Checking GPS and Health (Simulation)...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print(">>> GPS Lock OK! Ready to fly. <<<")
            break

    print("--- ARMING MOTORS ---")
    await drone.action.arm()
    await asyncio.sleep(2) # 2 second wait karega

    print("--- TAKING OFF ---")
    await drone.action.takeoff()

    while True:
        # Abhi ke liye drone hawa mein hover karega
        await asyncio.sleep(1)

# --- AI VISION & DECISION TASK ---
async def run_vision():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while True:
        success, frame = cap.read()
        if not success:
            break

        results = model(frame, imgsz=640, conf=0.4, verbose=False)
        
        person_detected = False

        for r in results:
            boxes = r.boxes
            for box in boxes:
                if int(box.cls[0]) == 0:  # Class 0 = Person
                    person_detected = True
                    x1, y1, x2, y2 = int(box.xyxy[0][0]), int(box.xyxy[0][1]), int(box.xyxy[0][2]), int(box.xyxy[0][3])
                    
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    area = (x2 - x1) * (y2 - y1)

                    # 1. Left/Right Turn (YAW) Logic
                    error_x = center_x - FRAME_CENTER_X
                    if error_x > DEADZONE:
                        yaw_cmd = "YAW RIGHT ➔"
                    elif error_x < -DEADZONE:
                        yaw_cmd = "YAW LEFT  ⬅️"
                    else:
                        yaw_cmd = "CENTERED  ="

                    # 2. Forward/Backward (PITCH) Logic
                    if area < 40000:  # Box chhota hai, target door hai
                        pitch_cmd = "MOVE FORWARD ⬆️"
                    elif area > 90000:  # Box bohot bada hai, target paas hai
                        pitch_cmd = "MOVE BACKWARD ⬇️"
                    else:
                        pitch_cmd = "HOLD DISTANCE ="

                    # Terminal mein drone ki commands print karna
                    print(f"AI COMMAND -> [ {yaw_cmd} ]  |  [ {pitch_cmd} ]  |  Distance Area: {area}")

                    # UI par draw karna
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
                    
                    # Screen ke center mein ek crosshair (aim) banana
                    cv2.line(frame, (FRAME_CENTER_X, 0), (FRAME_CENTER_X, 480), (255, 255, 255), 1)
                    cv2.line(frame, (0, FRAME_CENTER_Y), (640, FRAME_CENTER_Y), (255, 255, 255), 1)

        if not person_detected:
            print("AI COMMAND -> [ SEARCHING FOR TARGET... ]")

        cv2.imshow("AeroBrain Target System", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        await asyncio.sleep(0.01)

    cap.release()
    cv2.destroyAllWindows()

# --- MAIN LOOP ---
async def main():
    print("Starting AeroBrain AI System...")
    await asyncio.gather(run_drone(), run_vision())

if __name__ == "__main__":
    asyncio.run(main())
