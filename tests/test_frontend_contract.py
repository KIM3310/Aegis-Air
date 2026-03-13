from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "frontend" / "index.html"


def test_replay_focus_surface_contract() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    required_tokens = [
        'id="review-focus-rail"',
        'id="review-focus-title"',
        'id="review-focus-route"',
        'id="copy-review-path-btn"',
        'id="copy-top-replay-btn"',
        'id="copy-commander-brief-btn"',
        'Keep one replay case visible from proof to commander handoff.',
        'Fast path: /api/evals/replays → /api/runtime/brief → /api/incident-command-board.',
    ]

    for token in required_tokens:
        assert token in html, token
