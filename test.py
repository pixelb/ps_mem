import argparse
import sys


parser = argparse.ArgumentParser()
parser.add_argument('--foo', nargs='+')
a = parser.parse_args('--foo'.split())
print(a)