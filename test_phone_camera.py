import cv2

print("=" * 60)
print("PHONE / EXTERNAL CAMERA DETECTION TEST")
print("=" * 60)

for index in range(10):
    print(f"\nTesting camera index {index}...")

    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("  Status: NOT OPENED")
        cap.release()
        continue

    ret, frame = cap.read()

    if ret and frame is not None:
        height, width = frame.shape[:2]

        print("  Status: OPENED")
        print(f"  Resolution: {width}x{height}")
        print("  Frame Read: SUCCESS")
    else:
        print("  Status: OPENED BUT FRAME READ FAILED")

    cap.release()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)