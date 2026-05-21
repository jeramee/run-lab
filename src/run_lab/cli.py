from __future__ import annotations
import argparse, json
from .workspace import init_workspace, inspect_workspace
from .runner import run_demo
from .verify import verify_run
from .replay import inspect_replay_manifest

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="run-lab")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init")
    p.add_argument("workspace")

    p = sub.add_parser("inspect")
    p.add_argument("workspace", nargs="?", default=".")

    p = sub.add_parser("run")
    p.add_argument("--workspace", default=".")
    p.add_argument("--query-job", required=True)
    p.add_argument("--output-prefix", default="rag_literature_demo")
    p.add_argument("--render", default="html")

    p = sub.add_parser("verify")
    p.add_argument("run_dir")

    p = sub.add_parser("replay")
    p.add_argument("manifest")

    args = parser.parse_args(argv)
    if args.command == "init":
        print(init_workspace(args.workspace))
        return 0
    if args.command == "inspect":
        print(json.dumps(inspect_workspace(args.workspace), indent=2, sort_keys=True))
        return 0
    if args.command == "run":
        print(run_demo(args.workspace, args.query_job, args.output_prefix, args.render))
        return 0
    if args.command == "verify":
        result = verify_run(args.run_dir)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["verification_status"] == "pass" else 1
    if args.command == "replay":
        print(json.dumps(inspect_replay_manifest(args.manifest), indent=2, sort_keys=True))
        return 0
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
