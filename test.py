import cv2
import rospy
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu, LaserScan, Image
from nav_msgs.msg import Odometry
from cv_bridge import CvBridge
import tf
import math


# === HSV ДИАПАЗОНЫ ЦВЕТОВ ===
COLORS = {
    'blue': ((100, 100, 100), (130, 255, 255)),
    'green': ((40, 30, 30), (80, 255, 255)),
    'yellow': ((20, 100, 100), (40, 255, 255)),
    'red': None,  # особый случай - два диапазона
}


class Bot():

    def __init__(self):
        
        rospy.init_node('bot_controller', anonymous=True)

        self.start_x = 0
        self.start_y = 0
        self.start_yaw = 0

        self.cmd_vel = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

        rospy.Subscriber('/scan', LaserScan, self.scan_callback)
        rospy.Subscriber('/odom', Odometry, self.odom_callback)
        rospy.Subscriber('/imu', Imu, self.imu_callback)


        self.cv_bridge = CvBridge()
        self.current_frame = None

        rospy.Subscriber('/front_camera/image_raw', Image, self.image_callback)

        self.rate = rospy.Rate(100)

        rospy.on_shutdown(self.stop)


    def image_callback(self, msg):
        self.current_frame = self.cv_bridge.imgmsg_to_cv2(msg, 'bgr8')
    
    def odom_callback(self, msg):
        self.odom_data = msg

    def imu_callback(self, msg):
        self.imu_data = msg

    def scan_callback(self, msg):
        self.scan_data = msg

    def wait(self, ms):
        rospy.sleep(ms/1000)

    def stop(self):
        twist = Twist()
        self.cmd_vel.publish(twist)

    def get_image(self):
        return self.current_frame.copy()
    
    def get_position(self):
        x = self.odom_data.pose.pose.position.x - self.start_x
        y = self.odom_data.pose.pose.position.y - self.start_y
        return x, y

    def get_yaw(self):
        orient = self.odom_data.pose.pose.orientation
        q = (orient.x, orient.y, orient.z, orient.w)
        
        data = tf.transformations.euler_from_quaternion(q)

        return data[2]
    
    def get_yaw_degrees(self):
        return math.degrees(self.get_yaw())
    
    def move_linear(self, dist, speed=0.1):

        start_x = self.odom_data.pose.pose.position.x
        start_y = self.odom_data.pose.pose.position.y

        while not rospy.is_shutdown():

            twist = Twist()
            twist.linear.x = speed
            twist.angular.z = 0

            self.cmd_vel.publish(twist)

            curr_x = self.odom_data.pose.pose.position.x
            curr_y = self.odom_data.pose.pose.position.y

            traveled = ((curr_x - start_x) ** 2 + (curr_y - start_y) ** 2) ** 0.5

            if traveled >= dist:
                break

            self.rate.sleep()

        self.stop()

    
    def turn(self, angle, speed):

        angle_rad = math.radians(angle)
        start_yaw = self.get_yaw()
        target_yaw = self.normalize_angle(start_yaw - angle_rad)
        
        twist = Twist()
        twist.angular.z = -abs(speed) if angle_rad > 0 else abs(speed)
        
        while not rospy.is_shutdown():
            current_yaw = self.get_yaw()
            diff = self.normalize_angle(current_yaw-target_yaw)
            
            if abs(diff) < math.radians(2):  # точность 2 градуса
                break
            
            self.cmd_vel.publish(twist)
            self.rate.sleep()
        
        self.stop()
        return
    
    def normalize_angle(self, angle):
        return math.atan2(math.sin(angle), math.cos(angle))


# import colorsys

# h,s,v=colorsys.rgb_to_hsv(80/255,30/255,40/255)
# print(h*360,s*100,v*100)
# h,s,v=colorsys.rgb_to_hsv(65/255,25/255,35/255)

# print(h*360,s*100,v*100)
    
bot = Bot()
bot.wait(2000)
bot.turn(-90, 0.2)
# print(math.degrees(bot.get_yaw()))
# print(bot.move_linear(0.1))