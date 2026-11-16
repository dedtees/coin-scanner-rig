#!/usr/bin/env python3
"""Test motor holding torque — is 12V reaching the DRV8825?"""
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)

GPIO.output(18, GPIO.LOW)
print("EN LOW - try turning the motor shaft NOW")
print("You have 5 seconds...")
time.sleep(5)
GPIO.output(18, GPIO.HIGH)
print("Done. Was the shaft stiff or easy to turn?")
GPIO.cleanup()
