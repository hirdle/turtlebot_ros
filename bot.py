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
    

    def set_velocity(self, linear=0.0, angular=0.0):
        """Установка произвольной скорости"""
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.cmd_vel_pub.publish(twist)
    

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
    

    def _get_averaged_distance(self, center_angle, spread):
        """Усредненное расстояние в секторе"""
        if not self.scan_data:
            return float('inf')

        center_angle = abs(center_angle + 180) - 360

        distances = []
        for angle in range(center_angle - spread, center_angle + spread + 1):
            d = self.get_distance_at_angle(angle)
            if not math.isinf(d):
                distances.append(d)
        
        if distances:
            return sum(distances) / len(distances)
        return float('inf')
    

    def get_min_distance(self):
        """Минимальное расстояние до препятствия"""
        if not self.scan_data:
            return float('inf')
        
        valid_ranges = [r for r in self.scan_data.ranges 
                       if not math.isinf(r) and not math.isnan(r) and r > 0]
        
        if valid_ranges:
            return min(valid_ranges)
        return float('inf')
    

    def get_min_distance_in_sector(self, start_angle, end_angle):
        """Минимальное расстояние в секторе (градусы)"""
        if not self.scan_data:
            return float('inf')
        
        min_dist = float('inf')
        angle = start_angle
        while angle <= end_angle:
            d = self.get_distance_at_angle(angle)
            if d < min_dist:
                min_dist = d
            angle += 1
        return min_dist
    

    # ==================== IMU / ODOMETRY ====================
    
    def get_yaw(self):
        """Получить текущий угол поворота (yaw) в радианах"""
        if not self.odom_data:
            return 0.0
        
        orientation = self.odom_data.pose.pose.orientation
        quaternion = (orientation.x, orientation.y, orientation.z, orientation.w)
        euler = tf.transformations.euler_from_quaternion(quaternion)
        return euler[2]  # yaw
    
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
