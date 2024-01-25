import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--secret', help="Secret key to store", action='store', required=True)

args = parser.parse_args()


print(f"The KEY is {args.secret}")