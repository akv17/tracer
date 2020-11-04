import argparse
import os
from .core2 import _setup


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', type=str, required=True)
    parser.add_argument('--t', type=str, required=False, default='')
    args = parser.parse_args()
    targets = [p.strip() for p in args.t.split(',')]
    _setup(entry_fp=args.e, targets=targets)
