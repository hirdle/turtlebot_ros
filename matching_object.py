#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
main_matching.py - Простой модуль для детекции и матчинга знаков
"""

import cv2
import numpy as np
import os

from common_cv import (
    detect_blue,
    find_largest_contour,
    detect_dominant_color,
    preprocess_for_matching,
    color_detectors,
)


# ============ ЗАГРУЗКА ============

def load_templates(paths, color='auto', padding=20):
    """
    Загрузить и обработать шаблоны (детекция + извлечение ROI).
    color='auto' автоматически определит доминирующий цвет для каждого шаблона.
    Возвращает список (имя, roi_изображение)
    """
    templates = []
    for path in paths:
        image = cv2.imread(path)
        roi = extract_object_roi(image, color, padding)
        if roi is not None:
            name = os.path.basename(path)
            templates.append((name, roi))
    return templates



# ============ КОНТУРЫ И ROI ============

def get_bounding_box(contour, padding=20):
    """Получить bounding box контура с отступом. Возвращает (x_min, y_min, x_max, y_max)"""
    points = contour.reshape(-1, 2)
    x_min = points[:, 0].min() - padding
    x_max = points[:, 0].max() + padding
    y_min = points[:, 1].min() - padding
    y_max = points[:, 1].max() + padding
    return (int(x_min), int(y_min), int(x_max), int(y_max))


def extract_roi(image, bbox, output_size=300):
    """Вырезать ROI с перспективной трансформацией"""
    x_min, y_min, x_max, y_max = bbox
    
    pts1 = np.float32([
        [x_min, y_min],
        [x_max, y_min],
        [x_min, y_max],
        [x_max, y_max]
    ])
    pts2 = np.float32([
        [0, 0],
        [output_size, 0],
        [0, output_size],
        [output_size, output_size]
    ])
    
    M = cv2.getPerspectiveTransform(pts1, pts2)
    roi = cv2.warpPerspective(image, M, (output_size, output_size))
    return roi


def extract_object_roi(image, color='auto', padding=20, output_size=300):
    """
    Найти объект по цвету и извлечь его ROI.
    color='auto' автоматически определит доминирующий цвет.
    Возвращает ROI или None если объект не найден.
    """
    
    if color == 'auto':
        color = detect_dominant_color(image)
    
    detector = color_detectors.get(color, detect_blue)
    mask = detector(image)
    
    contour = find_largest_contour(mask)
    if contour is None:
        return None
    
    bbox = get_bounding_box(contour, padding)
    roi = extract_roi(image, bbox, output_size)
    return roi


# ============ ВИЗУАЛИЗАЦИЯ ============

def draw_result(image, contour, bbox, is_match, confidence, template_name=None):
    """Нарисовать результат на изображении"""
    result = image.copy()
    
    # Цвет: зеленый если совпало, красный если нет
    color = (0, 255, 0) if is_match else (0, 0, 255)
    
    # Рисуем контур
    if contour is not None:
        cv2.drawContours(result, [contour], -1, color, 2)
    
    # Рисуем bounding box
    if bbox is not None:
        x_min, y_min, x_max, y_max = bbox
        cv2.rectangle(result, (x_min, y_min), (x_max, y_max), color, 2)
        
        # Текст с результатом
        text = f"{'MATCH' if is_match else 'NO MATCH'}: {confidence:.2f}"
        cv2.putText(result, text, (x_min, y_min - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        if template_name and is_match:
            cv2.putText(result, template_name, (x_min, y_max + 25), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    return result


# ============ МАТЧИНГ ============


def match_single(roi, template):
    """
    Сравнить ROI с одним шаблоном.
    Возвращает уверенность (0.0 - 1.0)
    """
    roi_proc = preprocess_for_matching(roi)
    template_proc = preprocess_for_matching(template)
    
    # Приводим шаблон к размеру ROI
    template_resized = cv2.resize(template_proc, (roi_proc.shape[1], roi_proc.shape[0]))
    
    result = cv2.matchTemplate(roi_proc, template_resized, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    
    return float(max_val)


def match_templates(roi, templates, threshold=0.7):
    """
    Сравнить ROI со списком шаблонов.
    templates: список (имя, изображение)
    
    Возвращает: (is_match, confidence, best_template_name)
    """
    best_confidence = 0.0
    best_name = None
    
    for name, template in templates:
        confidence = match_single(roi, template)
        if confidence > best_confidence:
            best_confidence = confidence
            best_name = name
    
    is_match = best_confidence >= threshold
    return (is_match, best_confidence, best_name)


# ============ ГЛАВНАЯ ФУНКЦИЯ ============

def detect_and_match(frame, template_paths, color='auto', threshold=0.7, padding=20, save_path=None):
    """
    Главная функция: детекция объекта по цвету + матчинг с шаблонами.
    
    Оба изображения (камера и шаблоны) обрабатываются одинаково:
    детекция цвета -> контур -> bounding box -> перспективная трансформация
    
    Args:
        frame: изображение с камеры
        template_paths: список путей к шаблонам
        color: цвет для детекции ('blue', 'red', 'green', 'yellow', 'auto')
               'auto' автоматически определит доминирующий цвет
        threshold: порог уверенности для матчинга
        padding: отступ вокруг найденного объекта
        save_path: путь для сохранения результата (None = не сохранять)
    
    Returns:
        (is_match: bool, confidence: float, best_template: str or None)
    """
    
    # Автоопределение цвета если нужно
    actual_color = color
    if color == 'auto':
        actual_color = detect_dominant_color(frame)
    
    detector = color_detectors.get(actual_color, detect_blue)
    mask = detector(frame)
    contour = find_largest_contour(mask)
    
    if contour is None:
        return (False, 0.0, None, frame)
    
    bbox = get_bounding_box(contour, padding)
    roi = extract_roi(frame, bbox)
    
    # Загружаем и обрабатываем шаблоны (тот же алгоритм)
    templates = load_templates(template_paths, color, padding)
    
    # Матчинг
    is_match, confidence, best_name = match_templates(roi, templates, threshold)
    
    # Сохраняем результат если указан путь
    if save_path:
        result_img = draw_result(frame, contour, bbox, is_match, confidence, best_name)
        cv2.imwrite(result_img, save_path)
    
    return (is_match, confidence, best_name, draw_result(frame, contour, bbox, is_match, confidence, best_name))


# ============ ПРИМЕР ИСПОЛЬЗОВАНИЯ ============

"""
result, confidence, best = detect_and_match(
    image_path='tesing.png',
    template_paths=[
        'template/forward.png',
        'template/backward.png',
        'template/left.png',
        'template/right.png',
        'template/stop.png'
    ],
    color='auto',  # автоопределение цвета
    threshold=0.45,
    save_path='result.jpg'  # сохранить результат
)
print(f"Результат: {result}")
print(f"Уверенность: {confidence:.2f}")
print(f"Лучший шаблон: {best}")
print("Результат сохранен в result.jpg")
"""
