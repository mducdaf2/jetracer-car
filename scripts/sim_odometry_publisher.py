#!/usr/bin/env python
# -*- coding: utf-8 -*-
import rospy
from nav_msgs.msg import Odometry, Path
from geometry_msgs.msg import Twist, TransformStamped, PoseStamped, Quaternion
import tf
from math import sin, cos


class OdometryPublisher(object):
    def __init__(self):
        rospy.init_node('simulation_odometry', anonymous=False)
        self.frame_id = rospy.get_param('/simulation/odom_frame', 'odom')
        self.child_frame_id = rospy.get_param('/simulation/base_frame', 'base_link')
        self.publish_rate = rospy.get_param('/simulation/publish_rate', 20.0)
        self.max_path_length = rospy.get_param('/simulation/path_max_length', 1000)

        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.vx = 0.0
        self.wz = 0.0
        self.last_time = rospy.Time.now()

        self.odom_pub = rospy.Publisher('/odom', Odometry, queue_size=10)
        self.path_pub = rospy.Publisher('/path', Path, queue_size=10)
        self.tf_broadcaster = tf.TransformBroadcaster()

        rospy.Subscriber('/cmd_vel', Twist, self.cmd_vel_callback)

        self.path = Path()
        self.path.header.frame_id = self.frame_id

        self.timer = rospy.Timer(rospy.Duration(1.0 / self.publish_rate), self.update)

        rospy.loginfo('simulation_odometry started, publishing /odom and /path')
        rospy.spin()

    def cmd_vel_callback(self, msg):
        self.vx = msg.linear.x
        self.wz = msg.angular.z

    def update(self, event):
        now = rospy.Time.now()
        dt = (now - self.last_time).to_sec()
        if dt <= 0.0:
            return

        self.last_time = now
        self.x += self.vx * cos(self.yaw) * dt
        self.y += self.vx * sin(self.yaw) * dt
        self.yaw += self.wz * dt

        odom = Odometry()
        odom.header.stamp = now
        odom.header.frame_id = self.frame_id
        odom.child_frame_id = self.child_frame_id
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0

        quaternion = tf.transformations.quaternion_from_euler(0.0, 0.0, self.yaw)
        odom.pose.pose.orientation = Quaternion(*quaternion)
        odom.twist.twist.linear.x = self.vx
        odom.twist.twist.angular.z = self.wz

        self.odom_pub.publish(odom)
        self.tf_broadcaster.sendTransform(
            (self.x, self.y, 0.0),
            quaternion,
            now,
            self.child_frame_id,
            self.frame_id,
        )

        pose = PoseStamped()
        pose.header = odom.header
        pose.pose = odom.pose.pose
        self.path.header.stamp = now
        self.path.poses.append(pose)
        if len(self.path.poses) > self.max_path_length:
            self.path.poses = self.path.poses[-self.max_path_length:]
        self.path_pub.publish(self.path)


if __name__ == '__main__':
    try:
        OdometryPublisher()
    except rospy.ROSInterruptException:
        pass
