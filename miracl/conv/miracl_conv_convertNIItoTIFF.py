#!/usr/bin/env python
# Maged Goubran @ 2017, mgoubran@stanford.edu

# coding: utf-8

import argparse
from PyQt5.QtWidgets import *
import logging
import os
import sys
import warnings
from argparse import RawTextHelpFormatter
from datetime import datetime

import nibabel as nib
import scipy.ndimage
import tifffile as tiff
from PyQt5.QtGui import *

from miracl.conv import miracl_conv_gui_options as gui_opts

warnings.simplefilter("ignore", UserWarning)


def helpmsg():
    return '''

Converts Nifti images to Tiff

    A GUI will open to choose your:

        - < Input CLARITY Nii >

    ----------

    For command-line / scripting

    Usage: miracl_conv_convertNIItoTIFF.py -i [Nii file]

    Example: miracl_conv_convertNIItoTIFF.py -i stroke2.nii.gz -o stroke2.tiff -u 5

    required arguments:
      -i, --input          Input CLARITY Nii

    optional arguments:
      -u, --up             Up-sample ratio (default: 1)
      -o, --outnii         Output nii name (script will append downsample ratio & channel info to given name)
      -s, --spline         Spline order

      -h, --help           Show this help message and exit


        '''


# Dependencies:
#
#     Python 2.7
#     used modules:
#         argparse, numpy, cv2, nibabel, pyqt4,
#         glob, re, os, sys, datetime, joblib, multiprocessing


def folder_dialog(self, msg):
    """
    Get file / folder with gui with QFileDialog
    """

    folder = str(QFileDialog.getExistingDirectory(self, "%s" % msg, "."))

    if len(folder) > 0:
        print("\n Folder chosen for reading is: %s" % folder)
    else:
        print("No folder was chosen")

    return folder


def parsefn():
    if len(sys.argv) >= 3 and sys.argv[-2] == 'conv' and sys.argv[-1] == 'nii_tiff':
        parser = argparse.ArgumentParser(description='', usage=helpmsg(), formatter_class=RawTextHelpFormatter,
                                         add_help=False)
    else:
        parser = argparse.ArgumentParser(description='', usage=helpmsg(), formatter_class=RawTextHelpFormatter, add_help=False)
                                         #usage='%(prog)s  -i [In nii] -o [Out tiff] -u [Up-sample ratio] -s [Spline order]')

        required = parser.add_argument_group('required arguments')
        required.add_argument('-i', '--input', type=str, required=True, metavar='dir',
                              help="Input NII")

        optional = parser.add_argument_group('optional arguments')

        optional.add_argument('-u', '--up', type=int, metavar='', help="Up-sample ratio (default: 1)")
        optional.add_argument('-o', '--outtiff', type=str, metavar='', help="Output tiff name")
        optional.add_argument('-s', '--spline', type=int, metavar='', help="Spline order")

    # optional.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser


def parse_inputs(parser, args):
    if isinstance(args, list):
        args, unknown = parser.parse_known_args()

    if sys.argv[-2] == 'conv' and sys.argv[-1] == 'nii_tiff':

        print("Running in GUI mode")

        title = 'Nii to Tiff conversion'
        dirs = ['Input Nii file']
        fields = ['Out nii name (def = clarity)', 'Up-sample ratio (def = 1)', 'Spline order (def = 3)']

        app = QApplication(sys.argv)
        menu, linedits, labels = gui_opts.OptsMenu(title=title, dirs=dirs, fields=fields, helpfun=helpmsg())
        menu.show()
        app.exec_()
        app.processEvents()

        indirstr = labels[dirs[0]].text()
        input = str(indirstr.split(":")[1]).lstrip()
        assert os.path.exists(input), '%s does not exist ... please check path and rerun script' % input

        # Initialize default params

        outtiff = 'clarity.tif' if not linedits[fields[0]].text() else str(linedits[fields[0]].text())

        u = 1 if not linedits[fields[1]].text() else int(linedits[fields[1]].text())

        s = 3 if not linedits[fields[2]].text() else int(linedits[fields[1]].text())

    else:

        print("\n running in script mode")

        # check if pars given

        assert isinstance(args.input, str)
        input = args.input

        assert os.path.exists(input), '%s does not exist ... please check path and rerun script' % input

        if args.outtiff is None:
            outtiff = 'clarity.tif'
        else:
            assert isinstance(args.outtiff, str)
            outtiff = args.outtiff

        if args.up is None:
            u = 1
            print("\n Up-sample ratio not specified ... choosing default value of %d" % u)
        else:
            assert isinstance(args.up, int)
            u = args.up

        if args.spline is None:
            s = 3
            print("\n Spline order not specified ... choosing default value of %d" % s)
        else:
            assert isinstance(args.spline, int)
            s = args.spline

    return input, outtiff, u, s


# ---------
# Logging fn

def scriptlog(logname):
    class StreamToLogger(object):
        """
       Fake file-like stream object that redirects writes to a logger instance.
       """

        def __init__(self, logger, log_level=logging.INFO):
            self.logger = logger
            self.log_level = log_level
            self.linebuf = ''

        def write(self, buf):
            for line in buf.rstrip().splitlines():
                self.logger.log(self.log_level, line.rstrip())

        def flush(self):
            pass

    logging.basicConfig(
        level=logging.DEBUG,
        filename="%s" % logname,
        format='%(asctime)s:%(message)s',
        filemode='w')

    stdout_logger = logging.getLogger('STDOUT')
    handler = logging.StreamHandler()
    stdout_logger.addHandler(handler)
    sys.stdout = StreamToLogger(stdout_logger, logging.INFO)

    stderr_logger = logging.getLogger('STDERR')
    stderr_logger.addHandler(handler)
    sys.stderr = StreamToLogger(stderr_logger, logging.ERROR)


def convert_nii_to_tiff(input_nii, out_tiff, upsample_ratio, spline_order):
    nii = nib.load(input_nii).get_data()

    hres_tiff = scipy.ndimage.interpolation.zoom(nii, upsample_ratio, order=spline_order)

    tiff.imsave(out_tiff, hrestiff)


# ---------

# def converttiff2nii(d, i, x, newdata, tifx):
#     """
#     """
#
#     # down ratio
#     down = (1.0 / int(d))
#
#     sys.stdout.write("\r processing slice %d ..." % i)
#     sys.stdout.flush()
#
#     m = cv2.imread(x, -1)
#
#     # nearest neighbour for very large data sets
#     inter = cv2.INTER_CUBIC if tifx < 5000 else cv2.INTER_NEAREST
#
#     newdata[i, :, :] = cv2.resize(m, (0, 0), fx=down, fy=down, interpolation=inter)
#     # data.append(mres)

# ---------

def main(args):
    starttime = datetime.now()

    parser = parsefn()
    input, outtiff, u, s = parse_inputs(parser, args)

    # convert nii volume to tiff
    print("\n converting NII volume to TIFF")

    convert_nii_to_tiff(input, outtiff, u, s)

    print("\n conversion done in %s ... Have a good day!\n" % (datetime.now() - starttime))


if __name__ == "__main__":
    main(sys.argv[1:])


# Todos
