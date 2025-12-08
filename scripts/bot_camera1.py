#!/usr/bin/env python

import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError

from matching_object import detect_and_match


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
    

# Пример использования
if __name__ == '__main__':
    try:
        cam = BotCameraController()
        rospy.loginfo("BotCameraController initialized")
        
        if cam.wait_for_camera():
            rospy.loginfo("Camera ready")
            while True:
                image = cam.get_image()
                result, confidence, best, image_ = detect_and_match(
                    frame=image,
                    template_paths=[
                        'template/forward.png',
                        'template/backward.png',
                        'template/left.png',
                        'template/right.png',
                        'template/stop.png'
                    ],
                    color='auto',  # автоопределение цвета
                    threshold=0.45,
                    save_path=None,
                )
                if image_ is not None:
                    cv2.imshow("Camera Frame", image_)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                cam.rate.sleep()

    except rospy.ROSInterruptException:
        pass
