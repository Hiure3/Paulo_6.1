import sys, cv2
img = cv2.imread(sys.argv[1]); val, _, _ = cv2.QRCodeDetector().detectAndDecode(img); print(val)
