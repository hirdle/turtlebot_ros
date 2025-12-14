#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cv2
import numpy as np


# ============ СЛОВАРИ ArUco ============

ARUCO_DICT_MAP = {
    'DICT_4X4_50': cv2.aruco.DICT_4X4_50,
    'DICT_4X4_100': cv2.aruco.DICT_4X4_100,
    'DICT_4X4_250': cv2.aruco.DICT_4X4_250,
    'DICT_4X4_1000': cv2.aruco.DICT_4X4_1000,
    'DICT_5X5_50': cv2.aruco.DICT_5X5_50,
    'DICT_5X5_100': cv2.aruco.DICT_5X5_100,
    'DICT_5X5_250': cv2.aruco.DICT_5X5_250,
    'DICT_5X5_1000': cv2.aruco.DICT_5X5_1000,
    'DICT_6X6_50': cv2.aruco.DICT_6X6_50,
    'DICT_6X6_100': cv2.aruco.DICT_6X6_100,
    'DICT_6X6_250': cv2.aruco.DICT_6X6_250,
    'DICT_6X6_1000': cv2.aruco.DICT_6X6_1000,
    'DICT_7X7_50': cv2.aruco.DICT_7X7_50,
    'DICT_7X7_100': cv2.aruco.DICT_7X7_100,
    'DICT_7X7_250': cv2.aruco.DICT_7X7_250,
    'DICT_7X7_1000': cv2.aruco.DICT_7X7_1000,
    'DICT_ARUCO_ORIGINAL': cv2.aruco.DICT_ARUCO_ORIGINAL,
}


# ============ ГЛАВНАЯ ФУНКЦИЯ ============

def detect_and_match(frame, aruco_dict_type='DICT_4X4_50'):
    """
    Детекция ArUco маркеров на изображении
    
    Args:
        frame: изображение с камеры
        aruco_dict_type: тип словаря ArUco ('DICT_4X4_50', 'DICT_5X5_100', и т.д.)
    
    Returns:
        list: [(marker_id, corners, center, area), ...]
        - marker_id: ID маркера (int)
        - corners: углы маркера в формате [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        - center: центр маркера (x, y)
        - area: площадь маркера (float)
    """
    
    if frame is None:
        return []
    
    # Получаем словарь ArUco
    if aruco_dict_type not in ARUCO_DICT_MAP:
        aruco_dict_type = 'DICT_4X4_50'
    
    # Новый API для OpenCV 4.7.x+
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_MAP[aruco_dict_type])
    aruco_params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
    
    # Детекция маркеров
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, rejected = detector.detectMarkers(gray)
    
    result_list = []
    
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            marker_corners = corners[i][0]
            
            # Вычисляем центр маркера
            center_x = int(marker_corners[:, 0].mean())
            center_y = int(marker_corners[:, 1].mean())
            center = (center_x, center_y)
            
            # Вычисляем площадь маркера
            area = cv2.contourArea(marker_corners)
            
            # Преобразуем углы в удобный формат
            corners_list = marker_corners.tolist()
            
            result_list.append((int(marker_id), corners_list, center, float(area)))
    
    return result_list


# ============ ВИЗУАЛИЗАЦИЯ ============

def draw_markers(frame, detected_markers):
    """
    Отрисовка найденных маркеров на изображении
    
    Args:
        frame: изображение
        detected_markers: список маркеров от detect_and_match()
    
    Returns:
        изображение с нарисованными маркерами
    """
    
    if frame is None:
        return None
    
    result = frame.copy()
    
    for marker_id, corners, center, area in detected_markers:
        # Преобразуем углы в формат для OpenCV
        corners_array = np.array([corners], dtype=np.int32)
        
        # Рисуем границы маркера
        cv2.polylines(result, corners_array, True, (0, 255, 0), 2)
        
        # Рисуем центр
        cv2.circle(result, center, 4, (0, 0, 255), -1)
        
        # Рисуем ID маркера
        text_pos = (center[0] - 20, center[1] - 20)
        cv2.putText(result, f"ID: {marker_id}", text_pos, 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        # Рисуем площадь
        area_text_pos = (center[0] - 20, center[1] + 20)
        cv2.putText(result, f"Area: {int(area)}", area_text_pos, 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
    
    return result


# ============ ПРИМЕР ИСПОЛЬЗОВАНИЯ ============

"""
from bot import BotController
import matching_aruco

bot = BotController()
bot.wait_for_hardware()

frame = bot.get_image()
markers = matching_aruco.detect_and_match(frame)

for marker_id, corners, center, area in markers:
    print(f"Найден маркер ID={marker_id} в точке {center}, площадь={area}")

# Визуализация
result_frame = matching_aruco.draw_markers(frame, markers)
cv2.imshow('ArUco Detection', result_frame)
cv2.waitKey(0)
"""
