#!/usr/bin/python
# -*- coding: utf-8 -*-
''' Phase Correlation based image matching and registration libraries
'''
__author__ = "Yoshi Ri"
__copyright__ = "Copyright 2017, The University of Tokyo"
__credits__ = ["Yoshi Ri"]
__license__ = "BSD"
__version__ = "1.0.1"
__maintainer__ = "Yoshi Ri"
__email__ = "yoshiyoshidetteiu@gmail.com"
__status__ = "Production"

# Phase Correlation to Estimate Pose
import cv2
import numpy as np
import matplotlib.pyplot as plt # matplotlibの描画系
import math
from PhaseCorrelation import *
from WarpFunction import *

def POC(a,b):
    imshowflag = 1 # show the processing image
    a = a.astype(np.float32)
    b = b.astype(np.float32)
    height,width = a.shape
    hann = cv2.createHanningWindow((height, width),cv2.CV_64F)
    # rhann = np.sqrt(hann)
    
    # Windowing and FFT
    G_a = np.fft.fft2(a*hann)
    G_b = np.fft.fft2(b*hann)


    # 1. Get Rotation and Scaling Error
    # 1.1: Frequency Whitening  
    LA = np.fft.fftshift(np.log(np.absolute(G_a)+1))
    LB = np.fft.fftshift(np.log(np.absolute(G_b)+1))
    # 1.2: Log polar
    cx = width / 2
    cy = height / 2
    Mag = width/math.log(width)
    LPA = cv2.logPolar(LA, (cy, cx), Mag, cv2.INTER_LINEAR)
    LPB = cv2.logPolar(LB, (cy, cx), Mag, cv2.INTER_LINEAR)
    
    # 1.3: Filtering
    # --------------- Tuning parameter ----------------
    lpmin_tuning = 0.5   # default 0.5
    lpmax_tuning = 0.8   # default 0.8
    # -------------------------------------------------
    LPmin = math.floor(Mag*math.log(lpmin_tuning*width/2.0/math.pi))
    LPmax = min(width, math.floor(Mag*math.log(width*lpmax_tuning/2)))
    assert LPmax > LPmin, 'Invalid condition!\n Enlarge lpmax tuning parameter or lpmin_tuning parameter'
    Tile = np.repeat([0.0,1.0,0.0],[LPmin-1,LPmax-LPmin+1,width-LPmax])
    Mask = np.tile(Tile,[height,1])
    LPA_filt = LPA*Mask
    LPB_filt = LPB*Mask

    # 1.4: Phase Correlate to Get Rotation and Scaling
    Diff,peak = PhaseCorrelation(LPA_filt,LPB_filt)
    # Do not use "cv2.phaseCorrelate(LPA_filt,LPB_filt)" because the 2nd order fitting process is not suitable for this fucntion.
    
    #  Final output of scale and rotation
    theta1 = 360 * Diff[1] / height; # deg
    theta2 = theta1 + 180; # deg theta ambiguity
    #invscale = math.pow(float(width),Diff[0]/float(width))
    invscale = math.exp(Diff[0]/Mag)
    # print('Theta? ',-theta1,'Scale ',1/invscale)
    
    # 2.1: Correct rotation and scaling
    b1 = Warp_4dof(b,0,0,theta1*math.pi/180,invscale)
    b2 = Warp_4dof(b,0,0,theta2*math.pi/180,invscale)
    
    # 2.2 : Translation estimation
    diff1, peak1 = cv2.phaseCorrelate(a,b1)     #diff1, peak1 = PhaseCorrelation(a,b1)
    diff2, peak2 = cv2.phaseCorrelate(a,b2)     #diff2, peak2 = PhaseCorrelation(a,b2)
    # Use cv2.phaseCorrelate(a,b1) because it is much faster

    # 2.3: Compare peaks and choose true rotational error
    if peak1 > peak2:
        Trans = diff1
        peak = peak1
        theta = -theta1
    else:
        Trans = diff2
        peak = peak2
        theta = -theta2

    if theta > 180:
        theta -= 360
    elif theta < -180:
        theta += 360

    if 0:
        # Imshow
        plt.subplot(5,2,1)
        plt.imshow(LA,vmin=LA.min(), vmax=LA.max())
        plt.subplot(5,2,2)
        plt.imshow(LB,vmin=LB.min(), vmax=LB.max())
        plt.subplot(5,2,3)
        plt.imshow(LPA,vmin=LPA.min(), vmax=LPA.max(),cmap="gray")
        plt.subplot(5,2,4)
        plt.imshow(LPB, vmin=LPB.min(), vmax=LPB.max(),cmap="gray")
        plt.subplot(5,2,5)
        plt.imshow(LPA_filt,vmin=LPA_filt.min(), vmax=LPA_filt.max(),cmap="gray")
        plt.subplot(5,2,6)
        plt.imshow(LPB_filt, vmin=LPB_filt.min(), vmax=LPB_filt.max(),cmap="gray")
        plt.subplot(5,2,7)
        plt.imshow(b1,vmin=b1.min(), vmax=b1.max(),cmap="gray")
        plt.subplot(5,2,8)
        plt.imshow(b2, vmin=b2.min(), vmax=b2.max(),cmap="gray")

    return [Trans[0],Trans[1],theta,1/invscale] , peak