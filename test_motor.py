#!/usr/bin/env python3
"""Test stepper motor — spin one revolution."""
import RPi.GPIO as GPIO
import time

DIR_PIN = 20
STEP_PIN = 21
ENABLE_PIN = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(DIR_PIN, GPIO.OUT)
GPIO.setup(STEP_PIN, GPIO.OUT)
GPIO.setup(ENABLE_PIN, GPIO.OUT)

# Enable motor (LOW = enabled)
GPIO.output(ENABLE_PIN, GPIO.LOW)
time.sleep(0.1)

# Set direction
GPIO.output(DIR_PIN, GPIO.HIGH)

print("Spinning motor one revolution (200 steps)...")
for i in range(200):
    GPIO.output(STEP_PIN, GPIO.HIGH)
    time.sleep(0.002)
    GPIO.output(STEP_PIN, GPIO.LOW)
    time.sleep(0.002)

# Disable motor
GPIO.output(ENABLE_PIN, GPIO.HIGH)
GPIO.cleanup()
print("Done! Motor should have spun one full revolution.")
