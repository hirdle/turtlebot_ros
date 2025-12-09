#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест функции detect_traffic_light с видеопотоком ROS камеры
Клавиши: 'q' - выход
"""

import rospy
import cv2
from bot import BotController
from matching import detect_traffic_light

COLOR_BGR = {
    'red': (0, 0, 255),
    'green': (0, 255, 0),
    'yellow': (0, 255, 255),
    'blue': (255, 0, 0),
}


def main():
    bot = BotController(node_name='test_traffic_light_camera')
    rospy.loginfo("Waiting for camera...")
    
    if not bot.wait_for_hardware(timeout=10.0):
        rospy.logerr("Failed to initialize camera")
        return

    rospy.loginfo("Camera ready. Press 'q' to exit.")

    while not rospy.is_shutdown():
        frame = bot.get_image()
        if frame is None:
            rospy.sleep(0.1)
            continue

        lights = detect_traffic_light(frame)
        print(f"Detected lights: {[i[0] for i in lights]}")

        for i, (color, contour, area) in enumerate(lights):
            bgr = COLOR_BGR.get(color, (255, 255, 255))
            cv2.drawContours(frame, [contour], -1, bgr, 2)
            x, y, w, h = cv2.boundingRect(contour)
            cv2.putText(frame, f"{color} ({int(area)})", (x, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, bgr, 2)

        dominant = lights[0][0] if lights else "none"
        cv2.putText(frame, f"Dominant: {dominant}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, COLOR_BGR.get(dominant, (255, 255, 255)), 2)
        cv2.putText(frame, f"Colors: {len(lights)}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow("Traffic Light Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main()
    except rospy.ROSInterruptException:
        pass
