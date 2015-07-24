#!/usr/bin/env python2
import hw
from math import ceil
from time import time, sleep
from threading import Thread

class Image(object):
    def __init__(self, rectangle, data, stamp=None):
        if stamp is None:
            stamp = time()
        self.rectangle = rectangle
        self.data = data
        self.stamp = stamp

    def resolution(self):
        dim_meter = max(self.rectangle.width, self.rectangle.height)
        dim_pixel = max(self.data.cols,       self.data.rows)
        return dim_meter / dim_pixel

    def from_bench(self, point):
        x, y = self.rectangle.from_bench(point)
        return Vector(
                int(x * self.data.cols / self.rectangle.width),
                int(y * self.data.rows / self.rectangle.height))

    def to_bench(self, coord):
        x, y = coord
        return self.rectangle.to_bench(Vector(
            x * self.rectangle.width / self.data.cols,
            y * self.rectangle.height / self.data.rows))


class Canvas(object):
    def __init__(self, workspace, camera, polygon, min_precision, max_age, min_stitch):
        """max_age in seconds, but up to microsec resolution"""
        try:
            precision, camera = sorted(h for h in map(
                lambda head: (head.precision(), head) if isinstance(head, hw.Camera) else None,
                workspace.apparati) if h is not None)[0]
        except IndexError:
            raise hw.HardwareException("No cameras installed!!!!!!")

        if precision > min_precision:
            print("Warning, camera used for canvas of insufficient resolution -- camera has" +
                    "resolution %fm but a resolution of %fm was requested" % (precision, min_precision))

        self.backend = workspace, camera
        self.max_age = max_age
        self.min_stitch = min_stitch
        self.polygon = polygon
        self.images = self.generate_rects()
        self.thread = Thread(target = self.worker)
        self.thread.daemon = True
        self.thread.start()

    def generate_rects(self):
        _, camera = self.backend
        stitch = self.min_stitch
        prec = camera.precision()
        width, height = camera.resolution()
        wid = width - 2*stitch
        hei = height - 2*stitch

        bounding = self.polygon.rectangle(camera.orientation())
        cols = int(ceil(bounding.width / (wid * prec)))
        rows = int(ceil(bounding.height / (hei * prec)))

        return [i for s in [[((i,j), Rectangle(Vector(j*wid-stitch, i*hei-stitch), 0, width, height), None)
            for j in reversed(range(cols)) if i%2 else range(cols)] for i in range(rows)] for i in s]

    def worker(self):
        while True:
            expiry = self.max_age
            for (i, j), rect, image in self.images:
                if image is None or time() - image.stamp >= expiry:
                    cb = lambda image: self.update(i, j, image)
                    # queue image replacement
                    time.sleep(2)
                    pass

    def update(self, i, j, image):
        def replace(el):
            (a, b), rect, _ = el
            return ((i,j), rect, image) if (a,b)==(i,j) else el
        self.images = [replace(el) for el in self.images] #atomicity

    def status(self):
        expiry = self.max_age
        return all(image is not None and time() - image.stamp < expiry for _,_,image in self.images)

