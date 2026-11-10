#!/usr/bin/env python3
"""Test both cameras and save test images."""
import cv2

for cam_id in [0, 2]:
    print(f"Testing camera {cam_id}...", end=" ")
    cap = cv2.VideoCapture(cam_id)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            filename = f"test_cam{cam_id}.jpg"
            cv2.imwrite(filename, frame)
            print(f"OK - saved {filename}")
        else:
            print("FAILED - could not read frame")
        cap.release()
    else:
        print("FAILED - could not open")
print("Done.")