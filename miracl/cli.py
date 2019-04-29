import os
import sys
import argparse
import logging
from pathlib import Path

# logging.basicConfig(format='%(asctime)15s - %(levelname)s - %(message)s', level=logging.DEBUG)
# logger = logging.getLogger()

from miracl.flow import cli_flow
from miracl.reg import cli_reg
from miracl.seg import cli_seg
# from miracl.conv import cli_conv
from miracl.conv import miracl_conv_convertTIFFtoNII, miracl_conv_gui_options
from miracl.connect import cli_connect
from miracl.lbls import cli_lbls
from miracl.sta import cli_sta


def run_flow(parser, args):
    cli_flow.main()


def run_reg(parser, args):
    cli_reg.main()


def run_seg(parser, args):
    cli_seg.main()


# def run_io(parser, args):
#    cli_conv.main()

def run_tiff_nii(parser, args):
    miracl_conv_convertTIFFtoNII.main(args)


def run_connect(parser, args):
    cli_connect.main()


def run_lbls(parser, args):
    cli_lbls.main()


def run_sta(parser, args):
    cli_sta.main()


def get_parser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    # flow
    flow_parser = cli_flow.get_parser()
    parser_flow = subparsers.add_parser('flow', parents=[flow_parser], add_help=False,
                                        help="workflows to run")

    parser_flow.set_defaults(func=run_flow)

    # reg
    reg_parser = cli_reg.get_parser()
    parser_reg = subparsers.add_parser('reg', parents=[reg_parser], add_help=False,
                                       help="registration functions")

    parser_reg.set_defaults(func=run_reg)

    # seg
    seg_parser = cli_seg.get_parser()
    parser_seg = subparsers.add_parser('seg', parents=[seg_parser], add_help=False,
                                       help="segmentation functions")

    parser_seg.set_defaults(func=run_seg)

    # sta
    sta_parser = cli_sta.get_parser()
    parser_sta = subparsers.add_parser('sta', parents=[sta_parser], add_help=False,
                                       help="STA functions")

    parser_sta.set_defaults(func=run_sta)

    # connect
    connect_parser = cli_connect.get_parser()
    parser_connect = subparsers.add_parser('connect', parents=[connect_parser], add_help=False,
                                           help="connect functions")

    parser_connect.set_defaults(func=run_connect)

    # conv
    # io_parser = cli_conv.get_parser()
    # parser_io = subparsers.add_parser('conv', parents=[io_parser], add_help=False,
    #                                   help="conv functions")

    # parser_io.set_defaults(func=run_io)

    # tiff_nii
    tiff_nii_parser = miracl_conv_convertTIFFtoNII.parsefn()
    parser_tiff_nii = subparsers.add_parser('conv_tiff_nii', parents=[tiff_nii_parser], add_help=False,
                                            help='convert Tiff stacks to Nii')
    parser_tiff_nii.set_defaults(func=run_tiff_nii)


    # lbls
    lbls_parser = cli_lbls.get_parser()
    parser_lbls = subparsers.add_parser('lbls', parents=[lbls_parser], add_help=False,
                                      help="Label manipulation functions")

    parser_lbls.set_defaults(func=run_lbls)

    return parser


def main(args=None):
    """ main cli call"""
    if args is None:
        args = sys.argv[1:]

    # set miracl home
    # if os.environ['MIRACL_HOME'] is None:
    cli_file = os.path.realpath(__file__)
    miracl_dir = Path(cli_file).parents[0]
    os.environ['MIRACL_HOME'] = '%s' % miracl_dir

    parser = get_parser()
    args = parser.parse_args(args)
    args.func(parser, args)


if __name__ == '__main__':
    main()
