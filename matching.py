#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
matching.py - Упрощённый модуль для детекции ArUco, знаков и светофора
"""

import cv2
import numpy as np
import os

# === HSV ДИАПАЗОНЫ ЦВЕТОВ ===
COLORS = {
    'blue': ((100, 100, 100), (130, 255, 255)),
    'green': ((40, 30, 30), (80, 255, 255)),
    'yellow': ((20, 100, 100), (40, 255, 255)),
    'red': None,  # особый случай - два диапазона
}


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def _get_mask(img, color):
    """Получить маску по цвету"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    kernel = np.ones((5, 5), np.uint8)
    
    if color == 'red':
        m1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(m1, m2)
    else:
        low, high = COLORS.get(color, COLORS['blue'])
        mask = cv2.inRange(hsv, np.array(low), np.array(high))
    
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return mask


def _find_contour(mask, min_area=100):
    """Найти самый большой контур"""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) > min_area]
    return max(contours, key=cv2.contourArea) if contours else None


def _dominant_color(img):
    """Определить доминирующий цвет"""
    best, best_area = 'blue', 0
    for color in COLORS:
        area = cv2.countNonZero(_get_mask(img, color))
        if area > best_area:
            best, best_area = color, area
    return best


def _crop_roi(img, contour, pad=20, size=300):
    """Вырезать ROI вокруг контура"""
    pts = contour.reshape(-1, 2)
    x1, y1 = pts.min(axis=0) - pad
    x2, y2 = pts.max(axis=0) + pad
    
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    
    roi = img[int(y1):int(y2), int(x1):int(x2)]
    return cv2.resize(roi, (size, size)) if roi.size > 0 else None


# === ГЛАВНЫЕ ФУНКЦИИ ===

def detect_aruco(frame):
    """
    Детекция ArUco маркеров 7x7 с пониженной чувствительностью для низкого разрешения.
    
    Returns: [(marker_id, corners, area), ...]
    """
    if frame is None:
        return []
    
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_7X7_50)
    params = cv2.aruco.DetectorParameters()
    params.minMarkerPerimeterRate = 0.03  # поиграйсь с 0.02–0.05
    params.maxMarkerPerimeterRate = 100.0   # обычно ок

    detector = cv2.aruco.ArucoDetector(aruco_dict, params)
    corners, ids, _ = detector.detectMarkers(frame)
    
    result = []
    if ids is not None:
        for i, corner in enumerate(corners):
            area = cv2.contourArea(corner[0].astype(np.float32))
            result.append((ids[i][0], corner, area))
    return result


def detect_sign(frame, template_paths, color='auto', threshold=0.45):
    """
    Детекция и матчинг знака с шаблонами.
    
    Args:
        frame: изображение
        template_paths: список путей к шаблонам
        color: 'blue', 'red', 'green', 'yellow' или 'auto'
        threshold: порог совпадения (0.0-1.0)
    
    Returns: (is_match, confidence, template_name)
    """
    if frame is None:
        return (False, 0.0, None)
    
    if color == 'auto':
        color = _dominant_color(frame)
    
    mask = _get_mask(frame, color)
    contour = _find_contour(mask)
    if contour is None:
        return (False, 0.0, None)
    
    roi = _crop_roi(frame, contour)
    if roi is None:
        return (False, 0.0, None)
    
    roi_gray = cv2.GaussianBlur(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), (9, 9), 0)
    
    best_conf, best_name = 0.0, None
    for path in template_paths:
        tpl = cv2.imread(path)
        if tpl is None:
            continue
        
        # Обрабатываем шаблон так же
        tpl_mask = _get_mask(tpl, color)
        tpl_contour = _find_contour(tpl_mask)
        if tpl_contour is None:
            continue
        
        tpl_roi = _crop_roi(tpl, tpl_contour)
        if tpl_roi is None:
            continue
        
        tpl_gray = cv2.GaussianBlur(cv2.cvtColor(tpl_roi, cv2.COLOR_BGR2GRAY), (5, 5), 0)
        tpl_resized = cv2.resize(tpl_gray, (roi_gray.shape[1], roi_gray.shape[0]))
        
        result = cv2.matchTemplate(roi_gray, tpl_resized, cv2.TM_CCOEFF_NORMED)
        _, conf, _, _ = cv2.minMaxLoc(result)
        
        if conf > best_conf:
            best_conf, best_name = conf, os.path.basename(path)
    
    return (best_conf >= threshold, best_conf, best_name)


def detect_traffic_light(frame, min_area=5000):
    """
    Детекция цветов светофора.
    
    Returns: [(color, contour, area), ...] отсортировано по площади
    """
    if frame is None:
        return []
    
    result = []
    for color in COLORS:
        mask = _get_mask(frame, color)
        contour = _find_contour(mask, min_area=min_area)
        if contour is not None:
            result.append((color, contour, cv2.contourArea(contour)))
    
    return sorted(result, key=lambda x: x[2], reverse=True)
