#!/usr/bin/env python
# Maged Goubran @ 2016, mgoubran@stanford.edu

# coding: utf-8

import argparse
import os
import warnings
from datetime import datetime
from subprocess import call

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pandas as pd
import seaborn as sns
import tifffile as tiff
from allensdk.core.mouse_connectivity_cache import MouseConnectivityCache

warnings.filterwarnings("ignore")

# ---------
# help fn


def helpmsg():
    return '''Usage: miracl_get_exp_conn_graph_proj_den.py -l [label id]

    Query Allen connectivity API for injection experiments & finds the experiment with highest proj volume
    Outputs a connectivity graph of that experiment & its projection density images (as nii & tif)
    If a label has no injection experiments, the connectivity atlas is searched for experiments for its parent label.

    Search is performed for experiemtns on wildtype (C57BL/6J) mice

    example: miracl_get_exp_conn_graph_proj_den.py -l

    arguments (required):

        l. Allen atlas label id


    Dependencies:

	    Python 2.7
	    used modules:
            argparse, numpy, scipy, seaborn, pandas, tifffile, warnings, matplotlib, os, sys, datetime, allensdk


    '''


# ---------
# Get input arguments


def getinpars():
    parser = argparse.ArgumentParser(description='Sample argparse py', usage=helpmsg())
    parser.add_argument('-l', '--lbl', type=int, help="Input label id", required=True)

    args = parser.parse_args()

    # check if pars given

    assert isinstance(args.lbl, int)
    lbl = args.lbl

    return lbl


# ---------------


def initialize():
    # type: () -> object
    # input parameters

    # projection density threshold
    cutoff = 0.001

    # max label value
    # maxannot = 13000  # ignore labels in millions (too small)!

    # read ontology annotation csv

    miracl_home = os.environ['MIRACL_HOME']

    annot_csv = pd.read_csv('%s/atlases/ara/ara_mouse_structure_graph_hemi_split.csv' % miracl_home)

    # read atlas annotations
    # atlas_lbls = np.loadtxt('%s/ara/annotation/annotation_hemi_split_10um_labels.txt' % miracl_home)

    # major labels to exclude (ie root,grey,etc) @ depth < 5 or grap order < 6
    exclude = np.array(annot_csv[(annot_csv["depth"] < 5) | (annot_csv["graph_order"] < 6)].id)

    return cutoff, miracl_home, annot_csv, exclude


# ---------------

def getprojden(mcc, exp_id):
    # projection density: number of projecting pixels / voxel volume
    projd, pd_info = mcc.get_projection_density(exp_id)

    # injection density: number of projecting pixels in injection site / voxel volume
    # ind, ind_info = mcc.get_injection_density(exp_id)

    # injection fraction: number of pixels in injection site / voxel volume
    # inf, inf_info = mcc.get_injection_fraction(exp_id)

    # data mask:
    # binary mask indicating which voxels contain valid data
    # dm, dm_info = mcc.get_data_mask(exp_id)

    return projd


# ---------------

def savenii(inarr, vx, outnii):
    # save parent data as nifti
    mat = np.eye(4) * vx
    mat[3, 3] = 1

    inarr = np.rollaxis(inarr, 1)
    inarr = np.swapaxes(inarr, 1, 2)

    tform = nib.orientations.axcodes2ornt(('A', 'I', 'R'))
    arrort = nib.orientations.apply_orientation(inarr, tform)

    # Create nifti
    nii = nib.Nifti1Image(arrort, mat)

    # nifti header info
    nii.header.set_data_dtype(np.int32)
    nib.save(nii, outnii)


def savetiff(inarr, outtiff):
    tiff.imsave(outtiff, inarr)


# ---------------
# Exclude major lablels

def exlude_maj_lbls(in_lbls, exclude):
    """ excludes major labels at shallow depths (in the Allen
    structure ontology graph) from the connectivity analysis
    """

    indx = np.in1d(in_lbls, exclude)
    out_lbls = np.delete(in_lbls, np.where(indx == True))

    return out_lbls

# ---------------
# Query Allen API

def query_connect(exp_id, cutoff, exclude, mcc):
    """ Queries the structural connectivity of
    labels inside mask & sorts found labels by normalized projection volume
    """

    all_connect_ids = []
    all_norm_proj = []

    # get exp regions stats
    projection_df = mcc.get_structure_unionizes([exp_id], is_injection=False)

    # Should probably do ipsi/contra

    # get connected regions
    filter_exp = projection_df.loc[
        (projection_df['normalized_projection_volume'] > cutoff) & (projection_df['hemisphere_id'] != 3)]

    # sort exp values by norm proj volume
    norm_proj = filter_exp.sort_values(['normalized_projection_volume'], ascending=False).ix[:,
                ['hemisphere_id', 'structure_id', 'normalized_projection_volume']]
    norm_proj_vol = norm_proj["normalized_projection_volume"]
    all_norm_proj.append(norm_proj_vol)

    # distinguish label hemisphere
    orgid = np.array(norm_proj['structure_id'])
    hem = np.array(norm_proj['hemisphere_id'])
    connect_ids = [orgid[i] + 20000 if hem[i] == 1 else orgid[i] for i in range(len(hem))]

    # filter out labels to exclude
    excl_ids = np.in1d(connect_ids, exclude)
    connect_ids_excl = np.delete(connect_ids, np.where(excl_ids == True))
    all_connect_ids.append(connect_ids_excl)

    # extract n ids

    all_connect_ids = np.array(all_connect_ids)
    all_norm_proj = np.array(all_norm_proj)

    return all_connect_ids, all_norm_proj


# ---------------
# save connected ids & abreviations as csv

def saveconncsv(conn_ids, annot_csv, lbl_abrv, inj_exp):
    """ Saves connectivity ids (primary structures & targets)
    as a csv file with their ontology atlas ID number
    """

    print("\n Computing & saving connected ids as a csv file")

    # save as csv
    export_connect = pd.DataFrame(conn_ids)

    connect_cols = ['connect_lbl_%02d' % (i + 1) for i in range(export_connect.shape[1] - 1)]
    all_cols = ['injection_lbl'] + connect_cols

    export_connect.columns = all_cols
    export_connect.to_csv('%s_exp%s_connected_ids.csv' % (lbl_abrv, inj_exp), index=False)

    # export acronynms
    dic = annot_csv.set_index('id')['acronym'].to_dict()

    export_connect_abv = export_connect.replace(dic)
    export_connect_abv.to_csv('%s_exp%s_connected_abrvs.csv' % (lbl_abrv, inj_exp), index=False)

    return export_connect_abv


# ---------------
# compute & save projection map

def exportprojmap(all_norm_proj, export_connect_abv, lbl_abrv, inj_exp):
    """ Generates & saves the projection map of primary structures as png, and
    the projection data as a csv file
    """

    print("\n Computing & saving projection map")

    # export projection map (lbls w norm proj volumes along tree)

    n = 35

    out_norm_proj = all_norm_proj.T[:n]
    abrv_annot = np.array(export_connect_abv.T.ix[:n])
    abrv_annot = pd.DataFrame(abrv_annot).replace(np.nan, ' ', regex=True)

    plt.figure(figsize=(n, 3))
    sns.set_context("talk", font_scale=0.75)
    sns.heatmap(out_norm_proj.T,
                cbar_kws={"label": "Normalized projection volume"},
                annot=abrv_annot.T, fmt="s")

    plt.yticks(rotation=0)

    plt.ylabel('Primary injection structure')
    plt.xlabel('Target structure order along connection graph')
    plt.savefig('%s_exp%s_projection_map_along_graph.png' % (lbl_abrv, inj_exp), dpi=300)

    # export proj volumes
    # norm_proj_df = pd.DataFrame(out_norm_proj)
    # norm_proj_df.to_csv('normalized_projection_volumes.csv', index=False)


# ---------------

def main():
    starttime = datetime.now()

    # initial pars & read inputs
    lbl = getinpars()

    [cutoff, miracl_home, annot_csv, exclude] = initialize()

    mcc = MouseConnectivityCache(
        manifest_file='%s/connect/connectivity_exps/mouse_connectivity_manifest.json' % miracl_home)

    # Load all injection experiments from Allen api
    all_experiments = mcc.get_experiments(dataframe=True)
    # Filter to only wild-type strain
    projexps = all_experiments[all_experiments['strain'] == "C57BL/6J"]
    # no transgenic mice
    projexps = projexps[projexps['transgenic-line'] == ""]

    # ---------------

    # Check if labels have injection exps
    print("\n Checking if labels have injection experiments in the connectivity search")

    inj_exp = projexps[projexps['structure-id'] == lbl].id.index[0]

    while inj_exp is None:
        pid = annot_csv.parent_structure_id[annot_csv.id == lbl].values[0]
        inj_exp = projexps[projexps['structure-id'] == pid].id.index[0]

    # ---------------

    # Get projection density
    projd = getprojden(mcc, inj_exp)

    lbl_abrv = annot_csv[annot_csv['id'] == lbl]['acronym'].values[0]
    lbl_abrv = lbl_abrv[1:]  # drop 1st char

    print("\n Downloading projection density volume for experiment %d of lbl %d => %s" % (inj_exp, lbl, lbl_abrv))

    outpd = '%s_exp%s_projection_density.nii.gz' % (lbl_abrv, inj_exp)
    outtif = '%s_exp%s_projection_density.tif' % (lbl_abrv, inj_exp)
    # outind = '%s_injection_density.nii.gz' % experiment_id
    # outdm = '%s_binary_mask.nii.gz' % experiment_id

    vx = 0.025

    savenii(projd, vx, outpd)
    savetiff(projd, outtif)

    # orient
    call(["c3d", "%s" % outpd, "-orient", "ASR", "-o", "%s" % outpd])

    # savenii(ind, vx, outind)
    # savenii(dm, vx, outdm)

    # ---------------

    # Get connectivity graph
    # query structure connectivity from Allen API
    print("\n Quering structural connectivity of injection labels in the Allen API & sorting by projection volume")

    [all_connect_ids, all_norm_proj] = query_connect(inj_exp, cutoff, exclude, mcc)

    # save csv
    export_connect_abv = saveconncsv(all_connect_ids, annot_csv, lbl_abrv, inj_exp)

    # compute & save proj map
    exportprojmap(all_norm_proj, export_connect_abv, lbl_abrv, inj_exp)

    print ("\n Downloading connectivity graph & projection map done in %s ... Have a good day!\n" % (
    datetime.now() - starttime))


# Call main function
if __name__ == "__main__":
    main()


# ------
# TODOs

# TODOlp: use label abrv too
# TODOlp: add paremeter for choosing different stain or transgenic line of mice
