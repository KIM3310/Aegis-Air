from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aegis_engine.replay_evals import run_replay_suite


def main() -> None:
    suite = run_replay_suite()
    print(json.dumps(suite, indent=2))


if __name__ == "__main__":
    main()
