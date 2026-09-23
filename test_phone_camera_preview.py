import cv2

CAMERA_INDEX = 1

cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

if not cap.isOpened():
    print(f"ERROR: Could not open camera index {CAMERA_INDEX}")
    raise SystemExit(1)

print(f"Camera {CAMERA_INDEX} opened successfully.")
print("Press Q to close.")

while True:
    ret, frame = cap.read()

    if not ret:
        print("ERROR: Failed to read frame.")
        break

    cv2.imshow("Mobile Camera Test", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

print("Camera released cleanly.")