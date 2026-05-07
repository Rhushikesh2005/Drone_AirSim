import asyncio
from mavsdk import System

async def run():
    drone = System()
    print("Connecting to virtual drone...")
    
    # 🌟 ULTIMATE FIX: Windows ab loudspeaker par signal sunega
    await drone.connect(system_address="udpout://172.25.22.134:14580")
    
    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("-- Connected to drone! 🚀")
            break

    print("Waiting for drone to have a global position estimate...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("-- Global position state is good enough for flying.")
            break

    print("-- Arming")
    await drone.action.arm()

    print("-- Taking off")
    await drone.action.takeoff()

    await asyncio.sleep(10)

    print("-- Landing")
    await drone.action.land()

if __name__ == "__main__":
    asyncio.run(run())