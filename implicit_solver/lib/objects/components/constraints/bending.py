"""
@author: Vincent Bonnet
@description : Bending Constraint for the implicit solver
"""

from lib.objects.components import ConstraintBase
import lib.common.math_2d as math2D
from lib.common.data_block import DataBlock
import lib.common.node_accessor as na
from lib.system.scene import Scene
from numba import njit
import math
import numpy as np

class Bending(ConstraintBase):
    '''
    Describes a 2D bending constraint of a thin inextensible wire
    between three nodes.
    This bending is NOT the proper bending formulation and uses angle instead of curvature
    Some instabilities when using the curvature => Need to investigate
    '''
    def __init__(self):
        '''
        Constraint three nodes to maintain angle between
        node_ids[0] - node_ids[1] - node_ids[2]
        '''
        ConstraintBase.__init__(self, num_nodes = 3)
        self.rest_angle = np.float64(0.0)

    def set_object(self, details, node_ids):
        '''
        element is an object of type self.datablock_ct generated by add_fields
        '''
        x0, v0 = na.node_xv(details.node.blocks, node_ids[0])
        x1, v1 = na.node_xv(details.node.blocks, node_ids[1])
        x2, v2 = na.node_xv(details.node.blocks, node_ids[2])
        self.rest_angle = np.float64(math2D.angle(x0, x1, x2))
        self.node_IDs = np.copy(node_ids)

    @classmethod
    def compute_forces(cls, blocks_iterator, scene : Scene, details) -> None:
        '''
        Add the force to the datablock
        '''
        for ct_block in blocks_iterator:
            node_ids_ptr = ct_block['node_IDs']
            rest_angle_ptr = ct_block['rest_angle']
            stiffness_ptr = ct_block['stiffness']
            force_ptr = ct_block['f']
            block_n_elements = ct_block['blockInfo_numElements']

            for ct_index in range(block_n_elements):
                x0, v0 = na.node_xv(details.node.blocks, node_ids_ptr[ct_index][0])
                x1, v1 = na.node_xv(details.node.blocks, node_ids_ptr[ct_index][1])
                x2, v2 = na.node_xv(details.node.blocks, node_ids_ptr[ct_index][2])
                f0, f1, f2 = elastic_bending_forces(x0, x1, x2, rest_angle_ptr[ct_index], stiffness_ptr[ct_index], (True, True, True))
                force_ptr[ct_index][0] = f0
                force_ptr[ct_index][1] = f1
                force_ptr[ct_index][2] = f2

    @classmethod
    def compute_jacobians(cls, blocks_iterator, scene : Scene, details) -> None:
        '''
        Add the force jacobian functions to the datablock
        '''
        for ct_block in blocks_iterator:
            node_ids_ptr = ct_block['node_IDs']
            rest_angle_ptr = ct_block['rest_angle']
            stiffness_ptr = ct_block['stiffness']
            dfdx_ptr = ct_block['dfdx']
            block_n_elements = ct_block['blockInfo_numElements']

            for ct_index in range(block_n_elements):
                x0, v0 = na.node_xv(details.node.blocks, node_ids_ptr[ct_index][0])
                x1, v1 = na.node_xv(details.node.blocks, node_ids_ptr[ct_index][1])
                x2, v2 = na.node_xv(details.node.blocks, node_ids_ptr[ct_index][2])
                dfdx = elastic_bending_numerical_jacobians(x0, x1, x2, rest_angle_ptr[ct_index], stiffness_ptr[ct_index])
                dfdx_ptr[ct_index][0][0] = dfdx[0]
                dfdx_ptr[ct_index][1][1] = dfdx[1]
                dfdx_ptr[ct_index][2][2] = dfdx[2]
                dfdx_ptr[ct_index][0][1] = dfdx_ptr[ct_index][1][0] = dfdx[3]
                dfdx_ptr[ct_index][0][2] = dfdx_ptr[ct_index][2][0] = dfdx[4]
                dfdx_ptr[ct_index][1][2] = dfdx_ptr[ct_index][2][1] = dfdx[5]

'''
 Utility Functions
'''
@njit
def elastic_bending_energy(x0, x1, x2, rest_angle, stiffness):
    angle = math2D.angle(x0, x1, x2)
    arc_length = (math2D.norm(x1 - x0) + math2D.norm(x2 - x1)) * 0.5
    return 0.5 * stiffness * ((angle - rest_angle)**2) * arc_length

@njit
def elastic_bending_forces(x0, x1, x2, rest_angle, stiffness, enable_force = (True, True, True)):
    forces = np.zeros((3, 2))

    u = x0 - x1
    v = x1 - x2
    det = u[0]*v[1] - v[0]*u[1]
    dot = u[0]*v[0] + u[1]*v[1]

    norm_u = math.sqrt(u[0]**2 + u[1]**2)
    norm_v = math.sqrt(v[0]**2 + v[1]**2)

    diff_angle = rest_angle - math.atan2(det, dot)

    if enable_force[0] or enable_force[1]:
        forces[0][0] = v[0]*det - v[1]*dot
        forces[0][1] = v[0]*dot + v[1]*det

        forces[0] *= 0.5*(norm_u + norm_v)/(dot**2 + det**2)
        forces[0] += 0.25*u*diff_angle/norm_u

        forces[0] *= stiffness*diff_angle*-1.0

    if enable_force[2] or enable_force[1]:
        forces[2][0] = -(u[0]*det + u[1]*dot)
        forces[2][1] = u[0]*dot - u[1]*det

        forces[2] *= 0.5*(norm_u + norm_v)/(dot**2 + det**2)
        forces[2] += -0.25*v*diff_angle/norm_v

        forces[2] *= stiffness*diff_angle*-1.0

    if enable_force[1]:
        forces[1] -= (forces[0] + forces[2])

    return forces

@njit
def elastic_bending_numerical_jacobians(x0, x1, x2, rest_angle, stiffness):
    '''
    Returns the six jacobians matrices in the following order
    df0dx0, df1dx1, df2dx2, df0dx1, df0dx2, df1dx2
    dfdx01 is the derivative of f0 relative to x1
    etc.
    '''
    jacobians = np.zeros(shape=(6, 2, 2))
    STENCIL_SIZE = 1e-6

    # derivate of f0 relative to x0
    for g_id in range(2):
        x0_ = math2D.copy(x0)
        x0_[g_id] = x0[g_id]+STENCIL_SIZE
        forces = elastic_bending_forces(x0_, x1, x2, rest_angle, stiffness, (True, False, False))
        grad_f0_x0 = forces[0]
        x0_[g_id] = x0[g_id]-STENCIL_SIZE
        forces = elastic_bending_forces(x0_, x1, x2, rest_angle, stiffness, (True, False, False))
        grad_f0_x0 -= forces[0]
        grad_f0_x0 /= (2.0 * STENCIL_SIZE)
        jacobians[0, 0:2, g_id] = grad_f0_x0

    # derivate of f0, f1 relative to x1
    for g_id in range(2):
        x1_ = math2D.copy(x1)
        x1_[g_id] = x1[g_id]+STENCIL_SIZE
        forces = elastic_bending_forces(x0, x1_, x2, rest_angle, stiffness, (True, True, False))
        grad_f0_x1 = forces[0]
        grad_f1_x1 = forces[1]
        x1_[g_id] = x1[g_id]-STENCIL_SIZE
        forces = elastic_bending_forces(x0, x1_, x2, rest_angle, stiffness, (True, True, False))
        grad_f0_x1 -= forces[0]
        grad_f1_x1 -= forces[1]
        jacobians[1, 0:2, g_id] = grad_f1_x1 / (2.0 * STENCIL_SIZE)
        jacobians[3, 0:2, g_id] = grad_f0_x1 / (2.0 * STENCIL_SIZE)

    # derivate of f0, f1, f2 relative to x2
    for g_id in range(2):
        x2_ = math2D.copy(x2)
        x2_[g_id] = x2[g_id]+STENCIL_SIZE
        forces = elastic_bending_forces(x0, x1, x2_, rest_angle, stiffness, (True, True, True))
        grad_f0_x2 = forces[0]
        grad_f1_x2 = forces[1]
        grad_f2_x2 = forces[2]
        x2_[g_id] = x2[g_id]-STENCIL_SIZE
        forces = elastic_bending_forces(x0, x1, x2_, rest_angle, stiffness, (True, True, True))
        grad_f0_x2 -= forces[0]
        grad_f1_x2 -= forces[1]
        grad_f2_x2 -= forces[2]
        jacobians[4, 0:2, g_id] = grad_f0_x2 / (2.0 * STENCIL_SIZE)
        jacobians[5, 0:2, g_id] = grad_f1_x2 / (2.0 * STENCIL_SIZE)
        jacobians[2, 0:2, g_id] = grad_f2_x2 / (2.0 * STENCIL_SIZE)

    return jacobians
