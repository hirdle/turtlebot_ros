import rospy
import cv2
import tf
import matplotlib.pyplot as plt
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan, Imu, Image
from cv_bridge import CvBridge
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from tf.transformations import quaternion_from_euler
import actionlib

import numpy as np

import math


class Bot():

    def __init__(self):
        rospy.init_node('bot', anonymous=True)

        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

        rospy.Subscriber('/odom', Odometry, self.set_odom_data)
        rospy.Subscriber('/scan', LaserScan, self.set_scan_data)

        rospy.Subscriber('/camera/rgb/image_raw', Image, self.set_image)

        self.client = actionlib.SimpleActionClient("/move_base", MoveBaseAction)
        # self.client.wait_for_server()
        
        self.rate = rospy.Rate(100)

        self.base_speed = 0.15
        self.turn_speed = 1
        self.wheel_base = 0.287

        self.odom_data = None
        self.scan_data = None
        self.current_image = None

        self.colors = {
            'blue': [(0,0,90), (10,10,140)]
        }
        
        rospy.on_shutdown(self.stop)


    def wait(self, ms):
        rospy.sleep(ms/1000)

    def stop(self):
        self.cmd_vel_pub.publish(Twist())

    def get_image(self):
        return self.current_image.copy()
    
    def set_odom_data(self, msg):
        self.odom_data = msg
    
    def set_scan_data(self, msg):
        self.scan_data = msg

    def set_image(self, msg):
        try:
            self.current_image = CvBridge().imgmsg_to_cv2(msg, 'bgr8')

        except:
            print('Cameratarget_angle error')

    def get_position(self):
        x = self.odom_data.pose.pose.position.x
        y = self.odom_data.pose.pose.position.y
        return x,y
    
    def get_angle(self):
        return(2*math.degrees(math.asin(self.odom_data.pose.pose.orientation.z)*math.copysign(1,self.odom_data.pose.pose.orientation.w)))

    def normilize_angle(self, angle):
        return math.degrees(math.atan2(math.sin(math.radians(angle)), math.cos(math.radians(angle))))

    def move_linear(self, dist, speed=None):
        if not speed:
            speed = self.base_speed

        start_x, start_y = self.get_position()

        while not rospy.is_shutdown():

            curr_x, curr_y = self.get_position()

            if ((curr_x-start_x)**2+ (curr_y-start_y)**2)**0.5 >= dist:
                break

            twist = Twist()
            twist.linear.x = speed

            self.cmd_vel_pub.publish(twist)

            self.rate.sleep()

        self.stop()

    def turn(self, angle, speed=None):
        if not speed:
            speed = self.turn_speed

        target_angle = self.normilize_angle(self.get_angle() - angle)

        while not rospy.is_shutdown():

            if abs(target_angle-self.get_angle()) < 2:
                break

            twist = Twist()
            twist.angular.z = -speed * (angle/abs(angle))

            self.cmd_vel_pub.publish(twist)
            self.rate.sleep()

        self.stop()


    def move_motors_speed(self, left_speed, right_speed):
        
        linear = (right_speed + left_speed) / 2.0
        angular = (right_speed - left_speed) / self.wheel_base

        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.cmd_vel_pub.publish(twist)
    

    def move_circle_arc(self, radius, angle_deg, speed=0.1, clockwise=False):

        angular_speed = speed / radius
        linear_component = angular_speed * (self.wheel_base / 2.0)

        if clockwise:
            left_speed = speed + linear_component
            right_speed = speed - linear_component
        else:
            left_speed = speed - linear_component
            right_speed = speed + linear_component

        current_angle = self.get_angle()
        target_angle_deg = abs(angle_deg)
        accumulated_angle = 0.0

        while not rospy.is_shutdown():
            previous_angle = current_angle
            current_angle = self.get_angle()
            delta = self.normilize_angle(current_angle - previous_angle)
            accumulated_angle += abs(delta)

            if accumulated_angle >= target_angle_deg:
                break

            self.move_motors_speed(left_speed, right_speed)

        self.stop()


    def get_distance_at_angle(self, angle):

        angle = 360-abs(-angle - 180)

        if angle == 360:
            angle = 0

        return self.scan_data.ranges[angle]

    def get_min_distance(self):
        """Минимальное расстояние до препятствия"""
        if not self.scan_data:
            return float('inf')

        valid_ranges = [
            r for r in self.scan_data.ranges
            if not math.isinf(r) and not math.isnan(r) and r > 0
        ]

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

        start = start_angle % 360
        end = end_angle % 360

        for i in range(num_readings):
            raw_angle = i * angle_increment
            angle_deg = 360 - abs(raw_angle + 180)
            angle_deg = angle_deg % 360

            if start <= end:
                in_sector = start <= angle_deg <= end
            else:
                in_sector = angle_deg >= start or angle_deg <= end

            if in_sector:
                distance = self.scan_data.ranges[i]
                if not math.isinf(distance) and not math.isnan(distance):
                    result.append((angle_deg, distance))

        result.sort(key=lambda x: x[0])
        return result
    

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

        robot_x, robot_y = self.get_position()
        robot_yaw = math.radians(self.get_angle())

        object_angle_global = robot_yaw + math.radians(angle_deg)

        object_x = robot_x + distance * math.cos(object_angle_global)
        object_y = robot_y + distance * math.sin(object_angle_global)

        return (object_x, object_y, distance, angle_deg)
    

    def get_objects_positions(self, distance_threshold=0.3, min_cluster_size=3, max_distance=3.5):
        """
        Получить позиции всех объектов в глобальных координатах
        """
        if not self.scan_data:
            return []

        ranges = list(self.scan_data.ranges)
        angle_increment = math.degrees(self.scan_data.angle_increment)

        points = []
        for i, r in enumerate(ranges):
            if not math.isinf(r) and not math.isnan(r) and 0 < r < max_distance:
                points.append((i, r))

        if not points:
            return []

        clusters = []
        current_cluster = [points[0]]

        for i in range(1, len(points)):
            prev_idx, prev_r = points[i-1]
            curr_idx, curr_r = points[i]

            idx_gap = (curr_idx - prev_idx) > 5
            dist_gap = abs(curr_r - prev_r) > distance_threshold

            if idx_gap or dist_gap:
                if len(current_cluster) >= min_cluster_size:
                    clusters.append(current_cluster)
                current_cluster = []

            current_cluster.append((curr_idx, curr_r))

        if len(current_cluster) >= min_cluster_size:
            clusters.append(current_cluster)

        robot_x, robot_y = self.get_position()
        robot_yaw = math.radians(self.get_angle())
        objects = []

        for cluster in clusters:
            min_point = min(cluster, key=lambda p: p[1])
            center_idx, min_dist = min_point

            angle_deg = center_idx * angle_increment
            angle_deg = 360 - abs(angle_deg + 180)

            object_angle_global = robot_yaw + math.radians(angle_deg)
            object_x = robot_x + min_dist * math.cos(object_angle_global)
            object_y = robot_y + min_dist * math.sin(object_angle_global)

            objects.append((object_x, object_y, min_dist, angle_deg))

        objects.sort(key=lambda obj: obj[2])

        return objects
    
    
    def get_mask(self, frame, color='blue'):

        kernel = np.ones((5,5), np.uint8)

        low_color, high_color = self.colors.get(color)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mask = cv2.inRange(frame, low_color, high_color)

        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        return mask
    
    def find_contours(self, frame, min_area=1000):
        contours, _ = cv2.findContours(frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = [c for c in contours if cv2.contourArea(c) > min_area]
        return contours
    
    def track_object(self):

        while not rospy.is_shutdown():

            mask = self.get_mask(self.get_image())
            contours = self.find_contours(mask)

            if contours:

                c = contours[0]

                pts = c.reshape(-1,2)
                x1,y1 = pts.min(axis=0)
                x2,y2 = pts.max(axis=0)

                h, w = mask.shape[:2]

                diff = w/2 - (x1+x2)/2
                print(diff)

                twist = Twist()
                twist.angular.z = diff*0.001

                self.cmd_vel_pub.publish(twist)
                self.rate.sleep()


    def send_goal(self, x, y, yaw_deg):

        yaw = math.radians(yaw_deg)
        q = quaternion_from_euler(0, 0, yaw)

        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()

        goal.target_pose.pose.position.x = x
        goal.target_pose.pose.position.y = y
        goal.target_pose.pose.position.z = 0.0
        goal.target_pose.pose.orientation.x = q[0]
        goal.target_pose.pose.orientation.y = q[1]
        goal.target_pose.pose.orientation.z = q[2]
        goal.target_pose.pose.orientation.w = q[3]

        self.client.send_goal(goal)



b = Bot()
b.wait(1500)
# b.send_goal(-1.5,1.5,90)
print(b.get_object_angle_distance())
