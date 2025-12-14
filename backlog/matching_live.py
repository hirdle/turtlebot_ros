#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
matching_live.py - Матчинг шаблонов в реальном времени с видео потока

Управление:
  q - выход
  1,2,3,4 - принудительно выбрать цвет (blue, red, green, yellow)
  0 - вернуться к auto режиму
"""

import cv2
import numpy as np
import os
import glob
from main_matching import (
    load_templates,
    detect_dominant_color,
    detect_blue, detect_red, detect_green, detect_yellow,
    find_largest_contour,
    get_bounding_box,
    extract_roi,
    match_templates
)


def load_templates_from_folder(folder_path, color='auto', padding=20):
    """Загрузить все изображения из папки как шаблоны"""
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
    paths = []
    for ext in extensions:
        paths.extend(glob.glob(os.path.join(folder_path, ext)))
    
    if not paths:
        print(f"Предупреждение: шаблоны не найдены в {folder_path}")
        return []
    
    print(f"Найдено {len(paths)} шаблонов:")
    for p in paths:
        print(f"  - {os.path.basename(p)}")
    
    return load_templates(paths, color, padding)


def draw_detection(frame, contour, bbox, is_match, confidence, template_name=None):
    """Нарисовать результат детекции на кадре"""
    color = (0, 255, 0) if is_match else (0, 0, 255)
    
    if contour is not None:
        cv2.drawContours(frame, [contour], -1, color, 2)
    
    if bbox is not None:
        x_min, y_min, x_max, y_max = bbox
        cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, 2)
        
        text = f"{'MATCH' if is_match else 'NO MATCH'}: {confidence:.2f}"
        cv2.putText(frame, text, (x_min, y_min - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        if template_name and is_match:
            cv2.putText(frame, template_name, (x_min, y_max + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    return frame


def process_frame(frame, templates, color='auto', threshold=0.7, padding=20):
    """Обработать один кадр: детекция + матчинг."""
    color_detectors = {
        'blue': detect_blue,
        'red': detect_red,
        'green': detect_green,
        'yellow': detect_yellow
    }
    
    actual_color = color
    if color == 'auto':
        actual_color = detect_dominant_color(frame)
    
    detector = color_detectors.get(actual_color, detect_blue)
    mask = detector(frame)
    contour = find_largest_contour(mask)
    
    if contour is None:
        return frame, False, 0.0, None, actual_color
    
    bbox = get_bounding_box(contour, padding)
    roi = extract_roi(frame, bbox)
    
    if not templates:
        draw_detection(frame, contour, bbox, False, 0.0)
        return frame, False, 0.0, None, actual_color
    
    is_match, confidence, best_name = match_templates(roi, templates, threshold)
    draw_detection(frame, contour, bbox, is_match, confidence, best_name)
    
    return frame, is_match, confidence, best_name, actual_color


def run_live(camera_id=0, template_folder='template', color='auto', threshold=0.7):
    """
    Запустить матчинг в реальном времени.
    
    Args:
        camera_id: ID камеры (0 = встроенная)
        template_folder: папка с шаблонами
        color: цвет для детекции ('auto', 'blue', 'red', 'green', 'yellow')
        threshold: порог уверенности для матчинга
    """
    templates = load_templates_from_folder(template_folder, color)
    
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        print(f"Ошибка: не удалось открыть камеру {camera_id}")
        return
    
    print(f"\nЗапуск видео потока...")
    print(f"Цвет детекции: {color}")
    print(f"Порог матчинга: {threshold}")
    print("\nУправление: q=выход, 0=auto, 1=blue, 2=red, 3=green, 4=yellow")
    print("-" * 40)
    
    current_color = color
    color_keys = {'0': 'auto', '1': 'blue', '2': 'red', '3': 'green', '4': 'yellow'}
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Ошибка чтения кадра")
            break
        
        result_frame, is_match, confidence, best_name, detected_color = process_frame(
            frame.copy(), templates, current_color, threshold
        )
        
        cv2.putText(result_frame, f"Color: {current_color} -> {detected_color}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        if is_match:
            status = f"Detected: {best_name} ({confidence:.2f})"
            cv2.putText(result_frame, status, (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        cv2.imshow('Matching Live', result_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key != 255 and chr(key) in color_keys:
            current_color = color_keys[chr(key)]
            print(f"Color mode: {current_color}")
    
    cap.release()
    cv2.destroyAllWindows()
    print("Завершено")


if __name__ == '__main__':
    run_live(
        camera_id=0,
        template_folder='template',
        color='auto',
        threshold=0.45
    )
