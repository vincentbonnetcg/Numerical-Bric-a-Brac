"""
@author: Vincent Bonnet
@description : basic render routines
"""

import time
import math
import random
import numba
import numpy as np
from . import core as jit_core
from .maths import dot, copy, axpy, gamma_correction, clamp
from . import intersect

# pathtracer settings
BLACK = np.zeros(3)
MAX_DEPTH = 1 # max hit
NUM_SAMPLES = 1 # number of sample per pixel
RANDOM_SEED = 10
INV_PDF = 2.0 * math.pi; # inverse of probability density function
INV_PI = 1.0 / math.pi

@numba.njit(inline='always')
def update_ray_from_uniform_distribution(mempool):
    i = mempool.depth
    copy(mempool.ray_o, mempool.hit_p[i])
    # Find ray direction from uniform around hemisphere
    # Unit hemisphere from spherical coordinates
    # the unit  hemisphere is at origin and y is the up vector
    # theta [0, 2*PI) and phi [0, PI/2]
    # px = cos(theta)*sin(phi)
    # py = sin(theta)*sin(phi)
    # pz = cos(phi)
    # A uniform distribution (avoid more samples at the pole)
    # theta = 2*PI*rand()
    # phi = acos(rand())  not phi = PI/2*rand() !
    # Optimization
    # cos(phi) = cos(acos(rand())) = rand()
    # sin(phi) = sin(acos(rand())) = sqrt(1 - rand()^2)
    theta = 2*math.pi*random.random()
    cos_phi = random.random()
    sin_phi = math.sqrt(1.0 - cos_phi**2)
    v0 = math.cos(theta)*sin_phi
    v1 = cos_phi
    v2 = math.sin(theta)*sin_phi
    # compute the world sample
    mempool.ray_d[0] = v0*mempool.hit_bn[i][0] + v1*mempool.hit_n[i][0] + v2*mempool.hit_tn[i][0]
    mempool.ray_d[1] = v0*mempool.hit_bn[i][1] + v1*mempool.hit_n[i][1] + v2*mempool.hit_tn[i][1]
    mempool.ray_d[2] = v0*mempool.hit_bn[i][2] + v1*mempool.hit_n[i][2] + v2*mempool.hit_tn[i][2]

@numba.njit
def ray_tri_details(details, mempool):
    # details from Scene.tri_details()
    skip_face_id = -1
    if mempool.depth >= 0: # skip face based on previous hit
        skip_face_id = mempool.hit_face_id[mempool.depth]
    mempool.next_hit() # use the next allocated hit
    min_t = np.finfo(numba.float64).max
    data = details[0]
    tri_vertices = data.tri_vertices
    hit_id = -1
    # intersection test with triangles
    num_triangles = len(tri_vertices)
    for i in range(num_triangles):
        if i == skip_face_id:
            continue
        t = intersect.ray_triangle(mempool, tri_vertices[i])
        mempool.total_intersection += 1
        if t > 0.0 and t < min_t:
            min_t = t
            hit_id = i

    if hit_id >= 0:
        i = mempool.depth
        mempool.hit_t[i] = min_t
        axpy(min_t, mempool.ray_d, mempool.ray_o, mempool.hit_p[i])
        copy(mempool.hit_n[i], data.tri_normals[hit_id])
        copy(mempool.hit_tn[i], data.tri_tangents[hit_id])
        copy(mempool.hit_bn[i], data.tri_binormals[hit_id])
        mempool.hit_face_id[i] = hit_id
        copy(mempool.hit_material[i], data.tri_materials[hit_id])
        mempool.hit_materialtype[i] = data.tri_materialtype[hit_id]

        # two-sided intersection
        if dot(mempool.ray_d, mempool.hit_n[i]) > 0:
            mempool.hit_n[i][0] *= -1
            mempool.hit_n[i][1] *= -1
            mempool.hit_n[i][2] *= -1

@numba.njit
def recursive_trace(details, mempool):
    if mempool.depth + 1 >= MAX_DEPTH: # can another hit be allocated ?
        copy(mempool.result, BLACK)
        return

    ray_tri_details(details, mempool)
    if not mempool.valid_hit():
        copy(mempool.result, BLACK)
        return

    depth = mempool.depth

    if mempool.hit_materialtype[depth]==1: # light
        mempool.result *= mempool.hit_material[depth]
        return

    # update ray and compute weakening factor
    update_ray_from_uniform_distribution(mempool)
    weakening_factor = dot(mempool.ray_d, mempool.hit_n[depth])

    # rendering equation : emittance + (BRDF * incoming * cos_theta / pdf);
    mempool.result *= mempool.hit_material[depth]
    mempool.result *= INV_PI * weakening_factor * INV_PDF
    recursive_trace(details, mempool)

@numba.njit
def first_trace(details, mempool):
    if MAX_DEPTH == 0 or mempool.hit_materialtype[0]==1:
        copy(mempool.result, mempool.hit_material[0])
        return

    mempool.depth = 0
    mempool.result[0:3] = 0.0

    # update ray and compute weakening factor
    update_ray_from_uniform_distribution(mempool)
    weakening_factor = dot(mempool.ray_d, mempool.hit_n[0])

    # rendering equation : emittance + (BRDF * incoming * cos_theta / pdf);
    copy(mempool.result, mempool.hit_material[0])
    mempool.result *= INV_PI * weakening_factor * INV_PDF
    recursive_trace(details, mempool)


@numba.njit
def render(image, camera, details, start_time):
    mempool = jit_core.MemoryPool(NUM_SAMPLES)
    random.seed(RANDOM_SEED)
    for j in range(camera.height):
        for i in range(camera.width):
            # compute first hit to the scene
            camera.get_ray(i, j, mempool)
            ray_tri_details(details, mempool)

            if mempool.valid_hit() == False:
                continue

            # compute shade
            jj = camera.height-1-j
            ii = camera.width-1-i
            for _ in range(NUM_SAMPLES):
                first_trace(details, mempool)
                image[jj, ii] += mempool.result
            image[jj, ii] /= NUM_SAMPLES

            gamma_correction(image[jj, ii])

        '''
        with numba.objmode():
            p = (j+1) / camera.height
            print('. completed : %.2f' % (p * 100.0), ' %')
            if time.time() != start_time:
                t = time.time() - start_time
                estimated_time_left = (1.0 - p) / p * t
                print('    estimated time left: %.2f sec' % estimated_time_left)
        '''

    print('Total intersections ', mempool.total_intersection)
