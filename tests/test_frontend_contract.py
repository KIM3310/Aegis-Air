from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "frontend" / "index.html"


def test_replay_focus_surface_contract() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    required_tokens = [
        'id="review-focus-rail"',
        'id="review-focus-title"',
        'id="review-focus-route"',
        'id="review-focus-checkpoint"',
        'id="review-focus-freshness"',
        'id="review-focus-freshness-state"',
        'id="review-focus-freshness-note"',
        'id="review-focus-freshness-guard"',
        'id="copy-review-path-btn"',
        'id="copy-top-replay-btn"',
        'id="copy-commander-brief-btn"',
        'Keep one replay case visible from proof to commander handoff.',
        'Fast path: /api/evals/replays → /api/runtime/brief → /api/incident-command-board.',
        'Replay checkpoint keeps one case key attached from evidence to commander handoff.',
        'Proof freshness keeps replay and runtime timestamps visible before commander handoff.',
        'Commander handoff stays blocked when runtime proof is stale or missing.',
    ]

    for token in required_tokens:
        assert token in html, token
