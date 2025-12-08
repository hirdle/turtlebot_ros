#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест функции detect_aruco с видеопотоком камеры
Клавиши: 'q' - выход
"""

import cv2
from matching import detect_aruco


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Ошибка: не удалось открыть камеру")
        return

    print("Запущен тест detect_aruco. Нажмите 'q' для выхода.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        markers = detect_aruco(frame)

        for marker_id, corners, area in markers:
            pts = corners[0].astype(int)
            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
            cx, cy = pts.mean(axis=0).astype(int)
            cv2.putText(frame, f"ID:{marker_id} A:{int(area)}", (cx - 30, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        info = f"ArUco: {len(markers)}"
        cv2.putText(frame, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        cv2.imshow("ArUco Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
