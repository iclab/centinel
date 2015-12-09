from hlb_pi import HeadlessBrowser
import sys
import os


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write("Error: need at least one url or file name")
        sys.stderr.flush()
        raise SystemExit
    print sys.argv
    hlb = HeadlessBrowser()

    if '-' is sys.argv[1][0]:
        if len(sys.argv) < 3 or sys.argv[1] != "-f":
            sys.stdout.write("Usage: -f filename\n")
            sys.stdout.flush()
        else:
            hlb.run(input_file=sys.argv[2])
    else:
        hlb.run(input_list=sys.argv[1:])
