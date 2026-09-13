#!/usr/bin/env python3
"""Run bats files with tests split across N parallel workers.

Each bats file's tests are discovered and partitioned round-robin across
`workers` processes. Each worker runs `bats --filter <regex>` with a
regex matching its subset. Workers run concurrently; output is streamed
to stdout as each completes.

Usage: bats_parallel.py <workers> <bats-file> [bats-file ...]
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def extract_tests(bats_file: Path) -> list[str]:
    """Read a bats file and return the test names declared via @test."""
    out: list[str] = []
    pat = re.compile(r'^@test\s+"([^"]+)"')
    for line in bats_file.read_text().splitlines():
        m = pat.match(line)
        if m:
            out.append(m.group(1))
    return out


def regex_for(names: list[str]) -> str:
    """Build an anchored alternation regex matching exactly the given names.

    bats --filter does substring matching, so we anchor with ^...$ to
    prevent a name from accidentally matching another test whose
    description contains it as a substring.
    """
    return "^(" + "|".join(re.escape(n) for n in names) + ")$"


def run_worker(args: tuple[list[str], str]) -> tuple[int, str]:
    """Run a single bats invocation; return (exit_code, output)."""
    cmd, regex = args
    cmd += ["--filter", regex]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, (proc.stdout + proc.stderr)


def main() -> int:
    if len(sys.argv) < 3:
        print(f"usage: {sys.argv[0]} <workers> <bats-file> [bats-file ...]",
              file=sys.stderr)
        return 2

    workers = int(sys.argv[1])
    files = [Path(f) for f in sys.argv[2:]]

    # Discover all tests across all files, preserving order.
    all_tests: list[tuple[Path, str]] = []
    for f in files:
        for name in extract_tests(f):
            all_tests.append((f, name))

    if not all_tests:
        print("no tests found", file=sys.stderr)
        return 1

    # Partition round-robin into N worker buckets.
    buckets: list[list[str]] = [[] for _ in range(workers)]
    for i, (_f, name) in enumerate(all_tests):
        buckets[i % workers].append(name)

    # Build a worker invocation per (file, bucket). Each worker is a
    # disjoint subset; an empty bucket is skipped.
    jobs: list[tuple[list[str], str]] = []
    seen_files = [str(f) for f in files]
    base_cmd = ["bats"]
    for bucket in buckets:
        if not bucket:
            continue
        jobs.append((base_cmd + seen_files, regex_for(bucket)))

    overall = 0
    # Stream output as workers complete; preserve worker ordering by
    # printing worker results in submission order.
    results: dict[int, tuple[int, str]] = {}
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {pool.submit(run_worker, job): i for i, job in enumerate(jobs)}
        for fut in as_completed(futures):
            results[futures[fut]] = fut.result()

    for i in range(len(jobs)):
        rc, out = results[i]
        if out:
            sys.stdout.write(out)
            if not out.endswith("\n"):
                sys.stdout.write("\n")
            sys.stdout.flush()
        if rc != 0:
            overall = 1

    return overall


if __name__ == "__main__":
    sys.exit(main())
