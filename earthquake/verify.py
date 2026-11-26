"""Local D2 verification drills."""
import argparse

from pathlib import Path

from . import acquire, preflight, reconcile, restart, history_drill, publish_drill, load, demo


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--drill", choices=["preflight", "acquire", "reconcile", "restart", "history", "publish", "load"])
    acquisition = parser.add_mutually_exclusive_group()
    acquisition.add_argument("--resume", metavar="ACQUISITION_ID")
    acquisition.add_argument("--offline", type=Path, metavar="MANIFEST")
    args = parser.parse_args(argv)
    if args.drill == "acquire":
        return acquire.run(args.offline, args.resume)
    if args.offline is not None or args.resume is not None:
        parser.error("--offline and --resume require --drill acquire")
    if args.drill is None:
        return demo.run()
    if args.drill == "reconcile":
        return reconcile.run()
    if args.drill == "restart":
        return restart.run()
    if args.drill == "history":
        return history_drill.run()
    if args.drill == "publish":
        return publish_drill.run()
    if args.drill == "load":
        return load.run()
    return preflight.run()


if __name__ == "__main__":
    raise SystemExit(main())
