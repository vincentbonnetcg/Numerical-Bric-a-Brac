"""
@author: Vincent Bonnet
@description : Constraint base for the implicit solver
"""

import numpy as np
from constraints.base import Base
import core.math_2d as math2D
from core.data_block import DataBlock
from core.convex_hull import ConvexHull
from system.scene import Scene
from numba import njit


class AnchorSpring(Base):
    '''
    Describes a 2D spring constraint between a node and point
    '''
    def __init__(self, scene, stiffness, damping, node_id, kinematic, kinematic_parametric_point):
        Base.__init__(self, stiffness, damping, [node_id])
        target_pos = kinematic.get_position_from_parametric_point(kinematic_parametric_point)
        x, v = scene.node_state(node_id)
        self.rest_length = np.float(math2D.distance(target_pos, x))
        self.kinematic_index = np.uint32(kinematic.index)
        self.kinematic_component_index =  np.uint32(kinematic_parametric_point.index)
        self.kinematic_component_param = np.float(kinematic_parametric_point.t)

    @classmethod
    def num_nodes(cls) -> int :
        return 1

    @classmethod
    def init_element(cls, element, scene, node_id, kinematic, kinematic_parametric_point):
        '''
        element is an object of type self.datablock_ct generated in add_fields
        '''
        target_pos = kinematic.get_position_from_parametric_point(kinematic_parametric_point)
        x, v = scene.node_state(node_id)
        element.rest_length = math2D.distance(target_pos, x)
        element.kinematic_index = kinematic.index
        element.kinematic_component_index =  kinematic_parametric_point.index
        element.kinematic_component_param = kinematic_parametric_point.t

    @classmethod
    def add_fields(cls, datablock_cts : DataBlock) -> None:
        datablock_cts.add_field('rest_length', np.float)
        datablock_cts.add_field('kinematic_index', np.uint32)
        datablock_cts.add_field('kinematic_component_index', np.uint32)
        datablock_cts.add_field('kinematic_component_param', np.float)

    @classmethod
    def compute_forces(cls, datablock_cts : DataBlock, scene : Scene) -> None:
        kinematic_vel = np.zeros(2)
        node_ids_ptr = datablock_cts.node_ids
        stiffness_ptr = datablock_cts.stiffness
        damping_ptr = datablock_cts.damping
        rest_length_ptr = datablock_cts.rest_length
        k_index_ptr = datablock_cts.kinematic_index
        k_c_index_ptr = datablock_cts.kinematic_component_index
        k_c_param_ptr = datablock_cts.kinematic_component_param
        force_ptr = datablock_cts.f

        for ct_index in range(len(datablock_cts)):
            node_ids = node_ids_ptr[ct_index]
            x, v = scene.node_state(node_ids[0])
            kinematic = scene.kinematics[k_index_ptr[ct_index]]
            point_params = ConvexHull.ParametricPoint(k_c_index_ptr[ct_index], k_c_param_ptr[ct_index])
            target_pos = kinematic.get_position_from_parametric_point(point_params)
            force = spring_stretch_force(x, target_pos, rest_length_ptr[ct_index], stiffness_ptr[ct_index])
            force += spring_damping_force(x, target_pos, v, kinematic_vel, damping_ptr[ct_index])
            force_ptr[ct_index] = force

    @classmethod
    def compute_jacobians(cls, datablock_cts : DataBlock, scene : Scene) -> None:
        kinematic_vel = np.zeros(2)
        node_ids_ptr = datablock_cts.node_ids
        stiffness_ptr = datablock_cts.stiffness
        damping_ptr = datablock_cts.damping
        rest_length_ptr = datablock_cts.rest_length
        k_index_ptr = datablock_cts.kinematic_index
        k_c_index_ptr = datablock_cts.kinematic_component_index
        k_c_param_ptr = datablock_cts.kinematic_component_param
        dfdx_ptr = datablock_cts.dfdx
        dfdv_ptr = datablock_cts.dfdv

        for ct_index in range(len(datablock_cts)):
            node_ids = node_ids_ptr[ct_index]
            x, v = scene.node_state(node_ids[0])
            kinematic = scene.kinematics[k_index_ptr[ct_index]]
            point_params = ConvexHull.ParametricPoint(k_c_index_ptr[ct_index], k_c_param_ptr[ct_index])
            target_pos = kinematic.get_position_from_parametric_point(point_params)
            dfdx = spring_stretch_jacobian(x, target_pos, rest_length_ptr[ct_index], stiffness_ptr[ct_index])
            dfdv = spring_damping_jacobian(x, target_pos, v, kinematic_vel, damping_ptr[ct_index])
            dfdx_ptr[ct_index][0][0] = dfdx
            dfdv_ptr[ct_index][0][0] = dfdv

class Spring(Base):
    '''
    Describes a 2D spring constraint between two nodes
    '''
    def __init__(self, scene, stiffness, damping, node_ids):
        Base.__init__(self, stiffness, damping, node_ids)
        x0, v0 = scene.node_state(self.node_ids[0])
        x1, v1 = scene.node_state(self.node_ids[1])
        self.rest_length = np.float(math2D.distance(x0, x1))

    @classmethod
    def num_nodes(cls) -> int :
        return 2

    @classmethod
    def init_element(cls, element, scene, node_ids):
        '''
        element is an object of type self.datablock_ct generated in add_fields
        '''
        x0, v0 = scene.node_state(node_ids[0])
        x1, v1 = scene.node_state(node_ids[1])
        element.rest_length = math2D.distance(x0, x1)

    @classmethod
    def add_fields(cls, datablock_cts : DataBlock) -> None:
        datablock_cts.add_field('rest_length', np.float)

    @classmethod
    def compute_forces(cls, datablock_cts : DataBlock, scene : Scene) -> None:
        '''
        Add the force to the datablock
        '''
        node_ids_ptr = datablock_cts.node_ids
        rest_length_ptr = datablock_cts.rest_length
        stiffness_ptr = datablock_cts.stiffness
        damping_ptr = datablock_cts.damping
        force_ptr = datablock_cts.f

        for ct_index in range(len(datablock_cts)):
            node_ids = node_ids_ptr[ct_index]
            x0, v0 = scene.node_state(node_ids[0])
            x1, v1 = scene.node_state(node_ids[1])
            force = spring_stretch_force(x0, x1, rest_length_ptr[ct_index], stiffness_ptr[ct_index])
            force += spring_damping_force(x0, x1, v0, v1, damping_ptr[ct_index])
            force_ptr[ct_index][0] = force
            force_ptr[ct_index][1] = force * -1.0

    @classmethod
    def compute_jacobians(cls, datablock_cts : DataBlock, scene : Scene) -> None:
        '''
        Add the force jacobian functions to the datablock
        '''
        node_ids_ptr = datablock_cts.node_ids
        rest_length_ptr = datablock_cts.rest_length
        stiffness_ptr = datablock_cts.stiffness
        damping_ptr = datablock_cts.damping
        dfdx_ptr = datablock_cts.dfdx
        dfdv_ptr = datablock_cts.dfdv

        for ct_index in range(len(datablock_cts)):
            x0, v0 = scene.node_state(node_ids_ptr[ct_index][0])
            x1, v1 = scene.node_state(node_ids_ptr[ct_index][1])
            dfdx = spring_stretch_jacobian(x0, x1, rest_length_ptr[ct_index], stiffness_ptr[ct_index])
            dfdv = spring_damping_jacobian(x0, x1, v0, v1, damping_ptr[ct_index])
            # Set jacobians
            dfdx_ptr[ct_index][0][0] = dfdx_ptr[ct_index][1][1] = dfdx
            dfdx_ptr[ct_index][0][1] = dfdx_ptr[ct_index][1][0] = dfdx * -1
            dfdv_ptr[ct_index][0][0] = dfdv_ptr[ct_index][1][1] = dfdv
            dfdv_ptr[ct_index][0][1] = dfdv_ptr[ct_index][1][0] = dfdv * -1

'''
Utility Functions
'''
@njit
def spring_stretch_jacobian(x0, x1, rest, stiffness):
    direction = x0 - x1
    stretch = math2D.norm(direction)
    I = np.identity(2)
    if not math2D.is_close(stretch, 0.0):
        direction /= stretch
        A = np.outer(direction, direction)
        return -1.0 * stiffness * ((1 - (rest / stretch)) * (I - A) + A)

    return -1.0 * stiffness * I

@njit
def spring_damping_jacobian(x0, x1, v0, v1, damping):
    jacobian = np.zeros(shape=(2, 2))
    direction = x1 - x0
    stretch = math2D.norm(direction)
    if not math2D.is_close(stretch, 0.0):
        direction /= stretch
        A = np.outer(direction, direction)
        jacobian = -1.0 * damping * A

    return jacobian

@njit
def spring_stretch_force(x0, x1, rest, stiffness):
    direction = x1 - x0
    stretch = math2D.norm(direction)
    if not math2D.is_close(stretch, 0.0):
        direction /= stretch
    return direction * ((stretch - rest) * stiffness)

@njit
def spring_damping_force(x0, x1, v0, v1, damping):
    direction = x1 - x0
    stretch = math2D.norm(direction)
    if not math2D.is_close(stretch, 0.0):
        direction /= stretch
    relativeVelocity = v1 - v0
    return direction * (np.dot(relativeVelocity, direction) * damping)

@njit
def elastic_spring_energy(x0, x1, rest, stiffness):
    stretch = math2D.distance(x0, x1)
    return 0.5 * stiffness * ((stretch - rest)**2)
