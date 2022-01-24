#!/usr/bin/env python

import hela
import numpy as np
import argparse

REAL     = '<f16' # Floating point datatype
MAXVEL   = 1.5    # Default max angular velocity in deg/day.
MAXTIME  = 1.5    # Default max inter-image time interval
                  # for tracklets, in hours
IMAGERAD = 2.0    # radius from image center to most distant corner (deg)

def load_obsv(fn):
    """ Load the observation file, returning a numpy structured array """
    intype = np.dtype(list(dict(
        idstring='S20',	# S1000007a
        MJD=REAL,	# 59913.338779
        RA=REAL,	# 145.30337600000001
        Dec=REAL,	# -15.730053
    ).items()))

    data = np.loadtxt(fn, usecols=[0, 2, 5, 7], dtype=intype, delimiter=',', skiprows=1)
    return data

def positive_float(value):
    """ Argument parser support: convert positive nonzero float type """
    fvalue = float(value)
    if fvalue <= 0:
        raise argparse.ArgumentTypeError("%s is an invalid positive floating point value" % value)
    return fvalue

def obs_coordinates(value):
    """ Argument parser support: convert lon,cos,sin string to (lon, cos, sin) tuple """
    try:
        (obslon, plxcos, plxsin) = map(float, value.split(','))
    except Exception as e:
        raise argparse.ArgumentTypeError(f"error: {e}\nthe coordinates must be given as '<obslon>,<plxcos>,<plxsin>'.")
    return obslon, plxcos, plxsin

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some integers.')
    
    # required arguments
    parser.add_argument("--dets", "--detections", "-d", required=True, dest='indetfile', type=str, help='Detections file (CSV format)')
    parser.add_argument("--earth", "-e", required=True, dest="earthfile", type=str, help="Earth coordinates file (JPL HORIZONS format)")

    # optional arguments
    parser.add_argument("--imgs", "--images", "-i", dest="inimfile", type=str, help='Images list file (CSV)')
    parser.add_argument("--outim", "--outimages", dest="outimfile", type=str, help="Output image file")
    parser.add_argument("--pairfile", "--pairs", dest="outpairfile", type=str, default="outpairfile01.txt", help="Output pair file")
    parser.add_argument("--pairdet", dest="pairdetfile", type=str, default="pairdetfile01.txt", help="Output pair detections file")
    parser.add_argument("--imrad", dest="imrad", type=positive_float, default=IMAGERAD, help="Image radius (must be positive)")
    parser.add_argument("--maxtime", dest="maxtime", type=positive_float, default=MAXTIME, help="Maximum inter-image time interval (must be positive)")
    parser.add_argument("--maxvel", dest="maxvel", type=positive_float, default=MAXVEL, help="Maximum angular velocity (must be positive)")
    parser.add_argument("--observatory", "-o", dest="observatory", type=obs_coordinates, default=(289.26345, 0.865020, -0.500901), help="Observatory coordinates, '<obslon>,<plxcos>,<plxsin>'")

    args = parser.parse_args()
    print(args)

    obsv = load_obsv("../tests/sample.csv")
    #hela.dp(data)
    #print(data[0])
    #exit(0)

    hela.maketrack03a(obsv, args.earthfile, args.inimfile, args.outimfile, args.outpairfile, args.pairdetfile, args.imrad, args.maxtime, args.maxvel, args.observatory)
