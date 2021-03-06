#!/usr/bin/env python3

import cv2
import numpy as np

def display(im):
    ih, iw = im.shape[:2]
    sh = 700
    sw = int(iw * sh / ih)
    sm = cv2.resize(im, (sw, sh))

    cv2.imshow('im', sm)
    cv2.waitKey(0)

def warpTwoImages(img1, img2, H):
    '''warp img2 to img1 with homograph H'''
    h1,w1 = img1.shape[:2]
    h2,w2 = img2.shape[:2]
    pts1 = np.float32([[0,0],[0,h1],[w1,h1],[w1,0]]).reshape(-1,1,2)
    pts2 = np.float32([[0,0],[0,h2],[w2,h2],[w2,0]]).reshape(-1,1,2)
    pts2_ = cv2.perspectiveTransform(pts2, H)
    pts = np.concatenate((pts1, pts2_), axis=0)
    [xmin, ymin] = np.int32(pts.min(axis=0).ravel() - 0.5)
    [xmax, ymax] = np.int32(pts.max(axis=0).ravel() + 0.5)
    t = [-xmin,-ymin]
    print(xmin, ymin, xmax, ymax, t)
    Ht = np.array([[1,0,t[0]],[0,1,t[1]],[0,0,1]]) # translate

    result = cv2.warpPerspective(img2, Ht.dot(H), (xmax-xmin, ymax-ymin))
    im1 = np.full((ymax-ymin, xmax-xmin), 2, dtype=np.uint8) 
    im1[t[1]:h1+t[1],t[0]:w1+t[0]] = img1
    #result[t[1]:h1+t[1],t[0]:w1+t[0]] = img1
    res = np.maximum.reduce([result, im1])
    return res
    return result

clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
im1 = cv2.imread("./tile9b/00.jpg", 0)
im2 = cv2.imread("./tile9b/01.jpg", 0)
im1 = clahe.apply(im1)
im2 = clahe.apply(im2)
display(im1)
display(im2)

#for im in ims: display(im)
#cv2.destroyAllWindows()

orb = cv2.ORB_create()
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

ik1, id1 = orb.detectAndCompute(im1, None)
ik2, id2 = orb.detectAndCompute(im2, None)

matches = bf.match(id1, id2)
matches = sorted(matches, key=lambda m:m.distance)[:15]
im3 = cv2.drawMatches(im1, ik1, im2, ik2, matches, None)
#display(im3)

dst = np.float32([ik1[m.queryIdx].pt for m in matches]).reshape(-1,1,2)
src = np.float32([ik2[m.trainIdx].pt for m in matches]).reshape(-1,1,2)
M, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
matchesMask = mask.ravel().tolist()

im4 = np.zeros((8000,8000), np.uint8)
ih, iw = im1.shape[:2]
im4[:ih, :iw] = im1
im5 = cv2.warpPerspective(im2, M, (8000,8000))
pts = np.float32([[0,0],[0,ih-1],[iw-1,ih-1],[iw-1,0]]).reshape(-1,1,2)
dsts = cv2.perspectiveTransform(pts, M)
print(pts, dsts)
print([np.int32(dsts)])
im4 = cv2.polylines(im4, [np.int32(dsts)], True, (255,0,0), 30, cv2.LINE_AA)
#display(im4)

im6 = warpTwoImages(im1, im2, M)
display(im6)

