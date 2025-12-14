#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bot_camera_matching.py - Матчинг шаблонов в реальном времени с ROS камеры TurtleBot3

Управление:
  q - выход
  1,2,3,4 - принудительно выбрать цвет (blue, red, green, yellow)
  0 - вернуться к auto режиму
"""

import rospy
import cv2
import numpy as np
import os
import glob
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError

from main_matching_traffic_light import (
    detect_and_match
)



class BotCameraMatching:
    """Класс для матчинга шаблонов с ROS камеры TurtleBot3"""
    
    def __init__(self, camera_topic='/front_camera/image_raw', node_name='bot_camera_matching'):
        rospy.init_node(node_name, anonymous=True)
        
        self.bridge = CvBridge()
        self.current_frame = None
        self.padding = 20
        
        rospy.Subscriber(camera_topic, Image, self._image_callback)
        self.rate = rospy.Rate(30)
        
    
    def _image_callback(self, msg):
        try:
            self.current_frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except CvBridgeError as e:
            rospy.logerr(f"CvBridge Error: {e}")
    

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
    
    
    def run(self):
        """Запустить визуализацию матчинга в реальном времени"""
        rospy.loginfo("Запуск матчинга с ROS камеры...")

        if not self.wait_for_camera():
            rospy.logerr("Камера не готова")
            return
        
        rospy.loginfo("Камера готова")
        
        while not rospy.is_shutdown():
            if self.current_frame is None:
                self.rate.sleep()
                continue
            
            result = detect_and_match(
                frame=self.current_frame.copy()
            )
            print(*[i[0] for i in result])
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            
            self.rate.sleep()
        
        cv2.destroyAllWindows()
        rospy.loginfo("Завершено")


if __name__ == '__main__':
    try:
        matcher = BotCameraMatching(
            camera_topic='/front_camera/image_raw'
        )
        matcher.run()
    except rospy.ROSInterruptException:
        pass
