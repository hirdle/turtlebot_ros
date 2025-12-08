#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ArUco Live View - просмотр распознавания ArUco маркеров в реальном времени
"""

import sys
import os

# Добавляем родительскую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rospy
import cv2
from bot import BotController
import matching_aruco


def main():
    """Основная функция для live-просмотра ArUco маркеров"""
    
    try:
        # Инициализация робота
        rospy.loginfo("Инициализация BotController...")
        bot = BotController(node_name='aruco_live_view')
        
        # Ожидание инициализации оборудования
        rospy.loginfo("Ожидание инициализации камеры...")
        if not bot.wait_for_hardware(timeout=10.0):
            rospy.logerr("Не удалось инициализировать камеру")
            return
        
        rospy.loginfo("Камера готова! Начинаем распознавание ArUco маркеров...")
        rospy.loginfo("Нажмите 'q' для выхода, 'd' для смены словаря")
        
        # Список доступных словарей
        dict_types = ['DICT_4X4_50', 'DICT_5X5_100', 'DICT_6X6_1000', 'DICT_ARUCO_ORIGINAL']
        current_dict_index = 0
        current_dict = dict_types[current_dict_index]
        
        while not rospy.is_shutdown():
            # Получаем изображение с камеры
            frame = bot.get_image()
            
            if frame is None:
                rospy.logwarn("Не удалось получить изображение")
                bot.rate.sleep()
                continue
            
            # Детекция ArUco маркеров
            markers = matching_aruco.detect_and_match(frame, aruco_dict_type=current_dict)
            
            # Визуализация
            result_frame = matching_aruco.draw_markers(frame, markers)
            
            # Информация о найденных маркерах
            info_text = f"Словарь: {current_dict} | Найдено маркеров: {len(markers)}"
            cv2.putText(result_frame, info_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Вывод информации в консоль
            if markers:
                for marker_id, corners, center, area in markers:
                    rospy.loginfo(f"Маркер ID={marker_id}, центр={center}, площадь={int(area)}")
            
            # Показываем результат
            cv2.imshow('ArUco Live View', result_frame)
            
            # Обработка нажатий клавиш
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                rospy.loginfo("Выход...")
                break
            elif key == ord('d'):
                # Переключение словаря
                current_dict_index = (current_dict_index + 1) % len(dict_types)
                current_dict = dict_types[current_dict_index]
                rospy.loginfo(f"Переключено на словарь: {current_dict}")
            
            bot.rate.sleep()
        
    except rospy.ROSInterruptException:
        rospy.loginfo("Прервано пользователем")
    except Exception as e:
        rospy.logerr(f"Ошибка: {e}")
    finally:
        cv2.destroyAllWindows()
        rospy.loginfo("Завершение работы")


if __name__ == '__main__':
    main()
