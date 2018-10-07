"""
@author: Vincent Bonnet
@description : Routine to display objects and constraints
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from tools import profiler

class Render:

    def __init__(self):
        self.fig = plt.figure()
        self.font = {'family': 'serif',
                     'color':  'darkred',
                     'weight': 'normal',
                     'size': 12}
        self.renderFolderPath = ""
        self.ax = None

    # Set where to save the files
    def setRenderFolderPath(self, path):
        self.renderFolderPath = path

    # Render in the current figure
    def _render(self, scene, frameId):
        # Reset figure and create subplot
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)
        self.ax.axis('equal')
        self.ax.set_xlim(-3.5, 3.5)
        self.ax.set_ylim(-3.5, 3.5)

        # Set label
        plt.title('Implicit Solver - frame ' + str(frameId), fontdict=self.font)
        plt.xlabel('x (m)')
        plt.ylabel('y (m)')

        # Draw objects constraints
        for dynamic in scene.dynamics:
            for constraint in dynamic.internal_constraints:
                ids = constraint.localIds
                if len(ids) >= 2:
                    linedata = []
                    for pid in ids:
                        linedata.append(dynamic.x[pid])
                    x, y = zip(*linedata)
                    self.ax.plot(x, y, dynamic.render_prefs[2], lw=dynamic.render_prefs[3])

        # Draw particles
        for dynamic in scene.dynamics:
            x, y = zip(*dynamic.x)
            self.ax.plot(x, y, dynamic.render_prefs[0], markersize=dynamic.render_prefs[1])

        # Draw kinematics
        for kinematic in scene.kinematics:
            vertices = kinematic.getWorldSpaceVertices()
            polygon  = patches.Polygon(vertices, facecolor='orange', alpha=0.8)
            self.ax.add_patch(polygon)

    # Draw and display single frame
    @profiler.timeit
    def showCurrentFrame(self, scene, frameId):
        #self.fig = plt.figure(figsize=(7, 4), dpi=200) # to export higher resolution images
        self.fig = plt.figure()
        self._render(scene, frameId)
        plt.show()

    # Export frame
    @profiler.timeit
    def exportCurrentFrame(self, filename):
        if len(filename) > 0 and len(self.renderFolderPath) > 0:
            self.fig.savefig(self.renderFolderPath + "/" + filename)
