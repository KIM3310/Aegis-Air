from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "frontend" / "index.html"


def test_replay_focus_surface_contract() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    required_tokens = [
        'id="review-focus-rail"',
        'id="review-focus-title"',
        'id="review-focus-route"',
        'Keep one replay case visible from proof to commander handoff.',
    ]

    for token in required_tokens:
        assert token in html, token
