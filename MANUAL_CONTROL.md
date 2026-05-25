# Manual Control Guide for AeroBrain

This document describes the manual flight controls and related configuration options for the AeroBrain drone system.

## Quick Start
- Start the system:

```powershell
python drone_brain.py
```
- Press `M` to toggle between AI and Manual modes.

## Key Mappings (while the CV window is focused)
- `M` : Toggle AI / Manual mode
- `q` : Land and shut down the program

Manual mode controls (intended for use when mode = Manual):
- `W` : Pitch forward (move forward)
- `S` : Pitch backward (move backward)
- `A` : Roll left
- `D` : Roll right
- `Q` : Yaw left  (note: see conflict below)
- `E` : Yaw right
- `R` : Altitude up (in AirSim negative Z = up)
- `F` : Altitude down

## Configuration Parameters
You can tune these values in `config.py`:

- `TAKEOFF_ALTITUDE` : Default takeoff altitude in meters. Increase this to raise the initial altitude (e.g., 15.0).
- `MANUAL_THROTTLE_FACTOR` : Vertical speed multiplier used for manual `R`/`F` controls. Increase for faster climb/descent.
- `PITCH_MAX_SPEED` : Limits forward/backward speed in AI control.
- `YAW_DEADZONE` : Pixels from center where yaw corrections are suppressed to avoid jitter.

Example: to raise default takeoff altitude to 15 m, set:
```python
TAKEOFF_ALTITUDE = 15.0
```

## Important Notes / Known Issue
- The code currently uses the key `q` both for "yaw left" in the manual input handler and for quitting/landing in the main loop. Because the main loop checks the quit key before passing inputs to the manual handler, pressing `q` will trigger landing and program exit rather than yawing.

Recommendation: If you want `q` to yaw while in Manual mode, we can either:
- Change the quit key to a different key (for example `z`), or
- Remap yaw-left in `drone_brain.py` to a different key (for example `z`).

Tell me which behavior you prefer and I can patch the code accordingly.

## Troubleshooting
- If the drone does not reach the expected altitude on takeoff:
  - Make sure `TAKEOFF_ALTITUDE` is set to the desired value.
  - Verify AirSim is running and connected.
  - Check logs in `aerobrain.log` for arming/takeoff errors.

## Contact
If you want this document added to the README instead, or want an in-app overlay showing the controls, say so and I will implement it.
