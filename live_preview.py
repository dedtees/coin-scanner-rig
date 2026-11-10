import cv2

# Force V4L2 backend instead of GStreamer
print("Starting live camera preview (V4L2 backend)...")
print("Press 'q' in the window to quit.\n")

cap_top = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap_bottom = cv2.VideoCapture(2, cv2.CAP_V4L2)

if not cap_top.isOpened():
    print("ERROR: Top camera (0) not found")
    exit(1)
if not cap_bottom.isOpened():
    print("ERROR: Bottom camera (2) not found")
    exit(1)

for cap in [cap_top, cap_bottom]:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Cameras opened. Preview window should appear...")
print("Press 'q' to quit.\n")

while True:
    ret1, frame1 = cap_top.read()
    ret2, frame2 = cap_bottom.read()

    if not ret1 or not ret2:
        print("ERROR: Failed to read from cameras")
        break

    cv2.putText(frame1, "TOP CAMERA", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame2, "BOTTOM CAMERA", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    combined = cv2.hconcat([frame1, frame2])
    cv2.imshow("Coin Scanner - Live Preview (press q to quit)", combined)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap_top.release()
cap_bottom.release()
cv2.destroyAllWindows()
print("Preview closed.")
