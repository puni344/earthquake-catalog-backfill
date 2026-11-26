"""Local D2 verification drills."""
import argparse

from pathlib import Path

from . import acquire, preflight, reconcile, restart


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--drill", required=True, choices=["preflight", "acquire", "reconcile", "restart"])
    parser.add_argument("--offline", type=Path, metavar="MANIFEST")
    args = parser.parse_args(argv)
    if args.drill == "acquire":
        return acquire.run(args.offline)
    if args.offline is not None:
        parser.error("--offline requires --drill acquire")
    if args.drill == "reconcile":
        return reconcile.run()
    if args.drill == "restart":
        return restart.run()
    return preflight.run()


if __name__ == "__main__":
    raise SystemExit(main())
