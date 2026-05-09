"""Command-line interface for Governance-Ledger operational workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from governance_ledger.publish import approve_review_file, publish_review_file
from governance_ledger.runner import run_policy_directory
from governance_ledger.checks import check_validation_directory, format_check_summary
from governance_ledger.inspect import (
    format_artifact,
    format_contract_list,
    list_contracts,
    show_artifact,
)
from governance_ledger.summary import (
    build_pr_summary,
    format_publish_summary,
    format_run_summary,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="governance-ledger")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="generate draft governance artifacts")
    run_parser.add_argument("policies_dir")
    run_parser.add_argument("--generated-dir", default="generated")
    run_parser.add_argument("--reviews-dir", default="reviews")
    run_parser.add_argument("--json", action="store_true")
    run_parser.add_argument("--pr-summary")

    approve_parser = subparsers.add_parser("approve", help="approve a review artifact")
    approve_parser.add_argument("review_path")
    approve_parser.add_argument("--actor", required=True)
    approve_parser.add_argument("--timestamp")
    approve_parser.add_argument("--note")
    approve_parser.add_argument("--json", action="store_true")

    publish_parser = subparsers.add_parser("publish", help="publish an approved review")
    publish_parser.add_argument("review_path")
    publish_parser.add_argument("--generated-dir", default="generated")
    publish_parser.add_argument("--contracts-dir", default="contracts")
    publish_parser.add_argument("--reviews-dir", default="reviews")
    publish_parser.add_argument("--snapshots-dir", default="snapshots")
    publish_parser.add_argument("--actor", default="governance-team")
    publish_parser.add_argument("--compiler-actor", default="compiler-service")
    publish_parser.add_argument("--deployed-by", default="ops-team")
    publish_parser.add_argument("--environment", default="production")
    publish_parser.add_argument("--runtime", default="waveframe-guard")
    publish_parser.add_argument("--enforcement-engine-version", default="0.12.0")
    publish_parser.add_argument("--timestamp")
    publish_parser.add_argument("--json", action="store_true")

    check_parser = subparsers.add_parser("check", help="check generated validation artifacts")
    check_parser.add_argument("generated_dir")
    check_parser.add_argument("--json", action="store_true")

    list_parser = subparsers.add_parser("list", help="list governance registry artifacts")
    list_parser.add_argument("kind", choices=["contracts"])
    list_parser.add_argument("--contracts-dir", default="contracts")
    list_parser.add_argument("--json", action="store_true")

    show_parser = subparsers.add_parser("show", help="show a governance artifact")
    show_parser.add_argument("path")
    show_parser.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "run":
        result = run_policy_directory(
            args.policies_dir,
            generated_dir=args.generated_dir,
            reviews_dir=args.reviews_dir,
        )
        if args.pr_summary:
            Path(args.pr_summary).write_text(
                "\n\n".join(
                    build_pr_summary(
                        json.loads(Path(item["review"]).read_text(encoding="utf-8")),
                        policy_name=Path(item["policy"]).name,
                    )
                    for item in result
                )
                + "\n",
                encoding="utf-8",
            )
    elif args.command == "approve":
        result = approve_review_file(
            args.review_path,
            actor=args.actor,
            timestamp=args.timestamp,
            note=args.note,
        )
    elif args.command == "publish":
        result = publish_review_file(
            args.review_path,
            generated_dir=args.generated_dir,
            contracts_dir=args.contracts_dir,
            reviews_dir=args.reviews_dir,
            snapshots_dir=args.snapshots_dir,
            actor=args.actor,
            compiler_actor=args.compiler_actor,
            deployed_by=args.deployed_by,
            environment=args.environment,
            runtime=args.runtime,
            enforcement_engine_version=args.enforcement_engine_version,
            timestamp=args.timestamp,
        )
    elif args.command == "check":
        result = check_validation_directory(args.generated_dir)
    elif args.command == "list":
        result = list_contracts(args.contracts_dir)
    else:
        result = show_artifact(args.path)

    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.command == "run":
        print(format_run_summary(result))
    elif args.command == "publish":
        print(format_publish_summary(result))
    elif args.command == "check":
        print(format_check_summary(result))
        return 1 if result["error_count"] else 0
    elif args.command == "list":
        print(format_contract_list(result))
    elif args.command == "show":
        print(format_artifact(args.path, result))
    else:
        print(
            "\n".join(
                [
                    "[Governance Ledger]",
                    "",
                    "Review:",
                    f"  {result['review_id']} approved",
                    "",
                    "Status:",
                    f"  {result['review_status']}",
                ]
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
