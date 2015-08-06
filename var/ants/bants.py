#!/usr/bin/env python3
import pickle
import math
import sys
import cv2
import numpy as np
from PIL import Image, ImageSequence
from vector import Vector

#########################
#### image functions ####
#########################

def pil2cv(pil):
    return np.array(pil.convert("RGB"))[:,:,::-1]

def cv2pil(cv):
    return Image.fromarray(cv2.cvtColor(cv, cv2.COLOR_BGR2RGB))

class GIF(object):
    def __init__(self, path):
        im = Image.open(path)
        self.width, self.height = im.size
        self.dur = im.info['duration']
        self.frames = [frame.copy() for frame in ImageSequence.Iterator(im)]

    def pil(self, i):
        return self.frames[i].copy()

    def cv(self, i):
        return np.array(self.frames[i].convert("RGB"))[:,:,::-1]

    def __len__(self):
        return len(self.frames)

class Frame(object):
    def __init__(self, cv):
        self.im = cv2.cvtColor(cv, cv2.COLOR_BGR2GRAY)
        xs, ys = (self.im == 0).nonzero()
        self.coords = [Vector(x, y) for x,y in zip(list(xs), list(ys))]

########################
#### vector algebra ####
########################

def distance2(a, b, w, h):
    ax, ay = a
    bx, by = b
    dx = min(abs(bx - ax - w), abs(bx - ax), abs(bx - ax + w))
    dy = min(abs(by - ay - h), abs(by - ay), abs(by - ay + h))
    return dx*dx + dy*dy

def nearest(p, qs, w, h, maxr=10, maxn=20):
    return sorted(
        [q for q in qs if distance2(p, q, w, h) < maxr * maxr],
        key = lambda q: distance2(p, q, w, h)
    )[:maxn]

class Trajectory(object):
    comp = -1
    def __init__(self, a, b, dt):
        self.origin = a
        self.terminus = b
        self.dt = dt

    def velocity(self, w, h):
        ax, ay = self.origin
        bx, by = self.terminus
        dx = sorted([bx - ax - w, bx - ax, bx - ax + w], key=abs)[0]
        dy = sorted([by - ay - h, by - ay, by - ay + h], key=abs)[0]
        return Vector(dx, dy) / (self.dt + Trajectory.comp)

    def extrapolate(self, t, w, h):
        x, y = self.origin + t * self.velocity(w, h)
        return Vector(int(x)%w, int(y)%h)

##########################
#### image processing ####
##########################

def prune(path, leaf, w, h):
    trajectory = Trajectory(path[0], leaf, len(path))
    return not all(
            abs(trajectory.extrapolate(t, w, h) - path[t]) < 2
            for t in range(1, len(path)))

# expects paths[][0] to be from t=0
def grow_prunes(paths, frames, w, h, limit):
    limit = min(limit, len(frames))
    maxr = min(w,h)/2-20

    if not len(paths):
        print(".", end="")
        sys.stdout.flush()
        return []

    paths_harvest = []
    paths_seed = []

    for path in paths:
        length = distance2(path[0], path[-1], w, h)
        if len(path) >= limit or length > maxr * maxr:
            paths_harvest.append(path)
        else:
            stock = frames[len(path)].coords
            for leaf in nearest(path[-1], stock, w, h):
                if not prune(path, leaf, w, h):
                    paths_seed.append(path + [leaf])

    return paths_harvest + grow_prunes(paths_seed, frames, w, h, limit)

def grow_unique(origin, frames, w, h, limit=25):
    prunes = grow_prunes([[origin]], frames, w, h, limit)
    harvest = set((prune[-1], len(prune)) for prune in prunes)
    return [Trajectory(origin, leaf, t) for leaf,t in harvest]

##############
#### main ####
##############

if __name__ == "__main__":
    import os
    from optparse import OptionParser
    from multiprocessing import Pool

    # raw data
    ants = GIF('ants.gif')
    frames = [Frame(pil2cv(frame)) for frame in ants.frames]

    # cli options
    parser = OptionParser()
    parser.add_option("-r", "--rebuild", action="store_true", default=False,
            dest="reload", help="rebuild cache of trajectories")
    parser.add_option("-l", action="store", type="int", default=25,
            dest="limit", help="set the iteration limit (default 25)")
    parser.add_option("-i", "--interactive", action="store_true", default=False,
            dest="interactive", help="control the bants interactively")
    parser.add_option("-o", action="store", dest="file", help="save frames to a gif")
    parser.add_option("-b", action="store", default=100, dest="start", help="first frame to save")
    parser.add_option("-e", action="store", default=-300, dest="end", help="last frame to save")
    opts, _ = parser.parse_args()

    # get trajectories
    cache = 'cache.p'
    if opts.reload or not os.path.isfile(cache):
        limit = opts.limit
        def worker(origin):
            return grow_unique(origin, frames, ants.width, ants.height, limit=limit)
        nest = Pool(4).map(worker, frames[0].coords)
        trajectories = [traj for trajs in nest for traj in trajs]
        with open(cache, "wb") as cache_fd:
            pickle.dump(trajectories, cache_fd)
    else:
        with open(cache, "rb") as cache_fd:
            trajectories = pickle.load(cache_fd)

    # rendering
    def render(ants, trajectories, t):
        if 0 <= t < len(ants):
            im = ants.cv(t)
            im[:,:,0]=255
            for trajectory in trajectories:
                x, y = trajectory.extrapolate(t, ants.width, ants.height)
                im[x,y] = [0,0,255] if im[x,y,2] else [0,255,0]
        else:
            im = np.full((ants.width, ants.height, 3), 255, dtype=np.uint8)
            for trajectory in trajectories:
                x, y = trajectory.extrapolate(t, ants.width, ants.height)
                im[x,y,:] = 0

        return im

    # save gif
    if opts.file:
        import tempfile
        import subprocess

        dir = tempfile.mkdtemp()
        gif = opts.file
        start = opts.start
        end = opts.end
        sign = 1 if end - start >= 0 else -1

        frames = [cv2pil(render(ants, trajectories, t)) for t in range(start, end, sign)]
        fnames = []
        for i in range(len(frames)):
            fname = "%s/frame%07d.png" % (dir, i)
            frames[i].save(fname)
            fnames.append(fname)

        try:
            subprocess.call(["convert", "-delay", "10", "-loop", "0"]  + fnames + [gif])
        except:
            print("Failed to generate gif! Do you have convert installed?")
            print("Individual frames have been saved as .pngs to %s" % dir)
            print()


    # gui
    if opts.interactive:
        cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
        t = 0
        print("<< H < h | q | l > L >>");
        print("    [[ j | Δ | k ]]")
        while True:
            print("t = %+ 3d  Δ=%+2.1f" % (t, Trajectory.comp), end='\r')
            cv2.imshow('frame', render(ants, trajectories, t))
            k = cv2.waitKey(0) & 0xff

            if k == ord('h'):
                t -= 1
            elif k == ord('H'):
                t -= 20
            elif k == ord('l'):
                t += 1
            elif k == ord('L'):
                t += 20
            elif k == ord('j'):
                Trajectory.comp -= 0.2
            elif k == ord('k'):
                Trajectory.comp += 0.2
            elif k == ord('q'):
                break

        cv2.destroyAllWindows()
        print()

