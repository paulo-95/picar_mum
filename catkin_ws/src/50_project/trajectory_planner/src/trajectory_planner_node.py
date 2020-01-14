#!/usr/bin/env python
import rospy
import yaml
from geometry_msgs.msg import Point32
from sensor_msgs.msg import Image
from picar_msgs.srv import SetValue
from std_msgs.msg import Float32
from picar_msgs.msg import CarCmd, MsgCurvePoint2D
from picar_common.picar_common import get_param, get_config_file_path, set_param
from overtaker_state_machine import OvertakeStateMachine
from picar_common.curve import *

DEFAULT_FALSE_VALUE = float("inf")


class TrajectoryPlanner:

    def __init__(self):
        self._params = {}
        self.publishers = {}
        self.services = {}

        # import parameters from config yaml files
        config_file_name = get_param("~config_file_name", "default")

        config_file_path = get_config_file_path("trajection_planner",
                                                config_file_name)

        # shut down node if no config file could be found
        if config_file_path is None:
            rospy.signal_shutdown("Could not find any config file... "
                                  "Shutting down!")

        # read the config parameters form .yaml file
        self.setup_params(config_file_path)

        # register all publishers
        self.init_subscribers()

        # register all publishers
        self.init_publishers()

        # create all services
        self.init_services()

        self.switch_params = {"line_detection": False,
                              "object_detection": False,  # object detected
                              "overtake": False,  # overtaking is allowed
                              "cur_dist_obstacle": 0.0,
                              "t": 0.0,
                              "cur_dist_overtake": 0.0}

        # create state machine
        self.state_machine = OvertakeStateMachine(self.switch_params, self._params["min_dist_obstacle"])

    # --------------------------------------------------------------------
    # ----------------------- initialization -----------------------------
    # --------------------------------------------------------------------

    def setup_params(self, config_file_path):
        with open(config_file_path, "r") as file_handle:
            data = yaml.safe_load(file_handle)
        self._params = data
        for param_name in self._params:
            set_param("~" + param_name, self._params[param_name])

    def init_services(self):
        pass

    def init_publishers(self):
        """ initialize ROS publishers and stores them in a dictionary"""
        # relative position of leaders blue ball to picar
        self.publishers["des_car_command"] = rospy.Publisher("~desired_car_command", CarCmd,
                                                             queue_size=1)

    def init_subscribers(self):
        """ initialize ROS subscribers and stores them in a dictionary"""
        # pacemaker
        rospy.Subscriber("~pacemaker", Float32, self.run_node)
        # position of detected obstacle
        rospy.Subscriber("~obstacle_position", Point32, self.update_obstacle_pos_clb)
        # point on curve with position and circle
        rospy.Subscriber("~curve_point", MsgCurvePoint2D, self.update_curved_point_clb)

    def update_obstacle_pos_clb(self, message):
        obstacle = Point2D([message.x, message.y])

        if obstacle.x == DEFAULT_FALSE_VALUE or obstacle.y == DEFAULT_FALSE_VALUE:
            self.switch_params["object_detection"] = False
            self.state_machine.obstacle_point = None
        else:
            self.switch_params["object_detection"] = True
            self.state_machine.obstacle_point = obstacle

    def update_curved_point_clb(self, message):
        # message of type MsgCurvePoint2D
        curve_point = CurvePoint2D([message.x, message.y])
        curve_point.slope = message.slope
        curve_point.circle = Circle2D(message.cR, Point2D([message.x, message.y]))

        if curve_point.x == DEFAULT_FALSE_VALUE or curve_point.x == DEFAULT_FALSE_VALUE:
            self.switch_params["line_detection"] = False
            self.state_machine.curve_point = None
        else:
            self.switch_params["line_detection"] = True
            self.state_machine.curve_point = curve_point

    def run_node(self, time):
        time = time.data
        # update values of switching parameters
        self.switch_params["overtake"] = False  # TODO
        self.switch_params["cur_dist_obstacle"] = 0.0  # TODO
        self.switch_params["t"] = 0.0  # TODO
        self.switch_params["cur_dist_overtake"] = 0.0  # TODO

        # update switching parameters in state machine
        self.state_machine.switch_params = self.switch_params
        self.state_machine.state_switcher()

        rospy.loginfo("internal state clock: %f State: %s", time, self.state_machine.current_state)


if __name__ == "__main__":
    rospy.init_node("trajectory_planner")
    TrajectoryPlanner()
    rospy.spin()