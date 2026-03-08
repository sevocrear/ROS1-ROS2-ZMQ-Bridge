"""
This node subscibes to the given topic and calculates the time difference between the timestamp in the message and the current time in ROS2.
"""

import rclpy
from rclpy.node import Node
from can_msgs.msg import Frame


class AssessTimeDiffTimestamp(Node):
    def __init__(self):
        super().__init__('assess_time_diff_timestamp')
        self.subscription = self.create_subscription(
            Frame,
            '/received_messages',
            self.callback,
            10)
        self.subscription  # prevent unused variable warning
    def callback(self, msg):
        current_time = self.get_clock().now().to_msg()
        self.get_logger().info(f'Current time: {current_time.sec} seconds, {current_time.nanosec} nanoseconds')
        self.get_logger().info(f'Message time: {msg.header.stamp.sec} seconds, {msg.header.stamp.nanosec} nanoseconds')
        time_diff = (current_time.sec - msg.header.stamp.sec) * 1000 + (current_time.nanosec - msg.header.stamp.nanosec) / 1000000
        self.get_logger().info(f'Time difference: {time_diff} seconds')

def main(args=None):
    rclpy.init(args=args)
    node = AssessTimeDiffTimestamp()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
