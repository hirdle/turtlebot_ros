#!/usr/bin/env python

import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError


class BotCameraController:
    """Класс для работы с камерой Raspberry Pi на TurtleBot3"""
    
    def __init__(self, node_name='bot_camera_controller', init_node=True):
        if init_node:
            rospy.init_node(node_name, anonymous=True)
        
        self.bridge = CvBridge()
        self.current_frame = None
        
        rospy.Subscriber('/front_camera/image_raw', Image, self._image_callback)
        
        self.rate = rospy.Rate(10)
    
    # ==================== CALLBACKS ====================
    
    def _image_callback(self, msg):
        try:
            self.current_frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except CvBridgeError as e:
            rospy.logerr("CvBridge Error: %s" % e)
    
    # ==================== WAITING ====================
    
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
    
    # ==================== IMAGE GETTERS ====================
    
    def get_image(self):
        """Получить текущий кадр (BGR формат)"""
        if self.current_frame is None:
            return None
        return self.current_frame.copy()
    
    def get_image_rgb(self):
        """Получить текущий кадр в RGB формате"""
        if self.current_frame is None:
            return None
        return cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
    
    def get_hsv_image(self):
        """Получить текущий кадр в HSV формате"""
        if self.current_frame is None:
            return None
        return cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2HSV)
    
    def get_gray_image(self):
        """Получить текущий кадр в градациях серого"""
        if self.current_frame is None:
            return None
        return cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2GRAY)
    
    def get_image_size(self):
        """Получить размер изображения (height, width)"""
        if self.current_frame is None:
            return (0, 0)
        return self.current_frame.shape[:2]
    
    # ==================== SAVING ====================
    
    def save_image(self, filename):
        """Сохранить текущий кадр в файл"""
        if self.current_frame is None:
            rospy.logwarn("No image to save")
            return False
        return cv2.imwrite(filename, self.current_frame)
    
    # ==================== COLOR DETECTION ====================
    
    def detect_color(self, color='auto'):
        """
        Универсальная детекция цвета.
        color: 'red', 'green', 'blue', 'yellow' или 'auto' для автоопределения
        Возвращает (mask, color_name) - маску и название определенного цвета
        """
        if self.current_frame is None:
            return None, None
        
        if color == 'auto':
            return self.detect_dominant_color()
        
        color_methods = {
            'red': self._detect_red,
            'green': self._detect_green,
            'blue': self._detect_blue,
            'yellow': self._detect_yellow
        }
        
        detector = color_methods.get(color, self._detect_blue)
        return detector(), color
    
    def detect_dominant_color(self):
        """
        Автоматически определить доминирующий цвет на изображении.
        Возвращает (mask, color_name)
        """
        if self.current_frame is None:
            return None, None
        
        color_detectors = {
            'blue': self._detect_blue,
            'red': self._detect_red,
            'green': self._detect_green,
            'yellow': self._detect_yellow
        }
        
        best_color = 'blue'
        best_area = 0
        best_mask = None
        
        for color_name, detector in color_detectors.items():
            mask = detector()
            if mask is not None:
                area = cv2.countNonZero(mask)
                if area > best_area:
                    best_area = area
                    best_color = color_name
                    best_mask = mask
        
        return best_mask, best_color
    
    def _detect_color_hsv(self, lower_hsv, upper_hsv):
        """Внутренний метод для детекции по HSV диапазону с морфологией"""
        if self.current_frame is None:
            return None
        
        hsv = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2HSV)
        lower = np.array(lower_hsv, dtype=np.uint8)
        upper = np.array(upper_hsv, dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        return mask
    
    def _detect_red(self):
        """Детекция красного цвета"""
        if self.current_frame is None:
            return None
        hsv = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(mask1, mask2)
        
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        return mask
    
    def _detect_green(self):
        """Детекция зеленого цвета"""
        return self._detect_color_hsv((40, 100, 100), (80, 255, 255))
    
    def _detect_blue(self):
        """Детекция синего цвета"""
        return self._detect_color_hsv((100, 100, 100), (130, 255, 255))
    
    def _detect_yellow(self):
        """Детекция желтого цвета"""
        return self._detect_color_hsv((20, 100, 100), (40, 255, 255))
    
    def detect_red(self):
        """Детекция красного цвета (обратная совместимость)"""
        return self._detect_red()
    
    def detect_green(self):
        """Детекция зеленого цвета (обратная совместимость)"""
        return self._detect_green()
    
    def detect_blue(self):
        """Детекция синего цвета (обратная совместимость)"""
        return self._detect_blue()
    
    def detect_yellow(self):
        """Детекция желтого цвета (обратная совместимость)"""
        return self._detect_yellow()
    
    # ==================== CONTOURS ====================
    
    def find_contours(self, mask):
        """Найти контуры на бинарной маске"""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return contours
    
    def find_largest_contour(self, mask):
        """Найти самый большой контур"""
        contours = self.find_contours(mask)
        if not contours:
            return None
        return max(contours, key=cv2.contourArea)
    
    def get_contour_center(self, contour):
        """Получить центр контура (cx, cy)"""
        if contour is None:
            return None
        M = cv2.moments(contour)
        if M["m00"] == 0:
            return None
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return (cx, cy)
    
    def get_contour_area(self, contour):
        """Получить площадь контура"""
        if contour is None:
            return 0
        return cv2.contourArea(contour)
    
    # ==================== TEMPLATE MATCHING ====================
    
    def match_template(self, template_paths, color='auto', threshold=0.7, padding=20):
        """
        Сопоставить текущий кадр с камеры с шаблонами (использует main_matching).
        
        Args:
            template_paths: список путей к шаблонам
            color: цвет для детекции ('auto', 'red', 'green', 'blue', 'yellow')
            threshold: порог уверенности (0.0 - 1.0)
            padding: отступ вокруг найденного объекта
        
        Returns:
            (is_match: bool, confidence: float, best_template: str or None)
        """
        if self.current_frame is None:
            return (False, 0.0, None)
        
        
        templates = main_matching.load_templates(template_paths, color, padding)
        return main_matching.detect_and_match_image(
            self.current_frame, templates, color, threshold, padding
        )


# Пример использования
if __name__ == '__main__':
    try:
        cam = BotCameraController()
        rospy.loginfo("BotCameraController initialized")
        
        if cam.wait_for_camera():
            rospy.loginfo("Camera ready")
            while True:
                image = cam.get_image()
                if image is not None:
                    cv2.imshow("Camera Frame", image)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                cam.rate.sleep()

            
            
    except rospy.ROSInterruptException:
        pass
