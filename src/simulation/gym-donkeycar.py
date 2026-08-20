import rospy
import gymnasium as gym
import gym_donkeycar
import numpy as np

conf = {
    "host": "172.21.80.1", 
    "port": 9091
}
env = gym.make("donkey-warren-track-v0", conf=conf)

obs, info = env.reset()

rospy.publish_image(obs)
while True:
    if hasattr(rospy, 'read_control'):
        steering, throttle = rospy.read_control()
        action = np.array([steering, throttle])
    else:
        action = np.array([0.0, 0.5])

    obs, reward, terminated, truncated, info = env.step(action)

    rospy.publish_image(obs)