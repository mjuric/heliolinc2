#!/usr/bin/env python

import hela

REAL='<f16'

import numpy as np
def load_obsv(fn):
    intype = np.dtype(list(dict(
        idstring='S20',	# S1000007a
        MJD=REAL,	# 59913.338779
        RA=REAL,	# 145.30337600000001
        Dec=REAL,	# -15.730053
    ).items()))

    data = np.loadtxt(fn, usecols=[0, 2, 5, 7], dtype=intype, delimiter=',', skiprows=1)
    return data

data = load_obsv("../tests/sample.csv")
#hela.dp(data)
#print(data[0])
#exit(0)

args = ["./maketrack03a", "-dets", "../tests/sample.csv", "-earth", "../tests/Earth2hr2020s_01a.txt"]
hela.maketrack03a(args, data)
exit(0)
