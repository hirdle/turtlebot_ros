#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cv2
import numpy as np


# ============ ЗАГРУЗКА ============

def load_image(path):
    """Загрузить изображение"""
    image = cv2.imread(path)
    if image is None:
        raise FileNotFoundError(f"Не удалось загрузить: {path}")
    return image

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


# ============ КОНТУРЫ И ROI ============

def find_largest_contour(mask, min_area=100):
    """Найти самый большой контур. Возвращает контур или None"""

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filtered = [c for c in contours if cv2.contourArea(c) > min_area]
    
    if not filtered:
        return None
    return max(filtered, key=cv2.contourArea)

# ============ ВИЗУАЛИЗАЦИЯ ============

def save_result(image, path):
    """Сохранить изображение"""
    cv2.imwrite(path, image)


# ============ МАТЧИНГ ============

def preprocess_for_matching(image):
    """Предобработка изображения для матчинга"""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return blurred




# ============ ГЛАВНАЯ ФУНКЦИЯ ============

def detect_and_match(frame=None, image_path=None):
    """
    Главная функция: детекция объекта по цвету + матчинг с шаблонами.
    
    Оба изображения (камера и шаблоны) обрабатываются одинаково:
    детекция цвета -> контур -> bounding box -> перспективная трансформация
    
    Args:
        image_path: путь к изображению с камеры
        template_paths: список путей к шаблонам
        color: цвет для детекции ('blue', 'red', 'green', 'yellow', 'auto')
               'auto' автоматически определит доминирующий цвет
        threshold: порог уверенности для матчинга
        padding: отступ вокруг найденного объекта
        save_path: путь для сохранения результата (None = не сохранять)
    
    Returns:
        (is_match: bool, confidence: float, best_template: str or None)
    """
    if image_path:
        # Загружаем изображение
        image = load_image(image_path)
    else:
        image = frame
    
    
    # Детекция объекта
    color_detectors = {
        'blue': detect_blue,
        'red': detect_red,
        'green': detect_green,
        'yellow': detect_yellow
    }

    result_color_list = []

    for color, detector in color_detectors.items():
        mask = detector(image)
        contour = find_largest_contour(mask)
        if contour is not None:
            result_color_list.append((color, contour, cv2.contourArea(contour)))

    return result_color_list
                  

# ============ ПРИМЕР ИСПОЛЬЗОВАНИЯ ============

if __name__ == '__main__':
    print("=== Тест матчинга ===")
    
    try:
        detect_and_match(
            image='test1.png',
        )
        
    except FileNotFoundError as e:
        print(f"Ошибка: {e}")
