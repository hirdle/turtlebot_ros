import rospy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan, Image
import math
import matplotlib.pyplot as plt
import cv_bridge
import cv2
import numpy as np

class Bot:

    def __init__(self):
        rospy.init_node('bot', anonymous=True)

        self.cmd_vel = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

        self.current_frame = None
        self.odom_data = None
        self.scan_data = None

        self.start_x = 0
        self.start_y = 0

        rospy.Subscriber('/odom', Odometry, self.set_odom_data)
        rospy.Subscriber('/scan', LaserScan, self.set_scan_data)

        rospy.Subscriber('/camera/rgb/image_raw', Image, self.set_image)

        self.cv_bridge = cv_bridge.CvBridge()

        self.rate = rospy.Rate(100)

        self.base_speed = 0.15
        self.turn_speed = 0.5


        rospy.on_shutdown(self.stop)


    def set_image(self, msg):
        try:
            self.current_frame = self.cv_bridge.imgmsg_to_cv2(msg, 'bgr8')
        except:
            print('Camera Error')

    def get_image(self):
        return self.current_frame.copy()
        
    def set_odom_data(self, msg):
        self.odom_data = msg

    def set_scan_data(self, msg):
        self.scan_data = msg

    def wait(self, ms):
        rospy.sleep(ms/1000)

    def stop(self):
        self.cmd_vel.publish(Twist())

    def get_position(self):
        x = self.odom_data.pose.pose.position.x
        y = self.odom_data.pose.pose.position.y
        return x, y

    def move_linear(self, dist, speed=None):
        if not speed:
            speed = self.base_speed

        start_x, start_y = self.get_position()

        while not rospy.is_shutdown():

            curr_x, curr_y = self.get_position()

            if ((curr_x-start_x)**2+(curr_y-start_y)**2)**0.5 > dist:
                break


            twist = Twist()
            twist.linear.x = speed
            self.cmd_vel.publish(twist)

            self.rate.sleep()

        self.stop()

    
    def turn(self, angle, speed=None):
        if not speed:
            speed = self.turn_speed

        start_angle = self.get_curr_angle()
        target_angle = self.normalize_angle(start_angle - angle)

        while not rospy.is_shutdown():


            if abs(self.normalize_angle(self.get_curr_angle())  - target_angle) < 2:
                break

            twist = Twist()
            twist.angular.z = - speed * (angle / abs(angle))
            self.cmd_vel.publish(twist)

            self.rate.sleep()


        self.stop()
    

    def get_distance_at_angle(self, angle):
        
        ranges = self.scan_data.ranges

        angle_new = abs(-angle-180)
        if angle_new == 360:
            angle_new = 0

        return ranges[angle_new]
    

    def track_turn_object(self):
        while not rospy.is_shutdown():

            img = b.get_image()
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            kernel = np.ones((5,5), np.uint8)
            img = cv2.inRange(img, color_blue[0], color_blue[1])

            contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = [c for c in contours if cv2.contourArea(c) > 1000]

            if contours:
                contour_main = contours[0]

                pts = contour_main.reshape(-1,2)
                x1,y1 = pts.min(axis=0)
                x2,y2 = pts.max(axis=0)

                h,w = img.shape[:2]

                diff = w//2-(x2+x1)//2
                speed_z = diff*0.001

                twist = Twist()
                twist.angular.z = speed_z
                b.cmd_vel.publish(twist)

                b.rate.sleep()

                cv2.imshow('test', img)
                if cv2.waitKey(10) == ord('q'):
                    break


    def get_curr_angle(self):
        return(2*math.degrees(math.asin(self.odom_data.pose.pose.orientation.z)*math.copysign(1,self.odom_data.pose.pose.orientation.w)))

    def normalize_angle(self, angle):
        return math.degrees(math.atan2(math.sin(math.radians(angle)), math.cos(math.radians(angle))))


color_blue = [(0,0,90), (10,10,140)]



b = Bot()


b.wait(500)




