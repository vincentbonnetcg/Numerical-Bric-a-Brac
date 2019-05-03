"""
@author: Vincent Bonnet
@description : a scene contains objects/constraints/kinematics
The scene stores data in SI unit which are used by the solver
"""

import itertools

class Scene:
    def __init__(self):
        self.dynamics = [] # dynamic objects
        self.kinematics = [] # kinematic objects
        self.animators = [] # animators for kinematic objects
        self.conditions = [] # create static or dynamic constraints
        self.forces = []

    # Data Functions #
    def add_dynamic(self, dynamic):
        index = (len(self.dynamics))
        offset = 0
        for i in range(index):
            offset += self.dynamics[i].num_particles

        dynamic.set_indexing(index, offset)
        self.dynamics.append(dynamic)

    def add_kinematic(self, kinematic, animator = None):
        kinematic.set_indexing(index = (len(self.kinematics)))
        self.kinematics.append(kinematic)
        self.animators.append(animator)

    def update_kinematics(self, time, dt = 0.0):
        for index, kinematic in enumerate(self.kinematics):
            animation = self.animators[index]
            if animation:
                position, rotation = animation.get_value(time)
                kinematic.state.update(position, rotation, dt)

    def num_particles(self):
        num_particles = 0
        for dynamic in self.dynamics:
            num_particles += dynamic.num_particles
        return num_particles

    # Constraint Functions #
    def add_condition(self, condition):
        self.conditions.append(condition)

    def update_conditions(self, static = True):
        for condition in self.conditions:
            if condition.is_static() is static:
                condition.update_constraints(self)

    def get_constraints_iterator(self):
        values = []
        for condition in self.conditions:
            values.append(condition.constraints)

        return itertools.chain.from_iterable(values)

    # Force Functions #
    def add_force(self, force):
        self.forces.append(force)

    # Compute node identifier and retrieve node state
    # TODO : In the future, those functions will live in another class when
    # dynamics no longer have their own storage
    # n_state and n_add_f will be generalized too
    def n_id(self, object_id, node_id):
        global_node_id = self.dynamics[object_id].global_offset + node_id
        return [object_id, node_id, global_node_id]

    def n_global_index(self, n_id):
        return n_id[2]

    def n_state(self, n_id):
        dynamic = self.dynamics[n_id[0]]
        x = dynamic.x[n_id[1]]
        v = dynamic.v[n_id[1]]
        return (x, v)

    def n_add_f(self, n_id, f):
        dynamic = self.dynamics[n_id[0]]
        dynamic.f[n_id[1]] += f
