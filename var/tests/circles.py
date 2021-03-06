#!/usr/bin/env
from hw.shapeoko import Shapeoko, Axes
from lib.vector import Vector
from math import pi
import time
import glob

if __name__ == '__main__':
    """very simple circle drawing test (should instead use
       G2/G3 to draw arcs); connects to the first serial
       port it finds, calibrates it and then moves in a
       full circle with 1deg resolution"""

    com = glob.glob('/dev/ttyACM*')[0]
    print(com)
    stage = Shapeoko(com)
    time.sleep(2)
    stage.home([Axes.X, Axes.Y, Axes.Z])

    origin = Vector(100,100)
    radius = 80
    d2r = lambda deg: deg * pi / 180
    move = lambda v: stage.move([v.x(), v.y(), None])

    move(origin)
    for deg in range(0, 360, 1):
        point = origin + Vector.from_polar(radius, d2r(deg))
        move(point)

    stage.close()

