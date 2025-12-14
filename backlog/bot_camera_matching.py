#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bot_camera_matching.py - Матчинг шаблонов в реальном времени с ROS камеры TurtleBot3

Управление:
  q - выход
  1,2,3,4 - принудительно выбрать цвет (blue, red, green, yellow)
  0 - вернуться к auto режиму
"""

import rospy
import cv2
import numpy as np
import os
import glob
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError

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
        rospy.logwarn(f"Шаблоны не найдены в {folder_path}")
        return []
    
    rospy.loginfo(f"Найдено {len(paths)} шаблонов:")
    for p in paths:
        rospy.loginfo(f"  - {os.path.basename(p)}")
    
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


class BotCameraMatching:
    """Класс для матчинга шаблонов с ROS камеры TurtleBot3"""
    
    def __init__(self, template_folder='template', color='auto', threshold=0.7, 
                 camera_topic='/front_camera/image_raw', node_name='bot_camera_matching'):
        rospy.init_node(node_name, anonymous=True)
        
        self.bridge = CvBridge()
        self.current_frame = None
        self.color = color
        self.threshold = threshold
        self.padding = 20
        
        self.templates = load_templates_from_folder(template_folder, color, self.padding)
        
        rospy.Subscriber(camera_topic, Image, self._image_callback)
        self.rate = rospy.Rate(30)
        
        self.color_keys = {
            ord('0'): 'auto',
            ord('1'): 'blue',
            ord('2'): 'red',
            ord('3'): 'green',
            ord('4'): 'yellow'
        }
    
    def _image_callback(self, msg):
        try:
            self.current_frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except CvBridgeError as e:
            rospy.logerr(f"CvBridge Error: {e}")
    
    def wait_for_camera(self, timeout=5.0):
        """Ожидание готовности камеры"""
        start_time = rospy.Time.now()
        while not rospy.is_shutdown():
            if self.current_frame is not None:
                return True
            if (rospy.Time.now() - start_time).to_sec() > timeout:
                rospy.logwarn("Timeout waiting for camera")
                return False
            self.rate.sleep()
        return False
    
    def get_match_result(self):
        """
        Получить результат матчинга для текущего кадра.
        Returns: (is_match, confidence, template_name, detected_color) или None
        """
        if self.current_frame is None:
            return None
        
        _, is_match, confidence, best_name, detected_color = process_frame(
            self.current_frame.copy(), self.templates, self.color, self.threshold, self.padding
        )
        return (is_match, confidence, best_name, detected_color)
    
    def run(self):
        """Запустить визуализацию матчинга в реальном времени"""
        rospy.loginfo("Запуск матчинга с ROS камеры...")
        rospy.loginfo(f"Цвет детекции: {self.color}")
        rospy.loginfo(f"Порог матчинга: {self.threshold}")
        rospy.loginfo("Управление: q=выход, 0=auto, 1=blue, 2=red, 3=green, 4=yellow")
        
        if not self.wait_for_camera():
            rospy.logerr("Камера не готова")
            return
        
        rospy.loginfo("Камера готова")
        
        while not rospy.is_shutdown():
            if self.current_frame is None:
                self.rate.sleep()
                continue
            
            result_frame, is_match, confidence, best_name, detected_color = process_frame(
                self.current_frame.copy(), self.templates, self.color, self.threshold, self.padding
            )
            
            cv2.putText(result_frame, f"Color: {self.color} -> {detected_color}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            if is_match:
                status = f"Detected: {best_name} ({confidence:.2f})"
                cv2.putText(result_frame, status, (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            cv2.imshow('ROS Camera Matching', result_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key in self.color_keys:
                self.color = self.color_keys[key]
                rospy.loginfo(f"Color mode: {self.color}")
            
            self.rate.sleep()
        
        cv2.destroyAllWindows()
        rospy.loginfo("Завершено")


if __name__ == '__main__':
    try:
        matcher = BotCameraMatching(
            template_folder='template',
            color='auto',
            threshold=0.45,
            camera_topic='/front_camera/image_raw'
        )
        matcher.run()
    except rospy.ROSInterruptException:
        pass
