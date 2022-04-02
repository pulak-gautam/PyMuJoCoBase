from pdb import set_trace

import mujoco as mj
import nlopt
import numpy as np
from mujoco.glfw import glfw
from numpy.linalg import inv
from scipy import optimize

from mujoco_base import MuJoCoBase


class InitialValueProblem(MuJoCoBase):
    def __init__(self, xml_path):
        super().__init__(xml_path)
        self.simend = 5.0

    def reset(self):
        # Set camera configuration
        self.cam.azimuth = 89.608063
        self.cam.elevation = -11.588379
        self.cam.distance = 5.0
        self.cam.lookat = np.array([0.0, 0.0, 1.5])

        # Set initial guess
        v = 10.0
        theta = np.pi / 4
        time_of_flight = 2.0

        sol = self.optimize_ic(np.array([v, theta, time_of_flight]))

        # NLOPT solution:
        #     v_sol = 9.398687489285555
        # theta_sol = 1.2184054599970882
        v_sol, theta_sol = sol[0], sol[1]

        self.data.qvel[0] = v * np.cos(theta)
        self.data.qvel[2] = v * np.sin(theta)

    def simulator(self, x):
        v, theta, time_of_flight = x[0], x[1], x[2]

        self.data.qvel[0] = v * np.cos(theta)
        self.data.qvel[2] = v * np.sin(theta)

        while (self.data.time < time_of_flight):
            # Step simulation environment
            mj.mj_step(self.model, self.data)

        # Get position
        pos = np.array([self.data.qpos[0], self.data.qpos[2]])

        # Reset Data
        mj.mj_resetData(self.model, self.data)

        return pos

    def cost_func(self, x, grad):
        cost = 0.0

        return cost

    def equality_constraints(self, result, x, grad):
        """
        For details of the API please refer to:
        https://nlopt.readthedocs.io/en/latest/NLopt_Python_Reference/#:~:text=remove_inequality_constraints()%0Aopt.remove_equality_constraints()-,Vector%2Dvalued%20constraints,-Just%20as%20for 
        Note: Please open the link in Chrome
        """
        pos = self.simulator(x)
        result[0] = pos[0] - 5.0
        result[1] = pos[1] - 2.1

    def optimize_ic(self, x):
        # Define optimization problem
        opt = nlopt.opt(nlopt.LN_COBYLA, 3)

        # Define lower and upper bounds
        opt.set_lower_bounds([0.1, 0.1, 0.1])
        opt.set_upper_bounds([10000.0, np.pi/2-0.1, 10000.0])

        # Set objective funtion
        opt.set_min_objective(self.cost_func)

        # Define equality constraints
        tol = [1e-4, 1e-4]
        opt.add_equality_mconstraint(self.equality_constraints, tol)
        opt.set_xtol_rel(1e-4)

        xopt = opt.optimize(x)

        return xopt

    def simulate(self):
        while not glfw.window_should_close(self.window):
            simstart = self.data.time

            while (self.data.time - simstart < 1.0/60.0):
                # Step simulation environment
                mj.mj_step(self.model, self.data)

            if self.data.time >= self.simend:
                break

            # get framebuffer viewport
            viewport_width, viewport_height = glfw.get_framebuffer_size(
                self.window)
            viewport = mj.MjrRect(0, 0, viewport_width, viewport_height)

            # Update scene and render
            self.cam.lookat[0] = self.data.qpos[0]
            mj.mjv_updateScene(self.model, self.data, self.opt, None, self.cam,
                               mj.mjtCatBit.mjCAT_ALL.value, self.scene)
            mj.mjr_render(viewport, self.scene, self.context)

            # swap OpenGL buffers (blocking call due to v-sync)
            glfw.swap_buffers(self.window)

            # process pending GUI events, call GLFW callbacks
            glfw.poll_events()

        glfw.terminate()


def main():
    xml_path = "./xml/projectile_opt.xml"
    sim = InitialValueProblem(xml_path)
    sim.reset()
    sim.simulate()


if __name__ == "__main__":
    main()