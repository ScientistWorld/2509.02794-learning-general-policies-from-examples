"""Default evaluation entry point (scripts/evaluate.sh).

Scores every policy artifact on disk on the visible train slice and writes
`scoring/scores.json`. The scoring logic lives in `eval/train/evaluate_gripper.py`;
the hidden test slice uses its own independent copy in `eval/test/`.
"""
from __future__ import annotations

import sys

from eval.train.evaluate_gripper import main as _train_main


def main() -> None:
    argv = sys.argv[1:]
    if "--output" not in argv:
        argv = argv + ["--output", "scoring/scores.json"]
    _train_main(argv)


if __name__ == "__main__":
    main()
