#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import actionlib
import math

from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from tf.transformations import quaternion_from_euler

def send_goal(x, y, yaw_deg):
    client = actionlib.SimpleActionClient("move_base", MoveBaseAction)
    rospy.loginfo("Жду action server move_base...")
    client.wait_for_server()
    rospy.loginfo("move_base доступен")

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

    rospy.loginfo("Отправляю goal: x=%.2f, y=%.2f, yaw=%d°" % (x, y, yaw_deg))
    client.send_goal(goal)

    # Можно подождать результат
    finished = client.wait_for_result(rospy.Duration(120.0))  # таймаут 60 сек

    if not finished:
        rospy.logwarn("Не успел доехать до цели (timeout)")
        client.cancel_goal()
    else:
        state = client.get_state()
        rospy.loginfo("Результат move_base state=%d" % state)

if __name__ == "__main__":
    rospy.init_node("send_goal_action")

    x_target = 4
    y_target = 2
    yaw_deg = 0

    send_goal(x_target, y_target, yaw_deg)
