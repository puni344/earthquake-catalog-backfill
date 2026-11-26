"""Local D2 verification drills."""
import argparse

from pathlib import Path

from . import acquire, preflight, reconcile, restart, history_drill, publish_drill


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--drill", required=True, choices=["preflight", "acquire", "reconcile", "restart", "history", "publish"])
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
    if args.drill == "history":
        return history_drill.run()
    if args.drill == "publish":
        return publish_drill.run()
    return preflight.run()


if __name__ == "__main__":
    raise SystemExit(main())
