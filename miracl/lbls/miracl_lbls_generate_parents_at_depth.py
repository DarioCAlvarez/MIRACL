#!/usr/bin/env python
# Maged Goubran @ 2017, mgoubran@stanford.edu

# coding: utf-8

import argparse
import os
import re
import sys
from datetime import datetime
from os.path import basename
from subprocess import call

import nibabel as nib
import numpy as np
import pandas as pd

from miracl.utilfn.depends_manager import add_paths
from miracl import ATLAS_DIR

# ---------
# help fn

def helpmsg():
    return '''
    miracl_lbls_generate_parents_at_depth.py -d [depth] -m [hemisphere: split or combined
    (default: combined)] -v [voxel size in um: 10, 25 or 50 (default: 25)] -l [input labels (default: Allen labels]

    Generate parents labels at specific depth from Allen labels

    Labels with higher depth are combined by their parent labels

    example: miracl_lbls_generate_parents_at_depth.py -d 6 -m combined -v 10

    or

    miracl_lbls_generate_parents_at_depth.py -l my_registered_labels.nii.gz -d 6

    '''


# ---------
# Get input arguments

def parsefn():
    parser = argparse.ArgumentParser(description='', usage=helpmsg())
    parser.add_argument('-d', '--depth', type=int, help="chosen depth", required=True)
    parser.add_argument('-m', '--hemi', type=str, help="hemisphere mirrored or not", required=False)
    parser.add_argument('-v', '--res', type=int, help="voxel size in um", required=False)
    parser.add_argument('-l', '--inlbls', type=str, help="input labels", required=False)

    return parser


def parse_inputs(parser, args):
    if isinstance(args, list):
        args, unknown = parser.parse_known_args()

    # check if pars given

    if args.depth is None:
        d = 6
        print("depth not specified ... choosing default value of %d" % d)
    else:
        assert isinstance(args.depth, int)
        d = args.depth

    if args.inlbls is None:
        inlbls = "Allen"
        print("input labels not specified ... choosing default Allen lbls")

        if args.hemi is None:
            hemi = "combined"
            print("hemisphere not specified ... choosing default value of %s" % hemi)
        else:
            assert isinstance(args.hemi, str)
            hemi = args.hemi

        if args.res is None:
            res = 25
            print("voxel size not specified ... choosing default value of %dum" % res)
        else:
            assert isinstance(args.res, int)
            res = args.res

    else:
        inlbls = args.inlbls
        hemi = None
        res = None

    return d, inlbls, hemi, res


# --- Init pars ---

lblsplit = 20000  # number added to contra side
maxannotlbl = 13000  # > max lbl in ipsi

# ------------


def getalllbls(data):
    # get unique lblsfsl
    lbls = np.unique(list(data))
    lbls = lbls[lbls > 0]  # discard negative lbls

    return lbls


def getlblparent(clarinfo, lbl, pl, lblsplit, maxannotlbl):
    # path id
    path = clarinfo.structure_id_path[clarinfo.id == lbl]

    # remove /
    numpath = re.sub("[/]", ' ', str(path))

    # get digits
    digpath = [int(s) for s in numpath.split() if s.isdigit()]
    digpath = digpath[1:]  # drop 1st index

    # get parent
    if len(path) == 0:
        parent = lbl
    elif len(digpath) < pl:
        parent = digpath[0]
    else:
        parent = digpath[-pl]

    # if np.max(lbls) > lblsplit:
    parent = parent + lblsplit if lbl > maxannotlbl else parent

    return parent


# get all labels past depth
def getpastlabelsdepth(clarinfo, alllbls, chosendepth, lblsplit, maxannotlbl):
    pastparents = {}

    for l, lbl in enumerate(alllbls):

        lbldepth = clarinfo.depth[clarinfo.id == lbl].values
        if lbldepth > chosendepth:
            depthdiff = int(lbldepth - chosendepth) + 1
            pastparents[lbl] = getlblparent(clarinfo, lbl, depthdiff, lblsplit, maxannotlbl)

    return pastparents


# replace vals
def replacechildren(data, parentdata, pastlbl, pastparent):
    parentdata[data == pastlbl] = pastparent

    return parentdata


def saveniiparents(parentdata, vx, outnii):
    # save parent data as nifti
    mat = np.eye(4) * vx
    mat[3, 3] = 1

    # Create nifti
    nii = nib.Nifti1Image(parentdata, mat)

    # nifti header info
    nii.header.set_data_dtype(np.int32)
    nib.save(nii, outnii)

def get_parent_data(depth, inlbls='Allen', hemi='combined', res=25):
    ''' The main method for this function.
    '''
    if inlbls == "Allen":

        # load annotations
        print("Reading ARA annotation with %s hemispheres and %d voxel size" % (hemi, res))

        nii = '%s/ara/annotation/annotation_hemi_%s_%dum.nii.gz' % (ATLAS_DIR, hemi, res)
        print(nii)

    else:
        print("Reading input labels")
        nii = inlbls
    pass

    img = nib.load(nii)
    data = img.get_data()

    # load structure graph
    print("Reading ARA ontology structure_graph")
    arastrctcsv = "%s/ara/ara_mouse_structure_graph_hemi_split.csv" % ATLAS_DIR
    aragraph = pd.read_csv(arastrctcsv)

    # get lbls
    lbls = getalllbls(data)

    # loop over intensities
    parentdata = np.copy(data)

    print("Computing parent labels at depth %d" % depth)

    pastparents = getpastlabelsdepth(aragraph, lbls, depth, lblsplit, maxannotlbl)

    for pastlbl, pastparent in pastparents.items():
        replacechildren(data, parentdata, pastlbl, pastparent)

    return parentdata


def main(args):
    starttime = datetime.now()

    parser = parsefn()
    d, inlbls, hemi, res = parse_inputs(parser, args)

    # return the parent data as an array
    # parentdata = getparentdata(d, inlbls, hemi, res)

    if inlbls == "Allen":

        # load annotations
        print("Reading ARA annotation with %s hemispheres and %d voxel size" % (hemi, res))

        nii = '%s/ara/annotation/annotation_hemi_%s_%dum.nii.gz' % (ATLAS_DIR, hemi, res)
        print(nii)

    else:
        print("Reading input labels")
        nii = inlbls

    img = nib.load(nii)
    data = img.get_data()

    # load structure graph
    print("Reading ARA ontology structure_graph")
    arastrctcsv = "%s/ara/ara_mouse_structure_graph_hemi_split.csv" % ATLAS_DIR
    aragraph = pd.read_csv(arastrctcsv)

    # get lbls
    lbls = getalllbls(data)

    # loop over intensities
    parentdata = np.copy(data)

    print("Computing parent labels at depth %d" % d)

    pastparents = getpastlabelsdepth(aragraph, lbls, d, lblsplit, maxannotlbl)

    for pastlbl, pastparent in pastparents.items():
        replacechildren(data, parentdata, pastlbl, pastparent)

    vx = img.header.get_zooms()[0]
    orgname = basename(nii).split('.')[0]
    outnii = '%s_depth_%s.nii.gz' % (orgname, d)
    saveniiparents(parentdata, vx, outnii)

    if inlbls == "Allen":
        # orient
        call(["c3d", "%s" % outnii, "-orient", "ASR", "-type", "ushort", "-o", "%s" % outnii])

        call(["c3d", "%s" % outnii, "-origin", "-11.4x0x0mm", "-o", "%s" % outnii])

    print ("\n Parent labels at depth done in %s ... Have a good day!\n" % (datetime.now() - starttime))


if __name__ == "__main__":
    main(sys.argv)
