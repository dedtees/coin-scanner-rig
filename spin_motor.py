#!/usr/bin/env python3
"""Spin stepper motor continuously. Press Ctrl+C to stop."""
import RPi.GPIO as GPIO
import time

DIR_PIN = 20
STEP_PIN = 21
ENABLE_PIN = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(DIR_PIN, GPIO.OUT)
GPIO.setup(STEP_PIN, GPIO.OUT)
GPIO.setup(ENABLE_PIN, GPIO.OUT)

GPIO.output(ENABLE_PIN, GPIO.LOW)
GPIO.output(DIR_PIN, GPIO.HIGH)

print("Motor spinning continuously. Press Ctrl+C to stop.")
try:
    while True:
        GPIO.output(STEP_PIN, GPIO.HIGH)
        time.sleep(0.002)
        GPIO.output(STEP_PIN, GPIO.LOW)
        time.sleep(0.002)
except KeyboardInterrupt:
    GPIO.output(ENABLE_PIN, GPIO.HIGH)
    GPIO.cleanup()
    print("\nStopped.")
