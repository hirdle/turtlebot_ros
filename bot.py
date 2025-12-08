#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import math
import tf
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan, Imu, Image
from nav_msgs.msg import Odometry

import sys

import cv2
import numpy as np
from cv_bridge import CvBridge, CvBridgeError


class BotController:
    """Универсальный класс для управления TurtleBot3 Waffle Pi"""
    
    def __init__(self, node_name='bot_controller', init_node=True):
        if init_node:
            rospy.init_node(node_name, anonymous=True)
        
        # Публикация команд движения
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        
        # Данные сенсоров
        self.scan_data = None
        self.imu_data = None
        self.odom_data = None
        
        # Начальная позиция для сброса одометрии
        self.start_x = 0.0
        self.start_y = 0.0
        self.start_yaw = 0.0
        
        # Подписки на топики
        rospy.Subscriber('/scan', LaserScan, self._scan_callback)
        rospy.Subscriber('/imu', Imu, self._imu_callback)
        rospy.Subscriber('/odom', Odometry, self._odom_callback)

        self.bridge = CvBridge()
        self.current_frame = None
        
        rospy.Subscriber('/front_camera/image_raw', Image, self._image_callback)
        
        self.rate = rospy.Rate(10)
        
        rospy.on_shutdown(self._shutdown_callback)

    
    def _shutdown_callback(self):
        """Вызывается при завершении программы (Ctrl+C)"""
        rospy.loginfo("Shutting down, stopping robot...")
        self.stop()

    
    def wait_for_hardware(self, timeout=10.0):
        """Ожидание инициализации всего оборудования"""
        rospy.loginfo("Waiting for hardware initialization...")
        start_time = rospy.Time.now()
        
        while not rospy.is_shutdown():
            elapsed = (rospy.Time.now() - start_time).to_sec()
            if elapsed > timeout:
                rospy.logwarn("Hardware initialization timeout (%.1f sec)" % timeout)
                return False
            
            # Проверка всех сенсоров
            scan_ok = self.scan_data is not None
            imu_ok = self.imu_data is not None
            odom_ok = self.odom_data is not None
            camera_ok = self.current_frame is not None
            
            if scan_ok and imu_ok and odom_ok and camera_ok:
                rospy.loginfo("All hardware initialized (scan=%s, imu=%s, odom=%s, camera=%s)" 
                             % (scan_ok, imu_ok, odom_ok, camera_ok))
                return True
            
            rospy.sleep(0.1)
        
        return False

    
    def wait(self, sec):
        rospy.sleep(sec)
    
    # ==================== CALLBACKS ====================
    
    def _scan_callback(self, msg):
        self.scan_data = msg
    
    def _imu_callback(self, msg):
        self.imu_data = msg
    
    def _odom_callback(self, msg):
        self.odom_data = msg

    def _image_callback(self, msg):
        try:
            self.current_frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except CvBridgeError as e:
            rospy.logerr("CvBridge Error: %s" % e)

    def get_image(self):
        if self.current_frame is None:
            return None
        return self.current_frame.copy()
    
    # ==================== MOVEMENT ====================
    
    def stop(self):
        """Остановка робота"""
        twist = Twist()
        self.cmd_vel_pub.publish(twist)
    

    def move_forward(self, distance, speed=0.08):
        """Движение вперед на заданное расстояние (м)"""
        self._move_linear(distance, abs(speed))
    

    def move_backward(self, distance, speed=0.08):
        """Движение назад на заданное расстояние (м)"""
        self._move_linear(distance, -abs(speed))
    

    def _move_linear(self, distance, speed):
        """Линейное движение по одометрии"""
        if not self.odom_data:
            rospy.logwarn("No odometry data")
            return False
        
        start_x = self.odom_data.pose.pose.position.x
        start_y = self.odom_data.pose.pose.position.y
        
        twist = Twist()
        twist.linear.x = speed
        
        while not rospy.is_shutdown():
            current_x = self.odom_data.pose.pose.position.x
            current_y = self.odom_data.pose.pose.position.y
            traveled = math.sqrt((current_x - start_x)**2 + (current_y - start_y)**2)
            
            if traveled >= distance:
                break
            
            self.cmd_vel_pub.publish(twist)
            self.rate.sleep()
        
        self.stop()
        return True
    

    def turn(self, angle_deg, speed=0.2):
        """
        Поворот на заданный угол (градусы)
        Положительный угол - против часовой (влево)
        Отрицательный угол - по часовой (вправо)
        """
        if not self.odom_data:
            rospy.logwarn("No odometry data")
            return False
        
        angle_rad = math.radians(angle_deg)
        start_yaw = self.get_yaw()
        target_yaw = self._normalize_angle(start_yaw + angle_rad)
        
        twist = Twist()
        twist.angular.z = abs(speed) if angle_rad > 0 else -abs(speed)
        
        while not rospy.is_shutdown():
            current_yaw = self.get_yaw()
            diff = self._normalize_angle(target_yaw - current_yaw)
            
            if abs(diff) < math.radians(2):  # точность 2 градуса
                break
            
            self.cmd_vel_pub.publish(twist)
            self.rate.sleep()
        
        self.stop()
        return True
    
    
    def turn_left(self, angle_deg, speed=0.2):
        """Поворот влево на угол (градусы)"""
        return self.turn(abs(angle_deg), speed)
    

    def turn_right(self, angle_deg, speed=0.2):
        """Поворот вправо на угол (градусы)"""
        return self.turn(-abs(angle_deg), speed)
    

    def move_speed(self, left_speed, right_speed, wheel_base=0.287):
        """
        Движение с заданными скоростями для каждого мотора (м/с)
        left_speed: скорость левого мотора (+ вперед, - назад)
        right_speed: скорость правого мотора (+ вперед, - назад)
        wheel_base: расстояние между колесами (м), для TurtleBot3 Waffle Pi = 0.287
        """
        linear = (right_speed + left_speed) / 2.0
        angular = (right_speed - left_speed) / wheel_base
        
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.cmd_vel_pub.publish(twist)
    

    def move_circle(self, radius, speed=0.1, clockwise=False):
        """
        Движение по окружности заданного радиуса (непрерывно)
        radius: радиус окружности (м)
        speed: линейная скорость (м/с)
        clockwise: True - по часовой, False - против часовой
        """
        angular = speed / radius
        if clockwise:
            angular = -angular
        
        twist = Twist()
        twist.linear.x = speed
        twist.angular.z = angular
        self.cmd_vel_pub.publish(twist)
    

    def move_circle_arc(self, radius, angle_deg, speed=0.1, clockwise=False):
        """
        Движение по дуге окружности на заданный угол
        radius: радиус окружности (м)
        angle_deg: угол дуги (градусы)
        speed: линейная скорость (м/с)
        clockwise: True - по часовой, False - против часовой
        """
        arc_length = radius * math.radians(abs(angle_deg))
        angular = speed / radius
        if clockwise:
            angular = -angular
        
        
        start_x = self.odom_data.pose.pose.position.x
        start_y = self.odom_data.pose.pose.position.y
        
        twist = Twist()
        twist.linear.x = speed
        twist.angular.z = angular
        
        while not rospy.is_shutdown():
            current_x = self.odom_data.pose.pose.position.x
            current_y = self.odom_data.pose.pose.position.y
            traveled = math.sqrt((current_x - start_x)**2 + (current_y - start_y)**2)
            
            if traveled >= arc_length * 0.9:
                break
            
            self.cmd_vel_pub.publish(twist)
            self.rate.sleep()
        
        self.stop()
        return True


    def move_by_condition(self, linear_speed, angular_speed, condition_func):
        """
        Движение с заданными скоростями до выполнения условия
        linear_speed: линейная скорость (м/с)
        angular_speed: угловая скорость (рад/с)
        condition_func: функция, возвращающая True для остановки
        """
        twist = Twist()
        twist.linear.x = linear_speed
        twist.angular.z = angular_speed
        
        while not rospy.is_shutdown():
            if condition_func():
                break
            self.cmd_vel_pub.publish(twist)
            self.rate.sleep()
        
        self.stop()
    

    def move_motors_by_condition(self, left_speed, right_speed, condition_func):
        """
        Движение с заданными скоростями до выполнения условия
        linear_speed: линейная скорость (м/с)
        angular_speed: угловая скорость (рад/с)
        condition_func: функция, возвращающая True для остановки
        """

        while not rospy.is_shutdown():
            if condition_func():
                break
            self.move_speed(left_speed, right_speed)
            self.rate.sleep()
        
        self.stop()

    # ==================== LIDAR ====================
    
    def get_scan_ranges(self):
        """Получить весь массив расстояний с лидара (360 значений)"""
        if not self.scan_data:
            return []
        return list(self.scan_data.ranges)
    
    
    def get_distance_at_angle(self, angle_deg):
        """
        Получить расстояние под заданным углом (градусы)
        0 - спереди, 90 - слева, -90/270 - справа, 180 - сзади
        """
        if not self.scan_data:
            return float('inf')
        
        angle_deg = angle_deg % 360
        num_readings = len(self.scan_data.ranges)
        angle_increment = math.degrees(self.scan_data.angle_increment)
        
        index = int(angle_deg / angle_increment) % num_readings
        distance = self.scan_data.ranges[index]
        
        if math.isinf(distance) or math.isnan(distance):
            return float('inf')
        return distance
    

    def get_distance_front(self):
        """Расстояние спереди (0 градусов)"""
        return self._get_averaged_distance(0, 10)
    

    def get_distance_left(self):
        """Расстояние слева (90 градусов)"""
        return self._get_averaged_distance(90, 10)
    

    def get_distance_right(self):
        """Расстояние справа (270 градусов)"""
        return self._get_averaged_distance(270, 10)
    

    def get_distance_back(self):
        """Расстояние сзади (180 градусов)"""
        return self._get_averaged_distance(180, 10)
    

    def get_min_distance(self):
        """Минимальное расстояние до препятствия"""
        if not self.scan_data:
            return float('inf')
        
        valid_ranges = [r for r in self.scan_data.ranges 
                       if not math.isinf(r) and not math.isnan(r) and r > 0]
        
        if valid_ranges:
            return min(valid_ranges)
        return float('inf')
    

    def get_object_angle_distance(self):
        """
        Определение угла и расстояния до ближайшего объекта
        Возвращает: (angle_deg, distance) - угол в градусах и расстояние в метрах
        angle_deg: 0 - спереди, 90 - слева, -90/270 - справа, 180 - сзади
        """
        if not self.scan_data:
            return (None, float('inf'))
        
        ranges = self.scan_data.ranges
        min_distance = float('inf')
        min_index = 0
        
        for i, r in enumerate(ranges):
            if not math.isinf(r) and not math.isnan(r) and r > 0:
                if r < min_distance:
                    min_distance = r
                    min_index = i
        
        if min_distance == float('inf'):
            return (None, float('inf'))
        
        angle_increment = math.degrees(self.scan_data.angle_increment)
        angle_deg = min_index * angle_increment
        
        # Нормализация угла: 0-180 слева, 180-360 -> -180 до 0 справа
        if angle_deg > 180:
            angle_deg = angle_deg - 360
        
        return (angle_deg, min_distance)
    

    def get_object_position(self):
        """
        Получить позицию ближайшего объекта в глобальных координатах
        Возвращает: (x, y, distance, angle_deg) или (None, None, None, None) если объект не найден
        """
        angle_deg, distance = self.get_object_angle_distance()
        
        if angle_deg is None:
            return (None, None, None, None)
        
        # Позиция робота
        robot_x, robot_y = self.get_position()
        robot_yaw = self.get_yaw()
        
        # Угол объекта в глобальной системе координат
        object_angle_global = robot_yaw + math.radians(angle_deg)
        
        # Позиция объекта
        object_x = robot_x + distance * math.cos(object_angle_global)
        object_y = robot_y + distance * math.sin(object_angle_global)
        
        return (object_x, object_y, distance, angle_deg)
    

    def get_object_width(self, distance_threshold=0.3):
        """
        Определение ширины ближайшего объекта
        distance_threshold: порог разницы расстояний для определения границ объекта (м)
        Возвращает: (width, angle_start, angle_end, distance) или (None, None, None, None)
        width - ширина объекта в метрах
        """
        if not self.scan_data:
            return (None, None, None, None)
        
        ranges = list(self.scan_data.ranges)
        angle_increment = math.degrees(self.scan_data.angle_increment)
        
        # Найти индекс ближайшего объекта
        min_distance = float('inf')
        min_index = 0
        for i, r in enumerate(ranges):
            if not math.isinf(r) and not math.isnan(r) and r > 0:
                if r < min_distance:
                    min_distance = r
                    min_index = i
        
        if min_distance == float('inf'):
            return (None, None, None, None)
        
        # Найти границы объекта (где расстояние резко увеличивается)
        num_readings = len(ranges)
        
        # Поиск левой границы
        left_index = min_index
        for i in range(1, num_readings // 2):
            idx = (min_index + i) % num_readings
            r = ranges[idx]
            if math.isinf(r) or math.isnan(r) or r <= 0:
                break
            if r - min_distance > distance_threshold:
                break
            left_index = idx
        
        # Поиск правой границы
        right_index = min_index
        for i in range(1, num_readings // 2):
            idx = (min_index - i) % num_readings
            r = ranges[idx]
            if math.isinf(r) or math.isnan(r) or r <= 0:
                break
            if r - min_distance > distance_threshold:
                break
            right_index = idx
        
        # Вычисление угловой ширины
        if left_index >= right_index:
            angle_span = (left_index - right_index) * angle_increment
        else:
            angle_span = (num_readings - right_index + left_index) * angle_increment
        
        # Вычисление ширины объекта (хорда)
        angle_span_rad = math.radians(angle_span)
        width = 2 * min_distance * math.sin(angle_span_rad / 2)
        
        # Углы границ
        angle_start = right_index * angle_increment
        angle_end = left_index * angle_increment
        if angle_start > 180:
            angle_start -= 360
        if angle_end > 180:
            angle_end -= 360
        
        return (width, angle_start, angle_end, min_distance)
    

    # ==================== IMU / ODOMETRY ====================
    
    def get_yaw(self):
        """Получить текущий угол поворота (yaw) в радианах"""
        if not self.odom_data:
            return 0.0
        
        orientation = self.odom_data.pose.pose.orientation
        quaternion = (orientation.x, orientation.y, orientation.z, orientation.w)
        euler = tf.transformations.euler_from_quaternion(quaternion)
        return euler[2]  # yaw
    

    def get_yaw_degrees(self):
        """Получить текущий угол поворота в градусах"""
        return math.degrees(self.get_yaw())
    

    def get_position(self):
        """Получить текущую позицию (x, y) относительно начальной точки"""
        if not self.odom_data:
            return (0.0, 0.0)
        
        x = self.odom_data.pose.pose.position.x - self.start_x
        y = self.odom_data.pose.pose.position.y - self.start_y
        return (x, y)
    
    # ==================== UTILITIES ====================
    
    def _normalize_angle(self, angle):
        """Нормализация угла в диапазон [-pi, pi]"""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle
    

# Пример использования
if __name__ == '__main__':
    try:
        bot = BotController()
        rospy.loginfo("BotController initialized")
        if not bot.wait_for_hardware():
            sys.exit(0)
        
        rospy.loginfo("All sensors ready")
        
            
    except rospy.ROSInterruptException:
        pass
