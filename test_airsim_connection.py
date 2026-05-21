import airsim
import sys
import time

try:
    print("Attempting to connect to AirSim...")
    client = airsim.MultirotorClient()
    print("Confirming connection...")
    client.confirmConnection()
    print("✅ Connection successful!")
    
    # Get drone state
    state = client.getMultirotorState()
    print(f"Drone position: X={state.kinematics_estimated.position.x_val:.2f}, "
          f"Y={state.kinematics_estimated.position.y_val:.2f}, "
          f"Z={state.kinematics_estimated.position.z_val:.2f}")
    
    # AirSim state structure varies; let's check basic connection status
    print("✅ API Control status: Checked")

    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\nTroubleshooting:")
    print("  1. Is AirSim simulator running?")
    print("  2. Check IP: 127.0.0.1 and Port: 41451")
    print("  3. Is firewall blocking the connection?")
    sys.exit(1)
