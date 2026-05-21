#!/usr/bin/env python3
"""
AirSim Setup & Verification Script
This script verifies and configures AirSim for the AeroBrain project
"""

import os
import sys
import subprocess
import platform

print("=" * 70)
print("🚁 AeroBrain - AirSim Setup & Verification")
print("=" * 70)

# Check Python version
print("\n[1/5] Checking Python version...")
if sys.version_info >= (3, 8):
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} OK")
else:
    print(f"❌ Python 3.8+ required (found {sys.version_info.major}.{sys.version_info.minor})")
    sys.exit(1)

# Check operating system
print("\n[2/5] Checking operating system...")
if platform.system() != "Windows":
    print(f"⚠️  WARNING: This project is optimized for Windows (found {platform.system()})")
else:
    print("✅ Windows detected")

# Check required packages
print("\n[3/5] Checking required Python packages...")
required_packages = {
    'airsim': 'pip install airsim',
    'ultralytics': 'pip install ultralytics',
    'opencv-python': 'pip install opencv-python',
    'numpy': 'pip install numpy',
    'flask': 'pip install flask',
}

missing_packages = []
for package, install_cmd in required_packages.items():
    try:
        __import__(package)
        print(f"   ✅ {package}")
    except ImportError:
        print(f"   ❌ {package} - MISSING")
        missing_packages.append(package)

if missing_packages:
    print(f"\n❌ Missing packages detected. Install them using:")
    for package in missing_packages:
        print(f"   pip install {package}")
    sys.exit(1)

# Check model file
print("\n[4/5] Checking YOLO model...")
if os.path.exists('yolov8n.pt'):
    size_mb = os.path.getsize('yolov8n.pt') / (1024 * 1024)
    print(f"✅ yolov8n.pt found ({size_mb:.1f} MB)")
else:
    print("❌ yolov8n.pt not found")
    print("   Run: python -c 'from ultralytics import YOLO; YOLO(\"yolov8n.pt\")'")

# Test AirSim connection
print("\n[5/5] Testing AirSim connection...")
try:
    import airsim
    client = airsim.MultirotorClient()
    client.confirmConnection()
    print("✅ Connected to AirSim successfully!")
    print("   - AirSim is running and accessible")
    print("   - Client is ready for drone operations")
except Exception as e:
    print(f"❌ Cannot connect to AirSim: {e}")
    print("\n   TROUBLESHOOTING:")
    print("   1. Download AirSim from: https://github.com/microsoft/AirSim/releases")
    print("   2. Extract and run: AirSim.exe (Windows)")
    print("   3. Make sure port 41451 is not blocked")
    print("   4. Try again once AirSim is running")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ All checks passed! You're ready to run AeroBrain")
print("=" * 70)
print("\nQuick Start:")
print("  1. Make sure AirSim.exe is running")
print("  2. Run: python drone_brain.py")
print("  3. Or run Flask dashboard: python app.py")
print("=" * 70)
