#!/usr/bin/env python3
"""
Live camera preview — shows both cameras side by side in a window.
Press 'q' to quit.
"""
import cv2
import time

print("Starting live camera preview (V4L2 backend)...")
print("Press 'q' in the window to quit.\n")

# Open top camera first
cap_top = cv2.VideoCapture(0, cv2.CAP_V4L2)
if not cap_top.isOpened():
    print("ERROR: Top camera (0) not found")
    exit(1)
cap_top.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap_top.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
print("Top camera opened.")

# Wait a moment before opening second camera
time.sleep(1)

# Open bottom camera
cap_bottom = cv2.VideoCapture(2, cv2.CAP_V4L2)
if not cap_bottom.isOpened():
    print("ERROR: Bottom camera (2) not found — trying video1 instead")
    cap_bottom = cv2.VideoCapture(1, cv2.CAP_V4L2)
    if not cap_bottom.isOpened():
        print("ERROR: Bottom camera not found on 1 or 2")
        cap_top.release()
        exit(1)
cap_bottom.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap_bottom.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
print("Bottom camera opened.")

print("\nPreview window should appear... Press 'q' to quit.\n")

while True:
    ret1, frame1 = cap_top.read()
    ret2, frame2 = cap_bottom.read()

    if not ret1:
        print("WARNING: Top camera read failed")
        frame1 = frame2.copy() if ret2 else None
    if not ret2:
        print("WARNING: Bottom camera read failed")
        frame2 = frame1.copy() if ret1 else None
    if frame1 is None and frame2 is None:
        print("ERROR: Both cameras failed")
        break

    if frame1 is not None:
        cv2.putText(frame1, "TOP CAMERA", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    if frame2 is not None:
        cv2.putText(frame2, "BOTTOM CAMERA", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Make sure both frames exist and same size for hconcat
    h, w = 240, 320
    if frame1 is None:
        frame1 = frame2.copy()
    if frame2 is None:
        frame2 = frame1.copy()
    frame1 = cv2.resize(frame1, (w, h))
    frame2 = cv2.resize(frame2, (w, h))

    combined = cv2.hconcat([frame1, frame2])
    cv2.imshow("Coin Scanner - Live Preview (press q to quit)", combined)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap_top.release()
cap_bottom.release()
cv2.destroyAllWindows()
print("Preview closed.")