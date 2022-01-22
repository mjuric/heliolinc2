#!/usr/bin/env python

import hela

args = ["./maketrack03a", "-dets", "../tests/sample.csv", "-earth", "../tests/Earth2hr2020s_01a.txt"]

#hela.maketrack03a(args)

import numpy as np
struct = dict(names=['MJD', 'RA', 'Dec', 'x', 'y', 'z', 'idstring', 'index'], formats=['<f16', '<f16', '<f16', '<f16', '<f16', '<f16', 'S20', '<i8'])

#define IDCOL 1
#define MJDCOL 3
#define RACOL 6
#define DECCOL 8

intype = np.dtype(list(dict(
    name='S20', # S1000007a
    MJDidx='f8', # 37629
    MJD='f8', # 59913.338779
    epoch='f8', # 268112746.752
    a='f8', # -19.458
    ra='f8', # 145.30337600000001
    c='f8', # 0.236867
    dec='f8', # -15.730053
    e='f8', # -0.263781
    f='f8', # -156375137.693
    g='f8', # 272227481.445
    h='f8', # -18364635.669
    i='f8', # 27.914958000000002
    j='f8', # 12.29
    k='f8', # 11.884
    l='f8', # 4.12
    filter='S1', # y
    m='f8', # 10.001636306082517
    n='f8', # 10.001636306082517
    o='f8', # 0.0003224451542824411
).items()))

data = np.loadtxt("../tests/sample.csv", dtype=intype, delimiter=',', skiprows=1)
print(data[:2])

arr = np.zeros(len(data), dtype=struct)
arr["idstring"] = data["name"]
arr["MJD"] = data["MJD"]
arr["RA"] = data["ra"]
arr["Dec"] = data["dec"]

hela.dp(arr)

#np.dtype = {'names': ['MJD', 'RA', 'Dec', 'x', 'y', 'z', 'idstring', 'index'], 'formats': ['<f16', '<f16', '<f16', '<f16', '<f16', '<f16', 'S20', '<i8'], 'offsets': [0, 16, 32, 48, 64, 80, 96, 120], 'itemsize': 128}
