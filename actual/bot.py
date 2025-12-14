#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import math
import tf
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan, Imu, Image
from nav_msgs.msg import Odometry
import cv2
import actionlib
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal


import actual.matching as matching

import sys

from cv_bridge import CvBridge


class BotController:
    """Универсальный класс для управления TurtleBot3 Waffle Pi"""
    
    def __init__(self, node_name='bot_controller'):
        rospy.init_node(node_name, anonymous=True)
        
        # Публикация команд движения
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

        self.wheel_base = 0.287
        
        # Данные сенсоров
        self.scan_data = None
        self.imu_data = None
        self.odom_data = None
        
        # Начальная позиция
        self.start_x = 0.0
        self.start_y = 0.0
        self.start_yaw = 0.0
        
        # Подписки на топики
        rospy.Subscriber('/scan', LaserScan, self._scan_callback)
        rospy.Subscriber('/imu', Imu, self._imu_callback)
        rospy.Subscriber('/odom', Odometry, self._odom_callback)

        self.client = actionlib.SimpleActionClient('move_base',MoveBaseAction)
        self.client.wait_for_server()

        self.bridge = CvBridge()
        self.current_frame = None
        
        rospy.Subscriber('/front_camera/image_raw', Image, self._image_callback)
        
        self.rate = rospy.Rate(100)
        
        rospy.on_shutdown(self.stop)

    
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
        except Exception as e:
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
        """
        
        angle_rad = math.radians(angle_deg)
        start_yaw = self.get_yaw()
        target_yaw = self._normalize_angle(start_yaw - angle_rad)
        
        twist = Twist()
        twist.angular.z = -abs(speed) if angle_rad > 0 else abs(speed)
        
        while not rospy.is_shutdown():
            current_yaw = self.get_yaw()
            diff = self._normalize_angle(current_yaw-target_yaw)
            
            if abs(diff) < math.radians(2):  # точность 2 градуса
                break
            
            self.cmd_vel_pub.publish(twist)
            self.rate.sleep()
        
        self.stop()
        return True
    
    
    def turn_left(self, angle_deg=90, speed=0.2):
        """Поворот влево на угол (градусы)"""
        return self.turn(-abs(angle_deg), speed)
    

    def turn_right(self, angle_deg=90, speed=0.2):
        """Поворот вправо на угол (градусы)"""
        return self.turn(abs(angle_deg), speed)
    

    def move_motors_speed(self, left_speed, right_speed):
        """
        Движение с /заданными скоростями для каждого мотора (м/с)
        """

        linear = (right_speed + left_speed) / 2.0
        angular = (right_speed - left_speed) / self.wheel_base
        
        twist = Twist()
        twist.linear.x = linear
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

        angular_speed = speed / radius
        linear_component = angular_speed * (self.wheel_base / 2.0)
        
        if clockwise:
            left_speed = speed + linear_component
            right_speed = speed - linear_component
        else:
            left_speed = speed - linear_component
            right_speed = speed + linear_component
        
        
        current_yaw = self.get_yaw()
        target_angle_rad = math.radians(abs(angle_deg))
        accumulated_angle = 0.0
        
        while not rospy.is_shutdown():
            # Интегрируем изменение угла
            previous_yaw = current_yaw
            current_yaw = self.get_yaw()
            delta = self._normalize_angle(current_yaw - previous_yaw)
            accumulated_angle += abs(delta)
            
            if accumulated_angle >= target_angle_rad:
                break
            
            self.move_motors_speed(left_speed, right_speed)
            self.rate.sleep()
        
        self.stop()
        return True


    def move_by_condition(self, linear_speed, angular_speed, condition_func):
        """
        Движение с заданными скоростями до выполнения условия
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
        """

        while not rospy.is_shutdown():
            if condition_func():
                break
            self.move_motors_speed(left_speed, right_speed)
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
        
        angle_deg = abs(-angle_deg + 180) - 360
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
    

    def get_sector_data(self, start_angle, end_angle):
        """
        Получить все данные лидара в секторе [start_angle, end_angle]
        """
        if not self.scan_data:
            return []
        
        num_readings = len(self.scan_data.ranges)
        angle_increment = math.degrees(self.scan_data.angle_increment)
        result = []
        
        # Нормализуем углы в диапазон [0, 360)
        start = start_angle % 360
        end = end_angle % 360
        
        for i in range(num_readings):
            # Преобразуем индекс в угол (обратное преобразование из get_distance_at_angle)
            raw_angle = i * angle_increment
            angle_deg = 360 - abs(raw_angle + 180)
            angle_deg = angle_deg % 360
            
            # Проверяем, попадает ли угол в сектор
            if start <= end:
                in_sector = start <= angle_deg <= end
            else:
                # Сектор пересекает 0 градусов
                in_sector = angle_deg >= start or angle_deg <= end
            
            if in_sector:
                distance = self.scan_data.ranges[i]
                if not math.isinf(distance) and not math.isnan(distance):
                    result.append((angle_deg, distance))
        
        result.sort(key=lambda x: x[0])
        return result
    

    def get_sector_xy(self, start_angle, end_angle):
        """
        Получить все данные лидара в секторе [start_angle, end_angle]
        """
        if not self.scan_data:
            return []
        
        num_readings = len(self.scan_data.ranges)
        angle_increment = math.degrees(self.scan_data.angle_increment)
        
        # Нормализуем углы в диапазон [0, 360)
        start = start_angle % 360
        end = end_angle % 360
        
        xs, ys = [], []
        
        for i in range(num_readings):
            # Преобразуем индекс в угол (обратное преобразование из get_distance_at_angle)
            raw_angle = i * angle_increment
            angle_deg = 360 - abs(raw_angle + 180)
            angle_deg = angle_deg % 360
            
            # Проверяем, попадает ли угол в сектор
            if start <= end:
                in_sector = start <= angle_deg <= end
            else:
                # Сектор пересекает 0 градусов
                in_sector = angle_deg >= start or angle_deg <= end
            
            if in_sector:
                distance = self.scan_data.ranges[i]
                if not math.isinf(distance) and not math.isnan(distance):
                    xs.append(distance * math.cos(math.radians(angle_deg)))
                    ys.append(distance * math.sin(math.radians(angle_deg)))
        
        return xs, ys
    

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
        angle_deg = 360 - abs(angle_deg + 180)
        
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
    

    def get_objects_positions(self, distance_threshold=0.3, min_cluster_size=3, max_distance=3.5):
        """
        Получить позиции всех объектов в глобальных координатах
        
        Args:
            distance_threshold: порог разрыва между кластерами (м)
            min_cluster_size: мин. кол-во точек для объекта
            max_distance: макс. расстояние до объектов (м)
        
        Returns:
            list of (x, y, distance, angle_deg) для каждого объекта, отсортированный по расстоянию
        """
        
        if not self.scan_data:
            return []
        
        ranges = list(self.scan_data.ranges)
        angle_increment = math.degrees(self.scan_data.angle_increment)
        
        # 1. Фильтрация валидных точек
        points = []
        for i, r in enumerate(ranges):
            if not math.isinf(r) and not math.isnan(r) and 0 < r < max_distance:
                points.append((i, r))
        
        if not points:
            return []
        
        # 2. Кластеризация по разрывам расстояний
        clusters = []
        current_cluster = [points[0]]
        
        for i in range(1, len(points)):
            prev_idx, prev_r = points[i-1]
            curr_idx, curr_r = points[i]
            
            # Разрыв по индексу или расстоянию
            idx_gap = (curr_idx - prev_idx) > 5
            dist_gap = abs(curr_r - prev_r) > distance_threshold
            
            if idx_gap or dist_gap:
                if len(current_cluster) >= min_cluster_size:
                    clusters.append(current_cluster)
                current_cluster = []
            
            current_cluster.append((curr_idx, curr_r))
        
        # Добавить последний кластер
        if len(current_cluster) >= min_cluster_size:
            clusters.append(current_cluster)
        
        # 3. Вычисление позиций объектов
        robot_x, robot_y = self.get_position()
        robot_yaw = self.get_yaw()
        objects = []
        
        for cluster in clusters:
            # Центр кластера - минимальное расстояние
            min_point = min(cluster, key=lambda p: p[1])
            center_idx, min_dist = min_point
            
            angle_deg = center_idx * angle_increment
            angle_deg = 360 - abs(angle_deg + 180)
            
            # Глобальные координаты
            object_angle_global = robot_yaw + math.radians(angle_deg)
            object_x = robot_x + min_dist * math.cos(object_angle_global)
            object_y = robot_y + min_dist * math.sin(object_angle_global)
            
            objects.append((object_x, object_y, min_dist, angle_deg))
        
        # Сортировка по расстоянию
        objects.sort(key=lambda obj: obj[2])
        
        return objects
    

    def follow_wall(self, target_distance=0.4, side='right', speed=0.15, duration=None):
        """
        Следование вдоль стены на заданном расстоянии
        target_distance: желаемое расстояние до стены (м)
        side: 'left' или 'right' - с какой стороны стена
        speed: скорость движения (м/с)
        duration: время следования в секундах (None = бесконечно)
        """
        l = open('logs.csv', 'w')
        
        start_time = rospy.Time.now()
        last_omega = 0
        e_i = 0

        while not rospy.is_shutdown():
            if duration is not None and (rospy.Time.now() - start_time).to_sec() >= duration:
                break
            
            if side == 'right':
                # Сектор вокруг 270 градусов
                xs, ys = bot.get_sector_xy(55, 125)
            else:
                xs, ys = bot.get_sector_xy(-110, -70)


            if len(xs) < 3:
                cmd = Twist()
                cmd.linear.x = speed
                cmd.angular.z = last_omega
                self.cmd_vel_pub.publish(cmd)

                print('stalled')

                self.rate.sleep()
                continue
            
            # 2. Центроид
            x_mean = sum(xs)/len(xs)
            y_mean = sum(ys)/len(ys)

            # 3. Ковариация
            Sxx = sum((x - x_mean)**2 for x in xs)/len(xs)
            Syy = sum((y - y_mean)**2 for y in ys)/len(ys)
            Sxy = sum((x - x_mean)*(y - y_mean) for x, y in zip(xs, ys))/len(xs)

            # 4. Собственные векторы (для простоты через формулы 2x2)
            theta = 0.5 * math.atan2(2*Sxy, Sxx - Syy)
            u_x = math.cos(theta)
            u_y = math.sin(theta)

            # нормаль к стене
            n_x = -u_y
            n_y = u_x

            # 5. расстояние до стены
            d = n_x * x_mean + n_y * y_mean   # предполагаем, что n единичной длины

            e_d = target_distance - d

            # 6. ошибка по углу (стена должна быть параллельна X)
            phi_wall = math.atan2(u_y, u_x)
            e_phi = -phi_wall



            # print(e_d, phi_wall)
            # print(f'{e_d},{e_phi}', file=l)
            e_i += e_phi

            # 7. контроллер
            k_d = 1.5
            k_phi = 2
            k_i = 0.01

            omega = k_phi * e_phi + k_d * e_d + k_i * e_i
            if omega > 1.5:
                omega = 1.5
            elif omega < -1.5:
                omega = -1.5

            last_omega = omega

            cmd = Twist()
            cmd.linear.x = speed
            cmd.angular.z = omega
            self.cmd_vel_pub.publish(cmd)

            # print(f'{e_d},{omega}', file=l)


            self.rate.sleep()

        
        self.stop()
        return True
    

    def follow_object(self, color='black', min_area=1000):

        while not rospy.is_shutdown():
            img = self.get_image()
            if img is not None:
                mask = matching._get_mask(img, color)
                countour = matching._find_contour(mask, min_area=min_area)
                if countour is not None:
                    pts = countour.reshape(-1, 2)
                    x1,y1 = pts.min(axis=0)
                    x2,y2 = pts.max(axis=0)
                    x_center = (x1 + x2) // 2
                    img_center = img.shape[1] // 2
                    cv2.rectangle(img, (x1,y1), (x2,y2), (0,255,0), 2)
                    cv2.line(img, (img_center,0), (img_center, img.shape[0]), (255,0,0), 2)
                    cv2.line(img, (x_center,0), (x_center, img.shape[0]), (0,0,255), 2)
                    

                    diff = (img_center - x_center) * 0.0012

                    twist = Twist()
                    twist.angular.z = diff

                    twist.linear.x = 0.1

                    self.cmd_vel_pub.publish(twist)
                    
                else:
                    print('not')

            self.rate.sleep()
        


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
        return math.atan2(math.sin(angle), math.cos(angle))
    
    def send_goal(self, x, y, w=1.0):
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = x # Координаты в системе отсчета карты
        goal.target_pose.pose.position.y = y # (0,0) - точка включения навигации
        goal.target_pose.pose.orientation.w = w

        self.client.send_goal(goal)
        self.client.wait_for_result()
    
    
    

# Пример использования
if __name__ == '__main__':
    try:
        bot = BotController()
        rospy.loginfo("BotController initialized")
        bot.wait(1000)
        # if not bot.wait_for_hardware():
        #     sys.exit(0)
        # bot.follow_object()
        # bot.turn_right()
        bot.send_goal(1,1)
        
        # print(bot.get_sector_data(10, 50))
        # print(bot.get_min_distance())
        # bot.follow_wall(duration=1000, side='left', target_distance=0.2)
 
    except rospy.ROSInterruptException:
        pass
