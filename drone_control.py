"""
AirSim Drone Control Helper Module

Provides high-level functions for common drone operations:
- Takeoff and landing
- Position-based movement
- Velocity-based tracking
- Safe shutdown
"""

import airsim
import time
import logging

logger = logging.getLogger(__name__)


class DroneController:
    """Wrapper around AirSim MultirotorClient for safer, easier control."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 41451):
        """
        Initialize and connect to AirSim.
        
        Args:
            host: AirSim server IP
            port: AirSim server port
        """
        self.client = airsim.MultirotorClient(ip=host, port=port)
        self.is_armed = False
        self.is_flying = False
    
    def connect(self) -> bool:
        """
        Confirm connection and initialize drone.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.confirmConnection()
            logger.info("[OK] Connected to AirSim")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to AirSim: {e}")
            return False
    
    def arm_and_enable(self) -> bool:
        """
        Enable API control and arm motors.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.enableApiControl(True)
            logger.info("API control enabled")
            self.client.armDisarm(True)
            self.is_armed = True
            logger.info("[OK] Motors armed")
            return True
        except Exception as e:
            logger.error(f"Failed to arm: {e}")
            return False
    
    def takeoff(self, altitude: float = 5.0) -> bool:
        """
        Takeoff and hover at altitude.
        
        Args:
            altitude: Target altitude in meters (positive = up)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_armed:
                logger.warning("Motors not armed. Arming now...")
                if not self.arm_and_enable():
                    return False
            
            logger.info(f"Taking off to {altitude}m...")
            self.client.takeoffAsync().join()
            
            # Climb straight up to target altitude (NED: Z is negative for up)
            logger.info(f"Climbing to {altitude}m at 3m/s...")
            self.client.moveToZAsync(-float(altitude), 3).join()
            
            time.sleep(1)
            self.is_flying = True
            logger.info("[OK] Takeoff complete")
            return True
        except Exception as e:
            logger.error(f"Takeoff failed: {e}")
            return False
    
    def land(self) -> bool:
        """
        Land and disarm the drone.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Landing...")
            self.client.landAsync().join()
            time.sleep(2)
            self.is_flying = False
            logger.info("[OK] Landed successfully")
            return True
        except Exception as e:
            logger.error(f"Landing failed: {e}")
            return False
    
    def disarm(self) -> bool:
        """Disarm motors and disable API control."""
        try:
            self.client.armDisarm(False)
            self.client.enableApiControl(False)
            self.is_armed = False
            logger.info("[OK] Disarmed")
            return True
        except Exception as e:
            logger.error(f"Failed to disarm: {e}")
            return False
    
    def move_by_velocity(self, vx: float, vy: float, vz: float, 
                        yaw_rate: float = 0.0, duration: float = 0.1) -> bool:
        """
        Move drone by velocity (world frame).
        
        Args:
            vx: Forward velocity (m/s)
            vy: Right velocity (m/s)
            vz: Down velocity (m/s, negative = up)
            yaw_rate: Yaw rotation rate (deg/s)
            duration: Duration of command (seconds)
        
        Returns:
            True if successful
        """
        try:
            yaw_mode = airsim.YawMode(is_rate=True, yaw_or_rate=yaw_rate)
            self.client.moveByVelocityAsync(vx, vy, vz, duration, yaw_mode=yaw_mode)
            return True
        except Exception as e:
            logger.warning(f"Velocity command failed: {e}")
            return False
    
    def move_by_velocity_body_frame(self, forward: float, right: float, down: float,
                                   yaw_rate: float = 0.0, duration: float = 0.1) -> bool:
        """
        Move drone by velocity in body frame (relative to drone orientation).
        
        Args:
            forward: Forward velocity (m/s)
            right: Right velocity (m/s)
            down: Down velocity (m/s, positive = down)
            yaw_rate: Yaw rotation rate (deg/s)
            duration: Duration of command (seconds)
        
        Returns:
            True if successful
        """
        try:
            yaw_mode = airsim.YawMode(is_rate=True, yaw_or_rate=yaw_rate)
            self.client.moveByVelocityBodyFrameAsync(forward, right, down, duration, yaw_mode=yaw_mode)
            return True
        except Exception as e:
            logger.warning(f"Body frame velocity command failed: {e}")
            return False
    
    def move_to_position(self, x: float, y: float, z: float, velocity: float = 1.0) -> bool:
        """
        Move to absolute position (blocking).
        
        Args:
            x, y, z: Target position
            velocity: Movement speed (m/s)
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Moving to position ({x}, {y}, {z})...")
            self.client.moveToPositionAsync(x, y, z, velocity).join()
            return True
        except Exception as e:
            logger.error(f"Move to position failed: {e}")
            return False
    
    def rotate_to_yaw(self, yaw_deg: float) -> bool:
        """
        Rotate to absolute yaw heading (blocking).
        
        Args:
            yaw_deg: Target yaw in degrees
        
        Returns:
            True if successful
        """
        try:
            self.client.rotateToYawAsync(yaw_deg).join()
            return True
        except Exception as e:
            logger.error(f"Rotate failed: {e}")
            return False
    
    def get_state(self) -> airsim.MultirotorState:
        """
        Get current drone state (position, velocity, orientation).
        
        Returns:
            MultirotorState object
        """
        try:
            return self.client.getMultirotorState()
        except Exception as e:
            logger.warning(f"Failed to get state: {e}")
            return None
    
    def get_position(self) -> tuple:
        """
        Get current position (x, y, z).
        
        Returns:
            Tuple of (x, y, z) in meters, or None if failed
        """
        state = self.get_state()
        if state:
            pos = state.kinematics_estimated.position
            return (pos.x_val, pos.y_val, pos.z_val)
        return None
    
    def get_velocity(self) -> tuple:
        """
        Get current velocity (vx, vy, vz) in m/s.
        
        Returns:
            Tuple of (vx, vy, vz), or None if failed
        """
        state = self.get_state()
        if state:
            vel = state.kinematics_estimated.linear_velocity
            return (vel.x_val, vel.y_val, vel.z_val)
        return None
    
    def get_altitude(self) -> float:
        """
        Get current altitude (negative Z in AirSim).
        
        Returns:
            Altitude in meters (positive = up)
        """
        pos = self.get_position()
        if pos:
            return -pos[2]  # Negate Z (AirSim uses NED)
        return None
    
    def hover(self, duration: float = 1.0) -> None:
        """Stop and hover in place."""
        self.move_by_velocity(0, 0, 0, 0, duration)
    
    def safe_shutdown(self) -> None:
        """Emergency landing and cleanup."""
        try:
            if self.is_flying:
                logger.info("Emergency landing...")
                self.land()
            if self.is_armed:
                self.disarm()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def track_target_with_velocity(controller: DroneController,
                               target_center_x: int, target_center_y: int, target_area: int,
                               frame_center_x: int, frame_center_y: int,
                               frame_width: int, frame_height: int,
                               desired_area: int, yaw_deadzone: int = 50,
                               distance_too_far: int = 5000, distance_too_close: int = 20000) -> str:
    """
    Generate and send velocity commands to track a target in frame.
    
    Uses body frame for intuitive control: forward/back for distance, yaw for centering.
    
    Args:
        controller: DroneController instance
        target_center_x, target_center_y: Pixel center of target
        target_area: Pixel area of target bounding box
        frame_center_x, frame_center_y: Center of frame
        frame_width, frame_height: Frame dimensions
        desired_area: Ideal area to maintain (for distance)
        yaw_deadzone: Pixels from center before yaw corrects
        distance_too_far: Area threshold for "too far"
        distance_too_close: Area threshold for "too close"
    
    Returns:
        String describing the command sent
    """
    
    # YAW CONTROL: Rotate to center target horizontally
    error_x = target_center_x - frame_center_x
    yaw_rate = 0.0
    yaw_cmd = ""
    
    if error_x > yaw_deadzone:
        yaw_rate = 15.0  # Rotate right
        yaw_cmd = f"YAW RIGHT ➔"
    elif error_x < -yaw_deadzone:
        yaw_rate = -15.0  # Rotate left
        yaw_cmd = f"YAW LEFT ⬅"
    else:
        yaw_rate = 0.0
        yaw_cmd = "CENTERED ="
    
    # PITCH CONTROL: Move forward/back to maintain distance
    forward_velocity = 0.5  # Slight forward to maintain position
    pitch_cmd = ""
    
    if target_area < distance_too_far:
        forward_velocity = 2.0  # Move forward faster
        pitch_cmd = "MOVE FORWARD ⬆⬆"
    elif target_area > distance_too_close:
        forward_velocity = -1.0  # Move backward
        pitch_cmd = "MOVE BACKWARD ⬇"
    else:
        forward_velocity = 0.5
        pitch_cmd = "HOLD DISTANCE ="
    
    # Send command in body frame (forward/right/down relative to drone)
    controller.move_by_velocity_body_frame(
        forward=forward_velocity,
        right=0.0,
        down=0.0,
        yaw_rate=yaw_rate,
        duration=0.1  # Short duration; will be re-issued each loop
    )
    
    command_info = f"{yaw_cmd} | {pitch_cmd} | Area: {target_area}"
    return command_info
