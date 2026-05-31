from __future__ import annotations

from pathlib import Path
import json


def main() -> None:
    """Write a reproducible record of the simple imitation baseline."""

    out = Path("outputs/one_step_imitation/baseline.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "name": "one_step_imitation",
                "description": "Always imitates the first observed Gripper action, pick.",
                "action": "pick",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
