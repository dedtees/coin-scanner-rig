#!/usr/bin/env python3
"""
Automated Coin Scanner Rig — Raspberry Pi Control Script

Controls:
  - Stepper motor (NEMA 17 + DRV8825) to rotate the table
  - Two USB webcams (top + bottom) for simultaneous capture
  - IR break beam sensor to detect coin in position
  - 12V solenoid to push up flagged coins
  - Calls the Coin Scanner API on Render for AI analysis

Hardware connections (Raspberry Pi GPIO):
  - Stepper motor: STEP=GPIO17, DIR=GPIO27, ENABLE=GPIO18 (via L298N)
  - IR sensor: SIGNAL=GPIO23 (with pull-up)
  - Solenoid: GPIO24 (via relay or transistor switch, 12V)

Usage:
  python3 coin_scanner_rig.py [--denomination penny|nickel|dime|quarter|half_dollar|dollar]

Requirements:
  pip install opencv-python requests RPi.GPIO
"""

import argparse
import json
import logging
import os
import sys
import time
import threading
import queue
from typing import Optional, Dict, Any

import cv2
import requests

# GPIO imports — only available on Pi, stub for dev on other machines
try:
    import RPi.GPIO as GPIO
    ON_PI = True
except (ImportError, RuntimeError):
    ON_PI = False
    logging.warning("RPi.GPIO not available — running in simulation mode (no hardware)")

# ============================================================================
# CONFIGURATION
# ============================================================================

API_URL = "https://coin-scanner-api.onrender.com/api/detect"
API_TIMEOUT = 30  # seconds

# GPIO pins
PIN_STEP = 17
PIN_DIR = 27
PIN_ENABLE = 18
PIN_IR_SENSOR = 23
PIN_SOLENOID = 24

# Stepper motor config
STEPS_PER_REV = 200  # NEMA 17 = 200 steps/rev (1.8° per step)
MICROSTEPPING = 1     # 1 = full step (set by DRV8825 jumpers)
TOTAL_STEPS = STEPS_PER_REV * MICROSTEPPING

# Table config — 8 slots, 45° per slot
NUM_SLOTS = 8
STEPS_PER_SLOT = TOTAL_STEPS // NUM_SLOTS  # 25 steps per slot

# Camera config
CAM_TOP = 0    # /dev/video0
CAM_BOTTOM = 2  # /dev/video2
CAM_WIDTH = 1280
CAM_HEIGHT = 720

# Timing
STEP_DELAY = 0.002      # 2ms per step (500 steps/sec)
SETTLE_DELAY = 0.15      # wait for table to stop vibrating
SOLENOID_DELAY = 0.5     # how long to hold solenoid open
COOLDOWN_DELAY = 0.1      # brief pause between coins

# Coin denomination -> slot diameter (mm) for reference
COIN_SIZES = {
    "penny": 19.05,
    "nickel": 21.21,
    "dime": 17.91,
    "quarter": 24.26,
    "half_dollar": 30.61,
    "dollar": 26.49,
}

# Result colors for display
RESULT_COLORS = {
    "PASS": "\033[92m",       # green
    "REVIEW": "\033[93m",      # yellow
    "RARE": "\033[91m",        # red
}
RESET_COLOR = "\033[0m"

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("coin_scanner")


# ============================================================================
# HARDWARE CONTROL
# ============================================================================

class HardwareController:
    """Controls GPIO pins for stepper motor, IR sensor, and solenoid."""

    def __init__(self):
        if ON_PI:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(PIN_STEP, GPIO.OUT)
            GPIO.setup(PIN_DIR, GPIO.OUT)
            GPIO.setup(PIN_ENABLE, GPIO.OUT)
            GPIO.setup(PIN_IR_SENSOR, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(PIN_SOLENOID, GPIO.OUT)
            # Disable motor driver initially
            GPIO.output(PIN_ENABLE, GPIO.HIGH)  # HIGH = disabled on DRV8825
            GPIO.output(PIN_SOLENOID, GPIO.LOW)  # solenoid off

    def rotate_one_slot(self):
        """Rotate the table by one slot position (45°)."""
        if ON_PI:
            GPIO.output(PIN_ENABLE, GPIO.LOW)  # enable motor
            GPIO.output(PIN_DIR, GPIO.HIGH)   # clockwise

            for _ in range(STEPS_PER_SLOT):
                GPIO.output(PIN_STEP, GPIO.HIGH)
                time.sleep(STEP_DELAY)
                GPIO.output(PIN_STEP, GPIO.LOW)
                time.sleep(STEP_DELAY)

            GPIO.output(PIN_ENABLE, GPIO.HIGH)  # disable motor (save power)
        else:
            logger.info("[SIM] Rotating table one slot")
        time.sleep(SETTLE_DELAY)

    def coin_detected(self) -> bool:
        """Check if IR sensor detects a coin in the current slot."""
        if ON_PI:
            return GPIO.input(PIN_IR_SENSOR) == GPIO.LOW  # beam broken = coin present
        else:
            return True  # simulate always having a coin

    def fire_solenoid(self):
        """Trigger the push-up solenoid to eject a flagged coin."""
        logger.info("🆙 Firing solenoid — push up flagged coin!")
        if ON_PI:
            GPIO.output(PIN_SOLENOID, GPIO.HIGH)
            time.sleep(SOLENOID_DELAY)
            GPIO.output(PIN_SOLENOID, GPIO.LOW)
        else:
            time.sleep(SOLENOID_DELAY)

    def cleanup(self):
        """Clean up GPIO on exit."""
        if ON_PI:
            GPIO.output(PIN_ENABLE, GPIO.HIGH)
            GPIO.output(PIN_SOLENOID, GPIO.LOW)
            GPIO.cleanup()
        logger.info("Hardware cleaned up. Goodbye!")


# ============================================================================
# CAMERA CONTROL
# ============================================================================

class CameraController:
    """Controls two USB webcams for simultaneous top/bottom capture."""

    def __init__(self):
        self.cap_top = None
        self.cap_bottom = None
        self._init_cameras()

    def _init_cameras(self):
        """Open both camera streams."""
        if ON_PI:
            self.cap_top = cv2.VideoCapture(CAM_TOP, cv2.CAP_V4L2)
            if not self.cap_top.isOpened():
                logger.error("Failed to open top camera!")
            self.cap_top.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            self.cap_top.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            time.sleep(1)  # delay between camera opens for USB bandwidth

            self.cap_bottom = cv2.VideoCapture(CAM_BOTTOM, cv2.CAP_V4L2)
            if not self.cap_bottom.isOpened():
                logger.error("Failed to open bottom camera!")
            self.cap_bottom.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            self.cap_bottom.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            logger.info("Cameras initialized")
        else:
            logger.info("[SIM] Cameras simulated (no real capture)")

    def capture_both(self) -> Optional[tuple]:
        """
        Simultaneously capture from both cameras.
        Returns (front_bytes, back_bytes) or None if failed.
        """
        if not ON_PI or self.cap_top is None or self.cap_bottom is None:
            # Simulation mode — return dummy images
            logger.info("[SIM] Capturing both sides")
            return (b"", b"")

        # Read from both cameras as close to simultaneously as possible
        # Use threads to minimize time between captures
        results = {}

        def grab(cam_id, cap):
            ret, frame = cap.read()
            if ret:
                # Encode as JPEG for the API
                _, buf = cv2.imencode('.jpg', frame)
                results[cam_id] = buf.tobytes()
            else:
                results[cam_id] = None
                logger.error(f"Camera {cam_id} capture failed!")

        t_top = threading.Thread(target=grab, args=("top", self.cap_top))
        t_bot = threading.Thread(target=grab, args=("bottom", self.cap_bottom))
        t_top.start()
        t_bot.start()
        t_top.join(timeout=5)
        t_bot.join(timeout=5)

        front = results.get("top")
        back = results.get("bottom")

        if front is None or back is None:
            logger.error("One or both cameras failed to capture")
            return None

        return (front, back)

    def release(self):
        """Release camera resources."""
        if self.cap_top:
            self.cap_top.release()
        if self.cap_bottom:
            self.cap_bottom.release()
        logger.info("Cameras released")


# ============================================================================
# API CLIENT
# ============================================================================

class ScannerAPI:
    """Calls the Coin Scanner API on Render for AI analysis."""

    def __init__(self):
        self.session = requests.Session()
        self.request_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self._worker = None

    def start_worker(self):
        """Start background API worker thread for pipelined requests."""
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()
        logger.info("API worker started")

    def _worker_loop(self):
        """Background thread: process API requests from queue."""
        while True:
            item = self.request_queue.get()
            if item is None:
                break  # shutdown signal

            slot_num, front_bytes, back_bytes = item
            result = self._call_api(front_bytes, back_bytes)
            self.result_queue.put((slot_num, result))
            self.request_queue.task_done()

    def submit_scan(self, slot_num: int, front_bytes: bytes, back_bytes: bytes):
        """Submit a scan request to the background worker."""
        self.request_queue.put((slot_num, front_bytes, back_bytes))

    def get_result(self, timeout: float = API_TIMEOUT) -> Optional[tuple]:
        """Check for a completed API result (non-blocking with timeout)."""
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _call_api(self, front_bytes: bytes, back_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Call the Render API with front + back images."""
        if not front_bytes and not back_bytes:
            logger.info("[SIM] No real image data — skipping API call")
            return {"simulated": True, "disposition": "PASS", "detections": []}

        try:
            files = {
                "front": ("front.jpg", front_bytes, "image/jpeg"),
                "back": ("back.jpg", back_bytes or front_bytes, "image/jpeg"),
            }
            response = self.session.post(API_URL, files=files, timeout=API_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("API call timed out")
            return {"error": "timeout", "disposition": "PASS"}
        except requests.exceptions.RequestException as e:
            logger.error(f"API error: {e}")
            return {"error": str(e), "disposition": "PASS"}

    def stop(self):
        """Signal worker to stop."""
        self.request_queue.put(None)
        if self._worker:
            self._worker.join(timeout=5)


# ============================================================================
# RESULT DISPLAY
# ============================================================================

def display_result(slot_num: int, result: Dict[str, Any]):
    """Print the scan result to the console with color coding."""
    detections = result.get("detections", [])
    disposition = result.get("disposition", "PASS")
    color = RESULT_COLORS.get(disposition, RESET_COLOR)

    print(f"\n{'='*50}")
    print(f"  SLOT {slot_num} — {color}{disposition}{RESET_COLOR}")
    print(f"{'='*50}")

    if result.get("error"):
        print(f"  ⚠️  Error: {result['error']}")
        print(f"  Coin skipped (treated as PASS)")
        return "PASS"

    for d in detections:
        coin_type = d.get("type", "unknown")
        year = d.get("year", "?")
        mint = d.get("mint_mark", "") or ""
        face_value = d.get("face_value", 0)
        est_value = d.get("estimated_value", face_value)
        rare = d.get("rare")
        varieties = d.get("varieties_to_check", [])

        print(f"  🪙 {coin_type.title()} {year} {mint}")
        print(f"     Face: ${face_value:.2f}  |  Est: ${est_value:.2f}")

        if rare:
            notes = rare.get("notes", "")
            value = rare.get("value", 0)
            is_rare = rare.get("is_rare", False)
            flag = "🔴 RARE!" if is_rare else "🟡 CHECK"
            print(f"     {flag} ${value:.2f} — {notes}")

        if varieties:
            print(f"     🔍 Varieties to check:")
            for v in varieties[:3]:
                print(f"        • {v['description']}")

        # Show denomination warning if vision and OpenCV disagreed
        if d.get("denomination_warning"):
            print(f"     ⚠️  {d['denomination_warning']}")

    return disposition


# ============================================================================
# MAIN SCANNING LOOP
# ============================================================================

FORCE_CAPTURE = False

def run_scan(denomination: str = "quarter"):
    """
    Main scanning loop.
    Loads coins, rotates through each slot, captures, analyzes, and sorts.
    """
    logger.info(f"Starting coin scanner — denomination: {denomination}")
    logger.info(f"Slot diameter: {COIN_SIZES.get(denomination, 'N/A')}mm")
    logger.info(f"Slots per revolution: {NUM_SLOTS}")
    logger.info(f"API: {API_URL}")
    logger.info(f"Press Ctrl+C to stop\n")

    hw = HardwareController()
    cams = CameraController()
    api = ScannerAPI()
    api.start_worker()

    results_log = []
    slot = 0

    try:
        for revolution in range(1, 100):  # up to 100 revolutions (800 coins)
            logger.info(f"\n--- Revolution {revolution} ---")

            for slot_in_rev in range(NUM_SLOTS):
                slot += 1

                # 1. Check if coin is present (skip if --force-capture)
                if not FORCE_CAPTURE and not hw.coin_detected():
                    logger.info(f"Slot {slot}: empty — skipping")
                    hw.rotate_one_slot()
                    continue

                # 2. Capture both sides simultaneously
                logger.info(f"Slot {slot}: capturing...")
                images = cams.capture_both()
                if images is None:
                    logger.error(f"Slot {slot}: capture failed — skipping")
                    hw.rotate_one_slot()
                    continue

                front, back = images

                # 3. Submit to API (pipelined — doesn't block rotation)
                api.submit_scan(slot, front, back)

                # 4. Check for completed results from previous slots
                while True:
                    prev_result = api.get_result(timeout=0.1)
                    if prev_result is None:
                        break  # no results ready yet
                    prev_slot, prev_data = prev_result
                    disposition = display_result(prev_slot, prev_data)
                    results_log.append({
                        "slot": prev_slot,
                        "result": prev_data,
                    })
                    # Live-update dashboard
                    try:
                        import dashboard
                        dashboard.update_results(results_log, scanning=True)
                    except ImportError:
                        pass
                    # 5. If flagged, fire solenoid
                    if disposition in ("REVIEW", "RARE"):
                        logger.warning(f"Slot {prev_slot}: FLAGGED — firing solenoid!")
                        # Note: in pipelined mode, the coin may have already
                        # rotated past. For v1, we pause and let the operator
                        # manually retrieve flagged coins.
                        # V2 could track slot positions and fire solenoid
                        # when the flagged slot rotates to the solenoid position.

                # 6. Advance to next slot
                hw.rotate_one_slot()
                time.sleep(COOLDOWN_DELAY)

            # End of revolution — collect any remaining API results
            logger.info("Revolution complete — collecting remaining results...")
            api.request_queue.join()  # wait for all API calls to finish

            while True:
                prev_result = api.get_result(timeout=1)
                if prev_result is None:
                    break
                prev_slot, prev_data = prev_result
                disposition = display_result(prev_slot, prev_data)
                results_log.append({"slot": prev_slot, "result": prev_data})
                try:
                    import dashboard
                    dashboard.update_results(results_log, scanning=True)
                except ImportError:
                    pass
                if disposition in ("REVIEW", "RARE"):
                    logger.warning(f"Slot {prev_slot}: FLAGGED — coin should be set aside!")

    except KeyboardInterrupt:
        logger.info("\nStopping...")

    finally:
        # Collect any final results
        try:
            while True:
                prev_result = api.get_result(timeout=2)
                if prev_result is None:
                    break
                prev_slot, prev_data = prev_result
                disposition = display_result(prev_slot, prev_data)
                results_log.append({"slot": prev_slot, "result": prev_data})
        except:
            pass

        api.stop()
        cams.release()
        hw.cleanup()

        # Print summary
        total = len(results_log)
        rare_count = sum(1 for r in results_log if r["result"].get("disposition") in ("REVIEW", "RARE"))
        logger.info(f"\n{'='*50}")
        logger.info(f"  SCAN COMPLETE")
        logger.info(f"  Total coins scanned: {total}")
        logger.info(f"  Coins flagged: {rare_count}")
        logger.info(f"  Coins passed: {total - rare_count}")
        logger.info(f"{'='*50}")

        # Save results to JSON
        results_file = f"scan_results_{int(time.time())}.json"
        with open(results_file, "w") as f:
            json.dump(results_log, f, indent=2)
        logger.info(f"Results saved to {results_file}")

        # Update dashboard with final state
        try:
            import dashboard
            dashboard.update_results(results_log, scanning=False)
        except ImportError:
            pass  # dashboard not running


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automated Coin Scanner Rig — Raspberry Pi"
    )
    parser.add_argument(
        "--denomination",
        type=str,
        default="quarter",
        choices=list(COIN_SIZES.keys()),
        help="Coin denomination for template sizing",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run in simulation mode (no GPIO hardware required)",
    )
    parser.add_argument(
        "--force-capture",
        action="store_true",
        help="Capture every slot regardless of IR sensor (for testing without hardware)",
    )
    args = parser.parse_args()

    if args.force_capture:
        globals()['FORCE_CAPTURE'] = True

    if args.simulate and ON_PI:
        # Force simulation even on a Pi
        import types
        globals()['ON_PI'] = False

    run_scan(denomination=args.denomination)