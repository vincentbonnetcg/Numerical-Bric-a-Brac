"""
@author: Vincent Bonnet
@description : main
"""

import objects as obj
import render as rd
import solvers as sl
import profiler as profiler
import scene as sc

'''
 Global Constants
'''
WIRE_ROOT_POS = [0., -1.] # in meters
WIRE_LENGTH = 2.0 # in meters
WIRE_NUM_SEGMENTS = 4

BEAM_POS = [-4.0, 0.0] # in meters
BEAM_WIDTH = 8.0 # in meters
BEAM_HEIGHT = 1.0 # in meters
BEAM_CELL_X = 6 # number of cells along x
BEAM_CELL_Y = 3 # number of cells along y

STIFFNESS = 1.0 # in newtons per meter (N/m)
DAMPING = 0.0
PARTICLE_MASS = 0.001 # in Kg

GRAVITY = (0.0, -9.81) # in meters per second^2
NUM_FRAME = 100;
FRAME_TIMESTEP = 1.0/24.0 # in seconds
NUM_SUBSTEP = 4 # number of substep per frame

RENDER_FOLDER_PATH = "" # specify a folder to export png files
# Used command  "magick -loop 0 -delay 4 *.png out.gif"  to convert from png to animated gif

'''
 Execute
'''
# Create dynamic object and solver
wire = obj.Wire(WIRE_ROOT_POS, WIRE_LENGTH, WIRE_NUM_SEGMENTS, PARTICLE_MASS, STIFFNESS, DAMPING)
beam = obj.Beam(BEAM_POS, BEAM_WIDTH, BEAM_HEIGHT, BEAM_CELL_X, BEAM_CELL_Y, PARTICLE_MASS, STIFFNESS, DAMPING)

# Scene
scene = sc.Scene(GRAVITY)
scene.addObject(wire)
scene.addObject(beam)

#solver = sl.SemiImplicitSolver(GRAVITY, FRAME_TIMESTEP / NUM_SUBSTEP, NUM_SUBSTEP) #- only debugging - unstable with beam
solver = sl.ImplicitSolver(FRAME_TIMESTEP / NUM_SUBSTEP, NUM_SUBSTEP)

# Run simulation and render
render = rd.Render()
render.setRenderFolderPath(RENDER_FOLDER_PATH)

profiler = profiler.ProfilerSingleton()
for frameId in range(1, NUM_FRAME+1):
    profiler.clearLogs()
    
    solver.solveFrame(scene)

    print("")
    render.showCurrentFrame(scene, frameId)
    render.exportCurrentFrame(str(frameId).zfill(4) + " .png")
    
    profiler.printLogs()
