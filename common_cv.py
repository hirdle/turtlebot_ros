
import cv2
import numpy as np


# ============ ДЕТЕКЦИЯ ЦВЕТА ============

def detect_color(image, lower_hsv, upper_hsv):
    """Детекция произвольного цвета по HSV диапазону"""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower = np.array(lower_hsv, dtype=np.uint8)
    upper = np.array(upper_hsv, dtype=np.uint8)
    mask = cv2.inRange(hsv, lower, upper)
    
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return mask


def detect_blue(image):
    """Детекция синего цвета, возвращает маску"""
    return detect_color(image, (100, 100, 100), (130, 255, 255))


def detect_red(image):
    """Детекция красного цвета, возвращает маску"""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
    mask = cv2.bitwise_or(mask1, mask2)
    
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return mask


def detect_green(image):
    """Детекция зеленого цвета, возвращает маску"""
    return detect_color(image, (40, 90, 70), (80, 255, 255))


def detect_yellow(image):
    """Детекция желтого цвета, возвращает маску"""
    return detect_color(image, (20, 100, 100), (40, 255, 255))


def detect_dominant_color(image):
    """
    Автоматически определить доминирующий цвет на изображении.
    
    Args:
        image: изображение
        debug: если True, возвращает (цвет, словарь_площадей, словарь_масок)
    
    Returns:
        color или (color, areas_dict, masks_dict) если debug=True
    """
    color_detectors = {
        'blue': detect_blue,
        'red': detect_red,
        'green': detect_green,
        'yellow': detect_yellow
    }
    
    best_color = 'blue'
    best_area = 0
    areas = {}
    masks = {}
    
    for color_name, detector in color_detectors.items():
        mask = detector(image)
        area = cv2.countNonZero(mask)
        areas[color_name] = area
        masks[color_name] = mask
        if area > best_area:
            best_area = area
            best_color = color_name
    
    return best_color


# Детекция объекта
color_detectors = {
    'blue': detect_blue,
    'red': detect_red,
    'green': detect_green,
    'yellow': detect_yellow
}

# ============ КОНТУРЫ И ROI ============

def find_largest_contour(mask, min_area=100):
    """Найти самый большой контур. Возвращает контур или None"""

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filtered = [c for c in contours if cv2.contourArea(c) > min_area]
    
    if not filtered:
        return None
    return max(filtered, key=cv2.contourArea)


# ============ МАТЧИНГ ============

def preprocess_for_matching(image):
    """Предобработка изображения для матчинга"""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return blurred


