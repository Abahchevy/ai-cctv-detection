"""
Simple test - try loading a generic YOLOv8 person detector
"""
import cv2

print("Testing webcam feed directly...\n")

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    print("ERROR: Cannot open webcam!")
    exit(1)

print("Webcam opened successfully!")
print("Checking frame capture...\n")

for i in range(5):
    ret, frame = cap.read()
    if not ret:
        print(f"Frame {i+1}: FAILED to read")
    else:
        h, w, c = frame.shape
        mean_brightness = frame.mean()
        print(f"Frame {i+1}: OK - {w}x{h}, brightness={mean_brightness:.1f}")
        
        # Show the frame
        cv2.imshow("Webcam Test", frame)
        cv2.waitKey(1000)  # Show for 1 second

cap.release()
cv2.destroyAllWindows()

print("\n✓ Webcam test complete")
print("Check:")
print("  • Can you see yourself in the frames?")
print("  • Is the image clear and well-lit?")
print("  • If dark/blurry, improve lighting and try again")
