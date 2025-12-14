#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
aruco_camera.py - Распознавание ArUco маркеров с камеры в реальном времени
Тип маркеров: DataMatrix-подобные (DICT_APRILTAG_36h11)
"""

import cv2


def main():
    # Открываем камеру
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Ошибка: не удалось открыть камеру")
        return
    
    # ArUco словарь 7x7 (идентично matching_aruco.py)
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_7X7_50)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    print("Нажмите 'q' для выхода")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Детекция маркеров
        corners, ids, rejected = detector.detectMarkers(frame)
        
        # Отрисовка результатов
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
            
            for i, corner in enumerate(corners):
                pts = corner[0].astype(int)
                center = pts.mean(axis=0).astype(int)
                marker_id = ids[i][0]
                cv2.putText(frame, f"ID: {marker_id}", (center[0], center[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow("ArUco Detection", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
