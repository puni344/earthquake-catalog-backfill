"""Local D2 verification drills."""
import argparse

from . import preflight


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--drill", required=True, choices=["preflight"])
    parser.parse_args(argv)
    return preflight.run()


if __name__ == "__main__":
    raise SystemExit(main())
