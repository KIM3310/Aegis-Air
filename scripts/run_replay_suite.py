"""Run the Aegis-Air replay evaluation suite and print results as JSON.

Usage::

    python scripts/run_replay_suite.py
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aegis_engine.replay_evals import run_replay_suite  # noqa: E402


def main() -> None:
    """Execute the replay suite and print the JSON result to stdout."""
    suite: dict[str, Any] = run_replay_suite()
    print(json.dumps(suite, indent=2))


if __name__ == "__main__":
    main()
