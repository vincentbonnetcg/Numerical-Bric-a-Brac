"""
@author: Vincent Bonnet
@description : multivariable optimizations - gradient descent
"""

import convexFunctions
import nonConvexFunctions
import render
import optimizer
import linesearch

def main():
    # optimizer and linesearch settings
    linesearch.SCALE_STEP = 0.1
    optimizer.LINE_SEARCH_ALGO = linesearch.backtracking
    # Termination condition
    optimizer.MAX_ITERATIONS = 200
    optimizer.THRESHOLD = 1e-04

    # Multivariable non-convex functions
    render.draw2D(nonConvexFunctions.trigonometry2D, optimizer.GradientDescent)
    render.draw2D(nonConvexFunctions.trigonometry2D, optimizer.NewtonRaphson)
    render.draw2D(nonConvexFunctions.trigonometry2D, optimizer.QuasiNewtonRaphson_BFGS)

    # Multivariable convex functions
    #render.draw2D(convexFunctions.BohachevskyN1, optimizer.GradientDescent)
    #render.draw2D(convexFunctions.BohachevskyN1, optimizer.NewtonRaphson)
    #render.draw2D(convexFunctions.BohachevskyN1, optimizer.QuasiNewtonRaphson_BFGS)
    render.draw2D(convexFunctions.McCormick, optimizer.GradientDescent)
    render.draw2D(convexFunctions.McCormick, optimizer.NewtonRaphson)
    render.draw2D(convexFunctions.McCormick, optimizer.QuasiNewtonRaphson_BFGS)
    render.draw2D(convexFunctions.Booth, optimizer.GradientDescent)
    render.draw2D(convexFunctions.Booth, optimizer.NewtonRaphson)
    render.draw2D(convexFunctions.Booth, optimizer.QuasiNewtonRaphson_BFGS)

if __name__ == '__main__':
    main()
