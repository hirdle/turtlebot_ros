#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест функции detect_sign с видеопотоком ROS камеры
Клавиши: 'q' - выход, '1'-'4' - выбор цвета (blue/red/green/yellow), 'a' - auto
"""

import rospy
import cv2
import glob
import os
from actual.bot import BotController
from actual.matching import detect_sign

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "template")


def main():
    bot = BotController(node_name='test_sign_camera')
    rospy.loginfo("Waiting for camera...")
    
    if not bot.wait_for_hardware(timeout=10.0):
        rospy.logerr("Failed to initialize camera")
        return

    templates = glob.glob(os.path.join(TEMPLATE_DIR, "*.png"))
    templates += glob.glob(os.path.join(TEMPLATE_DIR, "*.jpg"))

    if not templates:
        rospy.logwarn(f"No templates found in {TEMPLATE_DIR}")

    color_mode = 'auto'
    color_keys = {'1': 'blue', '2': 'red', '3': 'green', '4': 'yellow', 'a': 'auto'}

    rospy.loginfo("Camera ready. Press 'q' to exit.")
    rospy.loginfo(f"Templates found: {len(templates)}")
    rospy.loginfo("Keys: 1=blue, 2=red, 3=green, 4=yellow, a=auto")

    while not rospy.is_shutdown():
        frame = bot.get_image()
        if frame is None:
            rospy.sleep(0.1)
            continue

        is_match, confidence, template_name = detect_sign(frame, templates, color=color_mode)

        status = f"Match: {template_name} ({confidence:.2f})" if is_match else f"No match ({confidence:.2f})"
        color = (0, 255, 0) if is_match else (0, 0, 255)

        cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, f"Color: {color_mode}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.imshow("Sign Test", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif chr(key) in color_keys:
            color_mode = color_keys[chr(key)]
            rospy.loginfo(f"Color mode: {color_mode}")

    cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main()
    except rospy.ROSInterruptException:
        pass
