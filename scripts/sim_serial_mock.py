#!/usr/bin/env python
# -*- coding: utf-8 -*-
import rospy
from geometry_msgs.msg import Twist
from std_msgs.msg import String


def format_cmd(msg):
    return "cmd_vel vx={:.3f} wz={:.3f}".format(msg.linear.x, msg.angular.z)


class SerialMockNode(object):
    def __init__(self):
        rospy.init_node('serial_mock', anonymous=False)
        self.pub = rospy.Publisher('/serial_status', String, queue_size=10)
        rospy.Subscriber('/cmd_vel', Twist, self.cmd_vel_callback)
        self.last_cmd = None
        self.timer = rospy.Timer(rospy.Duration(0.1), self.timer_callback)
        rospy.loginfo('serial_mock started, listening to /cmd_vel')
        rospy.spin()

    def cmd_vel_callback(self, msg):
        self.last_cmd = msg
        rospy.logdebug('serial_mock received %s', format_cmd(msg))

    def timer_callback(self, event):
        if self.last_cmd is None:
            return
        status = String()
        status.data = format_cmd(self.last_cmd)
        self.pub.publish(status)


if __name__ == '__main__':
    try:
        SerialMockNode()
    except rospy.ROSInterruptException:
        pass
