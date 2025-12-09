#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест функции detect_aruco с видеопотоком ROS камеры
Клавиши: 'q' - выход
"""

import rospy
import cv2
from bot import BotController
from matching import detect_aruco


def main():
    bot = BotController(node_name='test_aruco_camera')
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

        markers = detect_aruco(frame)

        for marker_id, corners, area in markers:
            pts = corners[0].astype(int)
            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
            cx, cy = pts.mean(axis=0).astype(int)
            cv2.putText(frame, f"ID:{marker_id} A:{int(area)}", (cx - 30, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        info = f"ArUco: {len(markers)}"
        cv2.putText(frame, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        cv2.imshow("ArUco Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main()
    except rospy.ROSInterruptException:
        pass
