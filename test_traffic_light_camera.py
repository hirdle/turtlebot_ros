#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест функции detect_traffic_light с видеопотоком камеры
Клавиши: 'q' - выход
"""

import cv2
from matching import detect_traffic_light

COLOR_BGR = {
    'red': (0, 0, 255),
    'green': (0, 255, 0),
    'yellow': (0, 255, 255),
    'blue': (255, 0, 0),
}


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Ошибка: не удалось открыть камеру")
        return

    print("Запущен тест detect_traffic_light. Нажмите 'q' для выхода.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        lights = detect_traffic_light(frame)

        for i, (color, contour, area) in enumerate(lights):
            bgr = COLOR_BGR.get(color, (255, 255, 255))
            cv2.drawContours(frame, [contour], -1, bgr, 2)
            x, y, w, h = cv2.boundingRect(contour)
            cv2.putText(frame, f"{color} ({int(area)})", (x, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, bgr, 2)

        dominant = lights[0][0] if lights else "none"
        cv2.putText(frame, f"Dominant: {dominant}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, COLOR_BGR.get(dominant, (255, 255, 255)), 2)
        cv2.putText(frame, f"Colors: {len(lights)}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow("Traffic Light Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
