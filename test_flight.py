import asyncio
from mavsdk import System
import sys
import time

async def run():
    """
    Complete test flight with error handling for MAVSDK/PX4 simulation
    """
    drone = System()
    connection_timeout = 30  # seconds
    start_time = time.time()
    
    try:
        print("[SYSTEM] Connecting to virtual drone via MAVSDK...")
        print("   Expected connection: UDP at 172.25.22.134:14580")
        
        # Connection attempt with timeout
        try:
            await asyncio.wait_for(
                drone.connect(system_address="udpout://172.25.22.134:14580"),
                timeout=connection_timeout
            )
            print("✅ Connection attempt initiated")
        except asyncio.TimeoutError:
            print(f"⚠️  WARNING: Connection timeout after {connection_timeout}s")
            print("   Make sure:")
            print("   - PX4 SITL simulator is running")
            print("   - MAVProxy bridge is active")
            print("   - Correct IP address and port")
            return
        except Exception as e:
            print(f"❌ ERROR: Connection failed: {e}")
            return
        
        print("Waiting for drone to connect...")
        try:
            async with asyncio.timeout(10):
                async for state in drone.core.connection_state():
                    if state.is_connected:
                        print("✅ Connected to drone!")
                        break
                    else:
                        print(f"   Status: {state}")
        except asyncio.TimeoutError:
            print("⚠️  WARNING: Connection state check timed out")
            return
        except Exception as e:
            print(f"❌ ERROR: Connection state error: {e}")
            return

        print("\nWaiting for drone to have a global position estimate...")
        try:
            async with asyncio.timeout(15):
                async for health in drone.telemetry.health():
                    if health.is_global_position_ok and health.is_home_position_ok:
                        print("✅ Global position and home position established")
                        print(f"   - Global Position OK: {health.is_global_position_ok}")
                        print(f"   - Home Position OK: {health.is_home_position_ok}")
                        break
                    else:
                        print(f"   Health Check: GPS={health.is_global_position_ok}, Home={health.is_home_position_ok}")
        except asyncio.TimeoutError:
            print("⚠️  WARNING: Health check timed out - proceeding anyway")
        except Exception as e:
            print(f"❌ ERROR: Health check failed: {e}")
            return

        try:
            print("\n[FLIGHT] Arming motors...")
            await drone.action.arm()
            print("✅ Motors armed successfully")
        except Exception as e:
            print(f"❌ ERROR: Failed to arm motors: {e}")
            return

        try:
            print("[FLIGHT] Taking off...")
            await drone.action.takeoff()
            print("✅ Takeoff initiated")
        except Exception as e:
            print(f"❌ ERROR: Takeoff failed: {e}")
            await drone.action.disarm()
            return

        try:
            print("[FLIGHT] Hovering for 10 seconds...")
            await asyncio.sleep(10)
            print("✅ Hover complete")
        except Exception as e:
            print(f"❌ ERROR: Hover interrupted: {e}")
            return

        try:
            print("[FLIGHT] Landing...")
            await drone.action.land()
            print("✅ Landing initiated")
            
            # Wait for landing to complete
            landing_timeout = 30
            async with asyncio.timeout(landing_timeout):
                async for flight_mode in drone.telemetry.flight_mode():
                    print(f"   Flight mode: {flight_mode}")
            print("✅ Landing complete")
        except asyncio.TimeoutError:
            print(f"⚠️  WARNING: Landing timeout after {landing_timeout}s - forcing disarm")
        except Exception as e:
            print(f"❌ ERROR: Landing failed: {e}")
            return
        
        print("\n🎉 Test flight completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️  INTERRUPTED by user")
        try:
            print("Emergency landing...")
            await drone.action.land()
            await asyncio.sleep(5)
        except:
            pass
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        return
    finally:
        try:
            await drone.action.disarm()
            print("✅ Motors disarmed")
        except:
            pass

if __name__ == "__main__":
    print("=" * 60)
    print("🚁 MAVSDK PX4 SITL Test Flight")
    print("=" * 60)
    try:
        asyncio.run(run())
    except Exception as e:
        print(f"❌ FATAL: {e}")
        sys.exit(1)
