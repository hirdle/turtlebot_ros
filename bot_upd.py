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
        self.client.wait_for_server()
        
        self.rate = rospy.Rate(100)

        self.base_speed = 0.15
        self.turn_speed = 1

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

    def get_distance_at_angle(self, angle):

        angle = 360-abs(-angle - 180)

        if angle == 360:
            angle = 0

        return self.scan_data.ranges[angle]
    
    
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
b.send_goal(-1.5,1.5,90)