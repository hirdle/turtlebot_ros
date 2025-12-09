import cv2
import numpy as np
import os
import colorsys

# import colorsys

# def rgb_to_hsv(r, g, b):
#     """Преобразовать RGB в HSV"""
#     h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
#     return h * 360, s * 100, v * 100

colors = {
    'blue': ((100, 100, 100), (130, 255, 255)),
    'green': ((40, 30, 30), (80, 255, 255)),
    'yellow': ((20, 100, 100), (40, 255, 255)),
    'red': None,  # два диапазона
}


def get_mask(frame, color):

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    kernel = np.ones((5, 5), np.uint8)

    if color != 'red':
        low, high = colors.get(color)
        mask = cv2.inRange(hsv, np.array(low), np.array(high))
    else:
        d1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
        d2 = cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(d1, d2)
    
    # улучшение маски
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    return mask


def find_contour(mask, min_area=100):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) > min_area]
    return max(contours, key=lambda x: cv2.contourArea(x)) if contours else None

def find_dominant_color(frame):
    best, best_area = None, 0

    for color in colors:
        area = cv2.countNonZero(get_mask(frame, color))
        if area > best_area:
            best, best_area = color, area

    return best


def crop_roi(frame, contour, pd=20, size=300):
    pts = contour.reshape(-1, 2)
    x1,y1 = pts.min(axis=0) - pd
    x2,y2 = pts.max(axis=0) + pd
    
    h,w = frame.shape[:2]
    x1,y1 = max(0,x1), max(0,y1)
    x1,y1 = min(w,x2), min(h,y2)

    roi = frame[int(y1):int(y2), int(x1):int(x2)]
    return cv2.resize(roi, (size, size)) if roi.size > 0 else None



def detect_traffic_light(frame, min_area=1000):

    result = []

    for color in colors:
        mask = get_mask(frame, color)
        contour = find_contour(mask, min_area=min_area)
        if contour is not None:
            result.append((color, cv2.contourArea(contour)))

    return sorted(result, key=lambda x: x[1], reverse=True)


def detect_sign(frame, templates, threshold):

    color = find_dominant_color(frame)
    mask = get_mask(frame, color)

    contour = find_contour(mask)
    if contour is None:
        return (False, None, 0)
    
    roi = crop_roi(frame, contour)
    if roi is None:
        return (False, None, 0)
    
    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    roi_gray_blur = cv2.GaussianBlur(roi_gray, (5, 5), 0)

    best_conf, best_name = 0, None

    for path in templates:

        tmp = cv2.imread(path)

        mask = get_mask(tmp, color)

        contour = find_contour(mask)
        if contour is None:
            continue
    
        tmp_roi = crop_roi(frame, contour)
        if tmp_roi is None:
            continue
        
        tmp_roi_gray = cv2.cvtColor(tmp_roi, cv2.COLOR_BGR2GRAY)
        tmp_roi_gray_blur = cv2.GaussianBlur(tmp_roi_gray, (5, 5), 0)
        tmp_roi_resized = cv2.resize(tmp_roi_gray_blur, (roi_gray_blur.shape[1], roi_gray_blur.shape[0]))

        result = cv2.matchTemplate(roi_gray_blur, tmp_roi_resized, cv2.TM_CCOEFF_NORMED)
        _, conf, _, _ = cv2.minMaxLoc(result)

        if conf > best_conf:
            best_conf, best_name = conf, os.path.basename(path)

    return (best_conf >= threshold, best_conf, best_name)


def detect_acuro(frame):

    acuro_dict = cv2.acuro.getPredefinedDictionary(cv2.acuro.DICT_7X7_50)
    params = cv2.acuro.DetectorParameters()

    detector = cv2.acuro.ACURODetector(acuro_dict, params)
    corners, ids, _ = detector.detectMarkers(frame)

    result = []

    if ids is None or len(ids) == 0:
        for i, corner in enumerate(corners):
            area = cv2.contourArea(corner[0].astype(np.float32))
            result.append((ids[i][0], corner, area))

    return result

