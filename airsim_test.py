import airsim
import time
import cv2
import numpy as np

print("Connecting to AirSim...")
# Connect to the AirSim simulator running on your local Windows machine
client = airsim.MultirotorClient()
client.confirmConnection()
client.enableApiControl(True)
client.armDisarm(True)

print("Taking off...")
client.takeoffAsync().join()

print("Hovering and taking a picture...")
time.sleep(2)

# Request an image from the front-facing camera
responses = client.simGetImages([
    airsim.ImageRequest("0", airsim.ImageType.Scene, False, False)
])

# Convert the virtual image into a format OpenCV and YOLO can read
response = responses[0]
# THE FIX IS HERE: using frombuffer instead of fromstring
img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8) 
img_rgb = img1d.reshape(response.height, response.width, 3)

# Save the picture to your folder to prove it worked!
cv2.imwrite("drone_view.png", img_rgb)
print(">>> Picture saved as drone_view.png! <<<")

print("Landing...")
client.landAsync().join()

# Lock the drone back up
client.armDisarm(False)
client.enableApiControl(False)
print("Flight complete.")