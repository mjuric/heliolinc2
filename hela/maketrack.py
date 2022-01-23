#!/usr/bin/env python

import hela

REAL='<f16'

import numpy as np
struct = dict(names=['MJD', 'RA', 'Dec', 'x', 'y', 'z', 'idstring', 'index'], formats=[REAL, REAL, REAL, REAL, REAL, REAL, 'S20', '<i8'])

def load_obsv(fn):
    intype = np.dtype(list(dict(
        name='S20',	# S1000007a
        MJD=REAL,	# 59913.338779
        ra=REAL,	# 145.30337600000001
        dec=REAL,	# -15.730053
    ).items()))

    data = np.loadtxt(fn, usecols=[0, 2, 5, 7], dtype=intype, delimiter=',', skiprows=1)

    arr = np.zeros(len(data), dtype=struct)
    arr["idstring"] = data["name"]
    arr["MJD"] = data["MJD"]
    arr["RA"] = data["ra"]
    arr["Dec"] = data["dec"]
    arr["index"] = -2 - np.arange(len(arr))

    return arr

data = load_obsv("../tests/sample.csv")
hela.dp(data)

args = ["./maketrack03a", "-dets", "../tests/sample.csv", "-earth", "../tests/Earth2hr2020s_01a.txt"]
hela.maketrack03a(args)
exit(0)
