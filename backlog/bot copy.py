#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import math
import tf
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan, Imu, Image
from nav_msgs.msg import Odometry

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
    
    # ==================== SENSOR WAITING ====================
    
    def wait_for_sensors(self, timeout=5.0):
        """Ожидание готовности всех сенсоров"""
        start_time = rospy.Time.now()
        while not rospy.is_shutdown():
            if self.scan_data and self.imu_data and self.odom_data:
                return True
            if (rospy.Time.now() - start_time).to_sec() > timeout:
                rospy.logwarn("Timeout waiting for sensors")
                return False
            self.rate.sleep()
        return False
    
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
    
    def turn(self, angle_deg, speed=0.5):
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
    
    def get_scan_data(self):
        """Получить полные данные сканирования (ranges, angle_min, angle_max, angle_increment)"""
        if not self.scan_data:
            return None
        return {
            'ranges': list(self.scan_data.ranges),
            'angle_min': self.scan_data.angle_min,
            'angle_max': self.scan_data.angle_max,
            'angle_increment': self.scan_data.angle_increment,
            'range_min': self.scan_data.range_min,
            'range_max': self.scan_data.range_max
        }
    
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
    
    def get_absolute_position(self):
        """Получить абсолютную позицию (x, y) по одометрии"""
        if not self.odom_data:
            return (0.0, 0.0)
        
        x = self.odom_data.pose.pose.position.x
        y = self.odom_data.pose.pose.position.y
        return (x, y)
    
    def reset_odom(self):
        """Сброс начальной позиции (текущая станет нулевой)"""
        if self.odom_data:
            self.start_x = self.odom_data.pose.pose.position.x
            self.start_y = self.odom_data.pose.pose.position.y
            self.start_yaw = self.get_yaw()
    
    def get_imu_angular_velocity(self):
        """Получить угловую скорость из IMU"""
        if not self.imu_data:
            return (0.0, 0.0, 0.0)
        
        return (self.imu_data.angular_velocity.x,
                self.imu_data.angular_velocity.y,
                self.imu_data.angular_velocity.z)
    
    def get_imu_linear_acceleration(self):
        """Получить линейное ускорение из IMU"""
        if not self.imu_data:
            return (0.0, 0.0, 0.0)
        
        return (self.imu_data.linear_acceleration.x,
                self.imu_data.linear_acceleration.y,
                self.imu_data.linear_acceleration.z)
    
    # ==================== UTILITIES ====================
    
    def _normalize_angle(self, angle):
        """Нормализация угла в диапазон [-pi, pi]"""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle
    
    def distance_to_point(self, x, y):
        """Расстояние до точки от текущей позиции"""
        pos = self.get_position()
        return math.sqrt((x - pos[0])**2 + (y - pos[1])**2)
    
    def angle_to_point(self, x, y):
        """Угол до точки от текущей позиции (градусы)"""
        pos = self.get_position()
        return math.degrees(math.atan2(y - pos[1], x - pos[0]))


# Пример использования
if __name__ == '__main__':
    try:
        bot = BotController()
        rospy.loginfo("BotController initialized")
        
        if bot.wait_for_sensors():
            # rospy.loginfo("All sensors ready")
            # while True:
            
                # Пример: получение расстояний
                # rospy.loginfo("Front: %.2f m" % bot.get_distance_front())
                # rospy.loginfo("Left: %.2f m" % bot.get_distance_left())
                # rospy.loginfo("Right: %.2f m" % bot.get_distance_right())
                # bot.rate.sleep()
                # bot.wait(0.5)
            
            # Пример: движение
            bot.move_forward(0.05, 0.05)  # 50 см вперед
            # bot.turn_right(90)            # поворот на 90 градусов влево
            
    except rospy.ROSInterruptException:
        pass
