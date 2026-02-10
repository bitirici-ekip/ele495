import cv2
import time
import threading
import numpy as np
import os
from picamera2 import Picamera2
from PIL import Image
import tesserocr

# Single-threaded Tesseract is faster on ARM
os.environ["OMP_THREAD_LIMIT"] = "1"

# Global variables
current_gray = None        # Grayscale rotated frame for display
current_thresh = None      # Thresholded frame for OCR
last_boxes = []
stable_boxes = {}
lock = threading.Lock()
running = True
ocr_fps = 0.0
box_id_counter = 0

# Stability config
STABILITY_DURATION = 0.1   
IOU_MATCH_THRESHOLD = 0.4


def iou(box1, box2):
    """Intersection over Union between two (x,y,w,h) boxes."""
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    xi1, yi1 = max(x1, x2), max(y1, y2)
    xi2, yi2 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
    if xi2 <= xi1 or yi2 <= yi1:
        return 0.0
    inter = (xi2 - xi1) * (yi2 - yi1)
    union = w1 * h1 + w2 * h2 - inter
    return inter / union if union > 0 else 0.0


def update_stable_boxes(new_detections):
    """
    Stabilize detections: match by IoU, keep alive for STABILITY_DURATION.
    Prevents text from flickering on/off between frames.
    """
    global stable_boxes, box_id_counter
    now = time.time()

    for det in new_detections:
        best_id = None
        best_score = IOU_MATCH_THRESHOLD
        for bid, sbox in stable_boxes.items():
            score = iou(det['rect'], sbox['rect'])
            if score > best_score:
                best_score = score
                best_id = bid

        if best_id is not None:
            stable_boxes[best_id]['rect'] = det['rect']
            stable_boxes[best_id]['text'] = det['text']
            stable_boxes[best_id]['last_seen'] = now
        else:
            box_id_counter += 1
            stable_boxes[box_id_counter] = {
                'rect': det['rect'],
                'text': det['text'],
                'last_seen': now,
            }

    expired = [bid for bid, sbox in stable_boxes.items()
               if now - sbox['last_seen'] > STABILITY_DURATION]
    for bid in expired:
        del stable_boxes[bid]


def ocr_worker():
    """
    OCR thread using tesserocr C API.
    Uses thresholded image for OCR (best accuracy),
    but display shows grayscale (looks much better).
    """
    global current_thresh, last_boxes, running, ocr_fps

    api = tesserocr.PyTessBaseAPI(
        path='/usr/share/tesseract-ocr/5/tessdata/',
        lang='eng',
        psm=tesserocr.PSM.SPARSE_TEXT,   # PSM 11: finds scattered text & single chars
        oem=tesserocr.OEM.LSTM_ONLY       # OEM 1: fastest
    )
    api.SetVariable("tessedit_do_invert", "0")

    while running:
        if current_thresh is not None:
            t_start = time.time()

            with lock:
                frame_ocr = current_thresh.copy()

            img_h, img_w = frame_ocr.shape[:2]

            try:
                pil_image = Image.fromarray(frame_ocr)
                api.SetImage(pil_image)

                # WORD-level detection
                boxes = api.GetComponentImages(tesserocr.RIL.WORD, True)

                new_detections = []
                for i, (im, box, _, _) in enumerate(boxes):
                    x, y, w_box, h_box = box['x'], box['y'], box['w'], box['h']

                    # Bounds check: skip boxes outside image
                    if x < 0 or y < 0 or x + w_box > img_w or y + h_box > img_h:
                        continue
                    if w_box <= 0 or h_box <= 0:
                        continue

                    api.SetRectangle(x, y, w_box, h_box)
                    text = api.GetUTF8Text().strip()
                    conf = api.MeanTextConf()

                    if conf > 50 and text:
                        new_detections.append({
                            'rect': (x, y, w_box, h_box),
                            'text': text
                        })

                with lock:
                    update_stable_boxes(new_detections)
                    last_boxes = [{'rect': sb['rect'], 'text': sb['text']}
                                  for sb in stable_boxes.values()]

            except Exception as e:
                print(f"OCR Error: {e}")

            elapsed = time.time() - t_start
            if elapsed > 0:
                ocr_fps = 1.0 / elapsed

        time.sleep(0.001)

    api.End()


def main():
    global current_gray, current_thresh, running

    print("Initializing Picamera2...")
    try:
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(
            main={"size": (300, 400), "format": "RGB888"}
        )
        picam2.configure(config)
        picam2.start()

        try:
            picam2.set_controls({"AfMode": 2, "AwbMode": 0})
        except Exception as e:
            print(f"Warning: Could not set controls: {e}")

    except Exception as e:
        print(f"Failed to initialize Picamera2: {e}")
        return

    print("Camera active (300x400 Grayscale). Starting optimized OCR...")
    print("Press 'q' or Ctrl+C to exit.")

    t = threading.Thread(target=ocr_worker, daemon=True)
    t.start()

    frame_count = 0
    fps_start = time.time()
    display_fps = 0.0

    try:
        while True:
            frame_rgb = picam2.capture_array()

            # RGB -> Grayscale directly (no BGR step)
            gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
            gray_rotated = cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE)

            # Threshold for OCR only (not for display)
            blurred = cv2.GaussianBlur(gray_rotated, (3, 3), 0)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            kernel = np.ones((2, 2), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

            with lock:
                current_thresh = thresh.copy()

            # Display: grayscale (nice looking) with colored annotations
            display_frame = cv2.cvtColor(gray_rotated, cv2.COLOR_GRAY2BGR)

            with lock:
                boxes_to_draw = list(last_boxes)

            for item in boxes_to_draw:
                (x, y, w_b, h_b) = item['rect']
                text = item['text']
                cv2.rectangle(display_frame, (x, y), (x + w_b, y + h_b), (0, 255, 0), 2)
                cv2.putText(display_frame, text, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # FPS
            frame_count += 1
            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                display_fps = frame_count / elapsed
                frame_count = 0
                fps_start = time.time()

            fps_text = f"Cam: {display_fps:.0f} | OCR: {ocr_fps:.1f} FPS"
            cv2.putText(display_frame, fps_text, (5, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            cv2.imshow('Camera OCR (Live)', display_frame)

            if (cv2.waitKey(1) & 0xFF == ord('q')) or \
               (cv2.getWindowProperty('Camera OCR (Live)', cv2.WND_PROP_VISIBLE) < 1):
                break
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        picam2.stop()
        cv2.destroyAllWindows()
        print("Exited.")


if __name__ == "__main__":
    main()
