#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест функции detect_sign с видеопотоком камеры
Клавиши: 'q' - выход, '1'-'4' - выбор цвета (blue/red/green/yellow), 'a' - auto
"""

import cv2
import glob
import os
from matching import detect_sign

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "template")


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Ошибка: не удалось открыть камеру")
        return

    templates = glob.glob(os.path.join(TEMPLATE_DIR, "*.png"))
    templates += glob.glob(os.path.join(TEMPLATE_DIR, "*.jpg"))

    if not templates:
        print(f"Предупреждение: шаблоны не найдены в {TEMPLATE_DIR}")

    color_mode = 'auto'
    color_keys = {'1': 'blue', '2': 'red', '3': 'green', '4': 'yellow', 'a': 'auto'}

    print("Запущен тест detect_sign. Нажмите 'q' для выхода.")
    print(f"Найдено шаблонов: {len(templates)}")
    print("Клавиши: 1=blue, 2=red, 3=green, 4=yellow, a=auto")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        is_match, confidence, template_name = detect_sign(frame, templates, color=color_mode)

        status = f"Match: {template_name} ({confidence:.2f})" if is_match else f"No match ({confidence:.2f})"
        color = (0, 255, 0) if is_match else (0, 0, 255)

        cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, f"Color: {color_mode}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.imshow("Sign Test", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif chr(key) in color_keys:
            color_mode = color_keys[chr(key)]
            print(f"Режим цвета: {color_mode}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
