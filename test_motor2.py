#!/usr/bin/env python3
"""Test stepper motor — slow spin with debug info."""
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
print("Enabling motor...")
GPIO.output(ENABLE_PIN, GPIO.LOW)
time.sleep(0.5)

# Set direction
print("Setting direction HIGH...")
GPIO.output(DIR_PIN, GPIO.HIGH)
time.sleep(0.5)

print("Stepping slowly (50 steps, 10ms each)...")
for i in range(50):
    GPIO.output(STEP_PIN, GPIO.HIGH)
    time.sleep(0.01)
    GPIO.output(STEP_PIN, GPIO.LOW)
    time.sleep(0.01)
    if i % 10 == 0:
        print(f"  Step {i}/50")

print("Now faster (200 steps, 3ms each)...")
for i in range(200):
    GPIO.output(STEP_PIN, GPIO.HIGH)
    time.sleep(0.003)
    GPIO.output(STEP_PIN, GPIO.LOW)
    time.sleep(0.003)

# Disable motor
print("Disabling motor...")
GPIO.output(ENABLE_PIN, GPIO.HIGH)
GPIO.cleanup()
print("Done. Did the motor move at all? Even a twitch?")
