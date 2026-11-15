#!/usr/bin/env python3
"""Test IR break beam sensor — watch the reading change in real time."""
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Watching IR sensor (GPIO 23)...")
print("Put something between the emitter and receiver to break the beam.")
print("Press Ctrl+C to stop.\n")

last_val = None
try:
    while True:
        val = GPIO.input(23)
        if val != last_val:
            if val == 0:
                print("IR: 0 (beam broken / coin detected)")
            else:
                print("IR: 1 (beam clear / no coin)")
            last_val = val
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nDone.")
    GPIO.cleanup()
