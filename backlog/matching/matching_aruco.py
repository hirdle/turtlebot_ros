#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
matching_aruco.py - Простой модуль для детекции ArUco маркеров 7x7
"""

import cv2
import numpy as np


# ============ ВИЗУАЛИЗАЦИЯ ============

def draw_result(image, corners, ids):
    """Нарисовать найденные ArUco маркеры на изображении"""
    result = image.copy()
    
    if ids is not None:
        cv2.aruco.drawDetectedMarkers(result, corners, ids)
        
        for i, corner in enumerate(corners):
            pts = corner[0].astype(int)
            center = pts.mean(axis=0).astype(int)
            marker_id = ids[i][0]
            cv2.putText(result, f"ID: {marker_id}", (center[0], center[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    return result


# ============ ГЛАВНАЯ ФУНКЦИЯ ============

def detect_and_match(frame=None):
    """
    Детекция ArUco маркеров 7x7 на изображении.
    
    Args:
        frame: изображение для анализа
    
    Returns:
        список кортежей (marker_id, corners, area) для каждого найденного маркера
    """
    if frame is None:
        return []
    
    # ArUco 7x7 = DICT_7X7_50 (или _100, _250, _1000)
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_7X7_50)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    # Детекция
    corners, ids, rejected = detector.detectMarkers(frame)
    
    result_list = []
    
    if ids is not None:
        for i, corner in enumerate(corners):
            marker_id = ids[i][0]
            pts = corner[0]
            area = cv2.contourArea(pts.astype(np.float32))
            result_list.append((marker_id, corner, area))
    
    return result_list
