#!/usr/bin/env python3
"""Test stepper motor — try both enable polarities and longer pulses."""
import RPi.GPIO as GPIO
import time

DIR_PIN = 20
STEP_PIN = 21
ENABLE_PIN = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(DIR_PIN, GPIO.OUT)
GPIO.setup(STEP_PIN, GPIO.OUT)
GPIO.setup(ENABLE_PIN, GPIO.OUT)

# Try 1: EN LOW (standard DRV8825)
print("=== Test 1: EN LOW (standard enable) ===")
GPIO.output(ENABLE_PIN, GPIO.LOW)
GPIO.output(DIR_PIN, GPIO.HIGH)
time.sleep(0.5)
print("Stepping 200 steps, 5ms each...")
for i in range(200):
    GPIO.output(STEP_PIN, GPIO.HIGH)
    time.sleep(0.005)
    GPIO.output(STEP_PIN, GPIO.LOW)
    time.sleep(0.005)
print("Test 1 done. Did motor move?")
time.sleep(1)

# Try 2: EN HIGH (some boards are active HIGH)
print("\n=== Test 2: EN HIGH (inverted enable) ===")
GPIO.output(ENABLE_PIN, GPIO.HIGH)
GPIO.output(DIR_PIN, GPIO.HIGH)
time.sleep(0.5)
print("Stepping 200 steps, 5ms each...")
for i in range(200):
    GPIO.output(STEP_PIN, GPIO.HIGH)
    time.sleep(0.005)
    GPIO.output(STEP_PIN, GPIO.LOW)
    time.sleep(0.005)
print("Test 2 done. Did motor move?")
time.sleep(1)

# Try 3: Direct STEP without EN control (float EN)
print("\n=== Test 3: EN floating, just stepping ===")
GPIO.setup(ENABLE_PIN, GPIO.IN)  # float the EN pin
GPIO.output(DIR_PIN, GPIO.HIGH)
time.sleep(0.5)
print("Stepping 200 steps, 5ms each...")
for i in range(200):
    GPIO.output(STEP_PIN, GPIO.HIGH)
    time.sleep(0.005)
    GPIO.output(STEP_PIN, GPIO.LOW)
    time.sleep(0.005)
print("Test 3 done. Did motor move?")

GPIO.cleanup()
print("\nAll tests complete.")
