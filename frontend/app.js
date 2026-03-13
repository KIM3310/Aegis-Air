document.addEventListener('DOMContentLoaded', () => {
    const chaosBtn = document.getElementById('chaos-btn');
    const terminalOutput = document.getElementById('terminal-output');
    const statusDot = document.getElementById('target-status');
    const metricLatency = document.getElementById('metric-latency');
    const metricError = document.getElementById('metric-error');
    const reportSource = document.getElementById('report-source');
    const reportSeverity = document.getElementById('report-severity');
    const reportBucket = document.getElementById('report-bucket');
    const reportConfidence = document.getElementById('report-confidence');
    const reportSummary = document.getElementById('report-summary');
    const reportEvidence = document.getElementById('report-evidence');
    const reportActions = document.getElementById('report-actions');
    const replayRefreshState = document.getElementById('replay-refresh-state');
    const replayScore = document.getElementById('replay-score');
    const replayChecks = document.getElementById('replay-checks');
    const replaySeverityAccuracy = document.getElementById('replay-severity-accuracy');
    const replayTaxonomy = document.getElementById('replay-taxonomy');
    const replayCases = document.getElementById('replay-cases');
    const driftTopBucket = document.getElementById('drift-top-bucket');
    const driftAttentionRuns = document.getElementById('drift-attention-runs');
    const driftWorstScore = document.getElementById('drift-worst-score');
    const driftVisibleRuns = document.getElementById('drift-visible-runs');
    const driftReviewActions = document.getElementById('drift-review-actions');
    const driftItems = document.getElementById('drift-items');
    const readinessSource = document.getElementById('readiness-source');
    const readinessMode = document.getElementById('readiness-mode');
    const readinessScore = document.getElementById('readiness-score');
    const readinessSchema = document.getElementById('readiness-schema');
    const readinessTarget = document.getElementById('readiness-target');
    const readinessTags = document.getElementById('readiness-tags');
    const readinessReviewFlow = document.getElementById('readiness-review-flow');
    const readinessOperatorRules = document.getElementById('readiness-operator-rules');
    const readinessRequiredFields = document.getElementById('readiness-required-fields');
    const readinessWatchouts = document.getElementById('readiness-watchouts');
    const reviewPackHeadline = document.getElementById('reviewpack-headline');
    const reviewPackProof = document.getElementById('reviewpack-proof');
    const reviewPackTarget = document.getElementById('reviewpack-target');
    const reviewPackArtifacts = document.getElementById('reviewpack-artifacts');
    const reviewPackSequence = document.getElementById('reviewpack-sequence');
    const reviewPackDelivery = document.getElementById('reviewpack-delivery');
    const copyReviewPathBtn = document.getElementById('copy-review-path-btn');
    const copyReviewRoutesBtn = document.getElementById('copy-review-routes-btn');
    const copyReviewPackBtn = document.getElementById('copy-review-pack-btn');
    const copyProofBundleBtn = document.getElementById('copy-proof-bundle-btn');
    const copyHandoffBtn = document.getElementById('copy-handoff-btn');
    const copyCommanderBriefBtn = document.getElementById('copy-commander-brief-btn');
    const copyReadinessClaimBtn = document.getElementById('copy-readiness-claim-btn');
    const copyTopReplayBtn = document.getElementById('copy-top-replay-btn');
    const loadReplayBtn = document.getElementById('load-replay-btn');
    const reviewpackHotkeys = document.getElementById('reviewpack-hotkeys');
    const reviewFocusLabel = document.getElementById('review-focus-label');
    const reviewFocusTitle = document.getElementById('review-focus-title');
    const reviewFocusSummary = document.getElementById('review-focus-summary');
    const reviewFocusBucket = document.getElementById('review-focus-bucket');
    const reviewFocusConfidence = document.getElementById('review-focus-confidence');
    const reviewFocusAction = document.getElementById('review-focus-action');
    const reviewFocusRoute = document.getElementById('review-focus-route');
    const reviewFocusFreshness = document.getElementById('review-focus-freshness');
    const reviewFocusFreshnessNote = document.getElementById('review-focus-freshness-note');
    const lensGrid = document.getElementById('lens-grid');
    const lensReviewerBtn = document.getElementById('lens-reviewer-btn');
    const lensCommanderBtn = document.getElementById('lens-commander-btn');
    const lensRecoveryBtn = document.getElementById('lens-recovery-btn');

    const DEMO_REPLAY_URL = './demo-data/replay-suite.json';
    const DEMO_REPORT_URL = './demo-data/sample-report.json';
    const DEMO_RUNTIME_BRIEF_URL = './demo-data/runtime-brief.json';
    const shouldAutorun = new URLSearchParams(window.location.search).get('autorun') === '1';
    const demoDelayScale = shouldAutorun ? 0.35 : 1;

    let isChaosActive = false;
    let currentLine = null;
    let runtimeMode = 'checking';
    let latestRuntimeBrief = null;
    let latestReplaySuite = null;
    let latestReplayDriftBoard = null;
    let currentLens = 'reviewer';

    const REVIEW_LENSES = {
        reviewer: [
            ['01 · Review path', 'Start with the pack, then read the strongest replay before you talk about the target.'],
            ['02 · Replay proof', 'Use the highest-scoring replay as the first trust-building surface.'],
            ['03 · Handoff', 'Copy the commander brief only after the schema-backed report reads cleanly.'],
        ],
        commander: [
            ['01 · Target claim', 'Open the target boundary and top replay before escalating the incident story.'],
            ['02 · Cmd brief', 'Copy the commander brief once severity, bucket, and evidence align.'],
            ['03 · Proof bundle', 'Use proof routes when the incident needs a fast handoff to the next owner.'],
        ],
        recovery: [
            ['01 · Replay delta', 'Use drift and replay score to explain what improved versus what is still risky.'],
            ['02 · Delivery mode', 'Tell the reviewer whether the proof is recorded, webhook, or live-probe based.'],
            ['03 · Load replay', 'Use Load Replay to move from summary into a concrete recovery example.'],
        ],
    };

    function appendToTerminal(text, type = 'system') {
        const div = document.createElement('div');
        div.className = `log-line ${type}`;
        div.textContent = text;
        terminalOutput.appendChild(div);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
        return div;
    }

    function renderList(target, items) {
        if (!target) return;
        target.innerHTML = '';
        items.forEach((item) => {
            const li = document.createElement('li');
            li.textContent = item;
            target.appendChild(li);
        });
    }

    function renderTagList(target, items) {
        target.innerHTML = '';
        items.forEach((item) => {
            const span = document.createElement('span');
            span.className = 'badge';
            span.textContent = item;
            target.appendChild(span);
        });
    }

    function renderLensCards() {
        if (!lensGrid) return;
        const cards = REVIEW_LENSES[currentLens] || REVIEW_LENSES.reviewer;
        lensGrid.innerHTML = cards.map(([label, body]) => `
            <article class="report-block">
                <span class="section-label">${label}</span>
                <p>${body}</p>
            </article>
        `).join('');
        [lensReviewerBtn, lensCommanderBtn, lensRecoveryBtn].forEach((btn) => btn?.classList.remove('active'));
        if (currentLens === 'reviewer') lensReviewerBtn?.classList.add('active');
        if (currentLens === 'commander') lensCommanderBtn?.classList.add('active');
        if (currentLens === 'recovery') lensRecoveryBtn?.classList.add('active');
    }

    function replayCaseKey(run) {
        return String(run?.id || run?.title || run?.scenario || '').trim();
    }

    function formatIsoStamp(value) {
        if (!value) return 'pending';
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) return String(value);
        return parsed.toISOString().replace('.000Z', 'Z');
    }

    function buildProofFreshnessLabel(run) {
        const replayStamp = run?.generated_at
            || latestReplaySuite?.generated_at
            || latestReplayDriftBoard?.generated_at
            || null;
        const runtimeStamp = latestRuntimeBrief?.generated_at || null;
        return `Replay ${formatIsoStamp(replayStamp)} · runtime ${formatIsoStamp(runtimeStamp)}`;
    }

    function buildProofFreshnessNote(run) {
        const runtimeStamp = latestRuntimeBrief?.generated_at;
        if (runtimeStamp) {
            return `Proof freshness keeps replay and runtime timestamps visible before commander handoff. Runtime brief: ${formatIsoStamp(runtimeStamp)}.`;
        }
        if (run?.generated_at || latestReplaySuite?.generated_at || latestReplayDriftBoard?.generated_at) {
            return `Proof freshness keeps replay and runtime timestamps visible before commander handoff. Replay evidence is loaded, but runtime proof still needs a fresh brief.`;
        }
        return 'Proof freshness keeps replay and runtime timestamps visible before commander handoff.';
    }

    function markReplaySelection(run) {
        const activeKey = replayCaseKey(run);
        replayCases?.querySelectorAll('.replay-case').forEach((item) => {
            item.classList.toggle('is-selected', item.dataset.replayKey === activeKey);
        });
    }

    function renderReplayFocus(run, label = 'Replay continuity') {
        const report = run?.report || {};
        const confidenceValue = typeof report.confidence === 'number'
            ? `${Math.round(report.confidence * 100)}%`
            : (typeof run?.confidence === 'number' ? `${Math.round(run.confidence * 100)}%` : '--');
        const runtimeRoute = latestRuntimeBrief?.links?.incident_command_board || '/api/incident-command-board';
        if (reviewFocusLabel) reviewFocusLabel.textContent = label;
        if (reviewFocusTitle) reviewFocusTitle.textContent = run?.title || 'Keep one replay case visible from proof to commander handoff.';
        if (reviewFocusSummary) {
            reviewFocusSummary.textContent = report.summary
                || run?.summary
                || 'Start with the top replay, keep its bucket and confidence visible, then move into the command brief without losing the incident thread.';
        }
        if (reviewFocusBucket) reviewFocusBucket.textContent = run?.failure_bucket || report.failure_bucket || '--';
        if (reviewFocusConfidence) reviewFocusConfidence.textContent = confidenceValue;
        if (reviewFocusAction) reviewFocusAction.textContent = report.immediate_actions?.[0]
            || run?.next_action
            || 'Copy the commander brief after the replay summary reads cleanly.';
        if (reviewFocusRoute) {
            reviewFocusRoute.textContent = `Fast path: /api/evals/replays → /api/runtime/brief → ${runtimeRoute}.`;
        }
        if (reviewFocusFreshness) reviewFocusFreshness.textContent = buildProofFreshnessLabel(run);
        if (reviewFocusFreshnessNote) reviewFocusFreshnessNote.textContent = buildProofFreshnessNote(run);
        markReplaySelection(run);
    }

    async function copyTextToClipboard(text) {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
            return;
        }

        const helper = document.createElement('textarea');
        helper.value = text;
        helper.setAttribute('readonly', 'true');
        helper.style.position = 'absolute';
        helper.style.left = '-9999px';
        document.body.appendChild(helper);
        helper.select();
        document.execCommand('copy');
        helper.remove();
    }

    function flashButtonLabel(button, idleLabel, nextLabel) {
        if (!button) return;
        button.textContent = nextLabel;
        window.setTimeout(() => {
            button.textContent = idleLabel;
        }, 1400);
    }

    function updateStatus(state, label) {
        statusDot.className = `status ${state}`;
        statusDot.textContent = `● ${label}`;
    }

    function delay(ms) {
        return new Promise((resolve) => window.setTimeout(resolve, Math.max(12, Math.round(ms * demoDelayScale))));
    }

    async function fetchJson(url) {
        const response = await fetch(url, { headers: { Accept: 'application/json' } });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const contentType = (response.headers.get('content-type') || '').toLowerCase();
        if (!contentType.includes('application/json')) {
            throw new Error('Expected JSON response');
        }
        return response.json();
    }

    function chunkText(text, chunkSize = 34) {
        const words = String(text || '').split(/\s+/).filter(Boolean);
        const chunks = [];
        let current = '';

        words.forEach((word) => {
            const candidate = `${current} ${word}`.trim();
            if (candidate.length <= chunkSize) {
                current = candidate;
                return;
            }
            if (current) chunks.push(`${current} `);
            current = word;
        });

        if (current) chunks.push(`${current} `);
        return chunks;
    }

    async function fetchJsonWithFallback(primaryUrl, fallbackUrl) {
        try {
            return { data: await fetchJson(primaryUrl), source: 'live' };
        } catch (_) {
            const fallback = await fetchJson(fallbackUrl);
            return { data: fallback, source: 'demo' };
        }
    }

    async function detectRuntimeMode() {
        try {
            await fetchJson('/api/meta');
            runtimeMode = 'live';
            chaosBtn.textContent = 'RUN INCIDENT REVIEW';
            appendToTerminal('[System] Live engine detected.', 'system');
        } catch (_) {
            runtimeMode = 'demo';
            chaosBtn.textContent = 'RUN RECORDED REVIEW';
            appendToTerminal('[System] No live engine detected. Using recorded review data.', 'system');
        }
    }

    function renderReport(report, sourceLabel) {
        if (!report) return;

        const metrics = report.metrics || {};
        reportSource.textContent = sourceLabel;
        reportSeverity.textContent = report.severity || '--';
        reportBucket.textContent = report.failure_bucket || '--';
        reportConfidence.textContent = typeof report.confidence === 'number'
            ? `${Math.round(report.confidence * 100)}%`
            : '--';
        reportSummary.textContent = report.summary || 'No summary available.';
        renderList(reportEvidence, report.supporting_evidence || ['No evidence captured.']);
        renderList(reportActions, report.immediate_actions || ['No action items generated.']);

        if (typeof metrics.p95_latency_ms === 'number') {
            metricLatency.textContent = `${metrics.p95_latency_ms}ms`;
        }
        if (typeof metrics.error_rate === 'number') {
            metricError.textContent = `${(metrics.error_rate * 100).toFixed(1)}%`;
        }
    }

    function renderReplaySuite(data, source) {
        latestReplaySuite = data;
        const summary = data.summary || {};
        replayRefreshState.textContent = source === 'demo' ? 'Recorded' : 'Loaded';
        replayScore.textContent = `${summary.score_pct || 0}%`;
        replayChecks.textContent = `${summary.passed_checks || 0}/${summary.total_checks || 0}`;
        replaySeverityAccuracy.textContent = `${summary.severity_accuracy_pct || 0}%`;
        replayTaxonomy.textContent = `${summary.taxonomy_coverage_pct || 0}%`;

        replayCases.innerHTML = '';
        (data.runs || []).forEach((run) => {
            const scorePct = typeof run.score_pct === 'number'
                ? run.score_pct
                : Math.round(((run.passed_checks || 0) / Math.max(run.total_checks || 1, 1)) * 1000) / 10;
            const article = document.createElement('article');
            article.className = 'replay-case is-clickable';
            article.dataset.replayKey = replayCaseKey(run);
            article.tabIndex = 0;
            article.setAttribute('role', 'button');
            article.innerHTML = `
                <div class="replay-case__top">
                    <h3>${run.title}</h3>
                    <span class="mini-badge">${scorePct}%</span>
                </div>
                <div class="replay-case__meta">
                    <span>${run.severity}</span>
                    <span>${run.failure_bucket}</span>
                    <span>${run.passed_checks}/${run.total_checks} checks</span>
                </div>
                <p>${run.report.summary}</p>
                <div class="replay-case__hint">Press to focus this replay case</div>
            `;
            const focusCase = () => focusReplayCase(run);
            article.addEventListener('click', focusCase);
            article.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    focusCase();
                }
            });
            replayCases.appendChild(article);
        });
        if ((data.runs || []).length > 0) {
            renderReplayFocus(data.runs[0]);
        }
    }

    function deriveReplayDriftBoardFromReplaySuite(data) {
        const runs = Array.isArray(data?.runs) ? data.runs : [];
        const bucketCounts = {};
        const items = runs
            .map((run) => {
                bucketCounts[run.failure_bucket] = (bucketCounts[run.failure_bucket] || 0) + 1;
                const driftSignals = [];
                if (run.severity === 'SEV1') driftSignals.push('sev1-case');
                if ((run.score_pct || 0) < 100) driftSignals.push('regression-gap');
                return {
                    case_id: run.case_id,
                    title: run.title,
                    severity: run.severity,
                    failure_bucket: run.failure_bucket,
                    score_pct: run.score_pct || 0,
                    drift_signals: driftSignals,
                    next_action: run.report?.immediate_actions?.[0] || 'Review the replay evidence before sharing this incident.',
                    summary: run.report?.summary || 'No replay summary available.',
                };
            })
            .sort((left, right) => {
                const severityRank = { SEV1: 0, SEV2: 1, SEV3: 2 };
                return (
                    (severityRank[left.severity] ?? 99) - (severityRank[right.severity] ?? 99) ||
                    (left.score_pct || 0) - (right.score_pct || 0)
                );
            });

        const topBucket = Object.entries(bucketCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || '--';
        return {
            summary: {
                visible_runs: items.length,
                top_failure_bucket: topBucket,
                attention_runs: items.filter((item) => item.drift_signals.length > 0).length,
                worst_score_pct: items.length > 0 ? Math.min(...items.map((item) => item.score_pct || 0)) : 0,
            },
            items,
            review_actions: [
                'Use the drift board to keep the riskiest replay bucket visible before demo handoff.',
                'Separate replay drift from live target reachability when explaining readiness.',
                'Pair this with the review pack and scorecard before claiming incident stability.',
            ],
        };
    }

    function renderReplayDriftBoard(data) {
        latestReplayDriftBoard = data;
        const summary = data?.summary || {};
        driftTopBucket.textContent = summary.top_failure_bucket || '--';
        driftAttentionRuns.textContent = `${summary.attention_runs ?? 0}`;
        driftWorstScore.textContent = typeof summary.worst_score_pct === 'number'
            ? `${summary.worst_score_pct}%`
            : '--';
        driftVisibleRuns.textContent = `${summary.visible_runs ?? 0}`;
        renderList(driftReviewActions, data?.review_actions || ['No drift review actions available.']);

        driftItems.innerHTML = '';
        const items = Array.isArray(data?.items) ? data.items : [];
        if (items.length === 0) {
            driftItems.innerHTML = '<div class="empty-state">No replay drift signals available.</div>';
            return;
        }

        items.slice(0, 3).forEach((item) => {
            const article = document.createElement('article');
            article.className = 'replay-case';
            article.innerHTML = `
                <div class="replay-case__top">
                    <h3>${item.title}</h3>
                    <span class="mini-badge">${item.score_pct ?? '--'}%</span>
                </div>
                <div class="replay-case__meta">
                    <span>${item.severity || '--'}</span>
                    <span>${item.failure_bucket || '--'}</span>
                    <span>${(item.drift_signals || []).join(', ') || 'stable'}</span>
                </div>
                <p>${item.summary || 'No summary available.'}</p>
                <div class="replay-case__hint">${item.next_action || 'Review this replay before handoff.'}</div>
            `;
            driftItems.appendChild(article);
        });
    }

    function renderRuntimeBrief(data, source) {
        latestRuntimeBrief = data;
        const replaySummary = data.replay_summary || {};
        const reportContract = data.report_contract || {};
        const targetService = data.target_service || {};

        readinessSource.textContent = source === 'demo' ? 'Recorded profile' : 'Live engine';
        readinessMode.textContent = data.mode || '--';
        readinessScore.textContent = `${replaySummary.score_pct || 0}%`;
        readinessSchema.textContent = reportContract.schema || '--';
        readinessTarget.textContent = targetService.status || '--';

        renderTagList(readinessTags, [
            data.readiness_contract || 'runtime-brief',
            `cases:${replaySummary.cases || 0}`,
            `checks:${replaySummary.total_checks || 0}`,
            `bucket:${replaySummary.bucket_accuracy_pct || 0}%`,
        ]);
        renderList(readinessReviewFlow, data.review_flow || ['No review flow available.']);
        renderList(readinessOperatorRules, data.operator_rules || ['No operator rules available.']);
        renderList(readinessRequiredFields, reportContract.required_fields || ['No schema fields available.']);
        renderList(readinessWatchouts, data.watchouts || ['No watchouts available.']);
    }

    function deriveReviewPackFromRuntime(data) {
        const reportContract = data.report_contract || {};
        const replaySummary = data.replay_summary || {};
        const targetService = data.target_service || {};
        return {
            headline: 'Reviewer-first pack for replay evidence, target reachability, and downstream handoff readiness in air-gapped environments.',
            proof_bundle: {
                replay_cases: replaySummary.cases || 0,
                rubric_checks: replaySummary.total_checks || 0,
                score_pct: replaySummary.score_pct || 0,
            },
            target_boundary: {
                status: targetService.status || 'unavailable',
                service: targetService.service || 'unknown',
            },
            handoff_contract: {
                delivery_modes: reportContract.delivery_modes || [],
            },
            two_minute_review: data.two_minute_review || [],
            artifacts: data.artifacts || [],
            proof_assets: data.proof_assets || [],
            review_sequence: [
                'Confirm /health and /api/meta before claiming live target readiness.',
                'Read /api/runtime/brief for replay score and trust boundary.',
                'Run live or recorded incident review only after schema and replay evidence align.',
            ],
        };
    }

    function renderReviewPack(data) {
        const proofBundle = data.proof_bundle || {};
        const targetBoundary = data.target_boundary || {};
        const handoffContract = data.handoff_contract || {};
        const artifacts = data.artifacts || [];
        const proofAssets = data.proof_assets || [];
        const twoMinuteReview = data.two_minute_review || [];

        reviewPackHeadline.textContent = data.headline || 'No reviewer pack headline available.';
        reviewPackProof.textContent = `${proofBundle.score_pct || 0}% / ${proofBundle.rubric_checks || 0} checks`;
        reviewPackTarget.textContent = `${targetBoundary.status || '--'} · ${targetBoundary.service || '--'}`;
        renderList(
            reviewPackArtifacts,
            [
                ...proofAssets.map((item) => `[Proof] ${item.label} -> ${item.href || item.path || '-'}`),
                ...artifacts.map((item) => `${item.label} -> ${item.href || item.path || '-'}`),
            ]
        );
        renderList(
            reviewPackSequence,
            [
                ...twoMinuteReview.map((item) => `2-minute: ${item}`),
                ...(data.review_sequence || []),
            ]
        );
        renderList(reviewPackDelivery, handoffContract.delivery_modes || ['No delivery modes available.']);
    }

    function focusReplayCase(run) {
        if (!run?.report) return;
        renderReport(run.report, `Replay focus · ${run.title}`);
        renderReplayFocus(run, 'Focused replay');
        updateStatus('review', 'REPLAY FOCUS');
        appendToTerminal(`[Review] Loaded replay case "${run.title}" into the incident panel.`, 'system');
    }

    async function copyReviewPath() {
        const sequence = Array.from(reviewPackSequence.querySelectorAll('li'))
            .map((item) => item.textContent?.trim())
            .filter(Boolean);
        const text = [
            'Aegis-Air review path',
            `Headline: ${reviewPackHeadline.textContent || '-'}`,
            `Proof bundle: ${reviewPackProof.textContent || '-'}`,
            `Target boundary: ${reviewPackTarget.textContent || '-'}`,
            `Proof freshness: ${reviewFocusFreshness?.textContent || '-'}`,
            '',
            'Review sequence',
            ...(sequence.length > 0 ? sequence.map((item) => `- ${item}`) : ['- Review sequence unavailable']),
        ].join('\n');

        try {
            await copyTextToClipboard(text);
            flashButtonLabel(copyReviewPathBtn, 'Review Path', 'Copied');
        } catch (error) {
            console.warn('copy review path failed', error);
            flashButtonLabel(copyReviewPathBtn, 'Review Path', 'Copy failed');
        }
    }

    async function copyReviewRoutes() {
        const routes = Array.from(reviewPackArtifacts.querySelectorAll('li'))
            .map((item) => item.textContent?.trim())
            .filter(Boolean);
        const runtimeLinks = latestRuntimeBrief?.links
            ? Object.entries(latestRuntimeBrief.links).map(([label, href]) => `${label}: ${href}`)
            : [];
        const text = [
            'Aegis-Air review routes',
            ...routes.map((item) => `- ${item}`),
            ...(runtimeLinks.length > 0 ? ['', 'Runtime links', ...runtimeLinks.map((item) => `- ${item}`)] : []),
        ].join('\n');

        try {
            await copyTextToClipboard(text);
            flashButtonLabel(copyReviewRoutesBtn, 'Review Routes', 'Copied');
        } catch (error) {
            console.warn('copy review routes failed', error);
            flashButtonLabel(copyReviewRoutesBtn, 'Review Routes', 'Copy failed');
        }
    }

    async function copyReviewPackSummary() {
        const sequence = Array.from(reviewPackSequence.querySelectorAll('li'))
            .map((item) => item.textContent?.trim())
            .filter(Boolean);
        const artifacts = Array.from(reviewPackArtifacts.querySelectorAll('li'))
            .map((item) => item.textContent?.trim())
            .filter(Boolean);
        const text = [
            'Aegis-Air review pack',
            `Headline: ${reviewPackHeadline.textContent || '-'}`,
            `Proof bundle: ${reviewPackProof.textContent || '-'}`,
            `Target boundary: ${reviewPackTarget.textContent || '-'}`,
            '',
            'Review sequence',
            ...(sequence.length > 0 ? sequence.map((item) => `- ${item}`) : ['- Review sequence unavailable']),
            '',
            'Artifacts',
            ...(artifacts.length > 0 ? artifacts.map((item) => `- ${item}`) : ['- Review artifacts unavailable']),
        ].join('\n');

        try {
            await copyTextToClipboard(text);
            flashButtonLabel(copyReviewPackBtn, 'Review Pack', 'Copied');
        } catch (error) {
            console.warn('copy review pack failed', error);
            flashButtonLabel(copyReviewPackBtn, 'Review Pack', 'Copy failed');
        }
    }

    async function copyHandoffSnapshot() {
        const deliveryModes = Array.from(reviewPackDelivery.querySelectorAll('li'))
            .map((item) => item.textContent?.trim())
            .filter(Boolean);
        const topCase = latestReplaySuite?.runs?.[0];
        const report = topCase?.report || {};
        const text = [
            'Aegis-Air handoff snapshot',
            `Headline: ${reviewPackHeadline.textContent || '-'}`,
            `Proof bundle: ${reviewPackProof.textContent || '-'}`,
            `Target boundary: ${reviewPackTarget.textContent || '-'}`,
            `Proof freshness: ${reviewFocusFreshness?.textContent || '-'}`,
            `Top replay: ${topCase?.title || '-'}`,
            `Severity: ${topCase?.severity || report.severity || '-'}`,
            `Bucket: ${topCase?.failure_bucket || report.failure_bucket || '-'}`,
            '',
            'Delivery modes',
            ...(deliveryModes.length > 0 ? deliveryModes.map((item) => `- ${item}`) : ['- Delivery modes unavailable']),
        ].join('\n');

        try {
            await copyTextToClipboard(text);
            flashButtonLabel(copyHandoffBtn, 'Handoff Snapshot', 'Copied');
        } catch (error) {
            console.warn('copy handoff snapshot failed', error);
            flashButtonLabel(copyHandoffBtn, 'Handoff Snapshot', 'Copy failed');
        }
    }

    async function copyCommanderBrief() {
        const topCase = latestReplaySuite?.runs?.[0];
        const report = topCase?.report || {};
        const immediateActions = Array.isArray(report.immediate_actions) ? report.immediate_actions : [];
        const evidence = Array.isArray(report.supporting_evidence) ? report.supporting_evidence : [];
        const runtimeLinks = latestRuntimeBrief?.links
            ? Object.entries(latestRuntimeBrief.links).slice(0, 4).map(([label, href]) => `- ${label}: ${href}`)
            : [];
        const text = [
            'Aegis-Air commander brief',
            `Runtime mode: ${runtimeMode}`,
            `Headline: ${reviewPackHeadline.textContent || '-'}`,
            `Proof bundle: ${reviewPackProof.textContent || '-'}`,
            `Target boundary: ${reviewPackTarget.textContent || '-'}`,
            `Proof freshness: ${reviewFocusFreshness?.textContent || '-'}`,
            `Top replay: ${topCase?.title || '-'}`,
            `Severity: ${topCase?.severity || report.severity || '-'}`,
            `Failure bucket: ${topCase?.failure_bucket || report.failure_bucket || '-'}`,
            `Summary: ${report.summary || 'No summary available.'}`,
            `Next action: ${immediateActions[0] || 'Review runtime brief and replay evidence before escalating.'}`,
            '',
            'Immediate actions',
            ...(immediateActions.length > 0 ? immediateActions.slice(0, 3).map((item) => `- ${item}`) : ['- No immediate actions available.']),
            '',
            'Evidence',
            ...(evidence.length > 0 ? evidence.slice(0, 3).map((item) => `- ${item}`) : ['- No evidence captured.']),
            ...(runtimeLinks.length > 0 ? ['', 'Fast routes', ...runtimeLinks] : []),
        ].join('\n');

        try {
            await copyTextToClipboard(text);
            flashButtonLabel(copyCommanderBriefBtn, 'Commander Brief', 'Copied');
        } catch (error) {
            console.warn('copy commander brief failed', error);
            flashButtonLabel(copyCommanderBriefBtn, 'Commander Brief', 'Copy failed');
        }
    }

    async function copyReadinessClaim() {
        const topCase = latestReplaySuite?.runs?.[0];
        const report = topCase?.report || {};
        const text = [
            'Aegis-Air readiness claim',
            `Headline: ${reviewPackHeadline.textContent || '-'}`,
            `Proof bundle: ${reviewPackProof.textContent || '-'}`,
            `Target boundary: ${reviewPackTarget.textContent || '-'}`,
            `Proof freshness: ${reviewFocusFreshness?.textContent || '-'}`,
            `Replay score: ${replayScore.textContent || '-'}`,
            `Severity accuracy: ${replaySeverityAccuracy.textContent || '-'}`,
            `Top replay: ${topCase?.title || '-'}`,
            `Bucket: ${topCase?.failure_bucket || report.failure_bucket || '-'}`,
            `Action: ${(report.immediate_actions || [])[0] || 'unavailable'}`,
            '',
            'Fast routes',
            '- /api/runtime/brief',
            '- /api/review-pack',
            '- /api/evals/replays',
        ].join('\n');

        try {
            await copyTextToClipboard(text);
            flashButtonLabel(copyReadinessClaimBtn, 'Readiness Claim', 'Copied');
        } catch (error) {
            console.warn('copy readiness claim failed', error);
            flashButtonLabel(copyReadinessClaimBtn, 'Readiness Claim', 'Copy failed');
        }
    }

    async function copyProofBundle() {
        const artifacts = Array.from(reviewPackArtifacts.querySelectorAll('li'))
            .map((item) => item.textContent?.trim())
            .filter(Boolean);
        const sequence = Array.from(reviewPackSequence.querySelectorAll('li'))
            .map((item) => item.textContent?.trim())
            .filter(Boolean);
        const text = [
            'Aegis-Air proof bundle',
            `Headline: ${reviewPackHeadline.textContent || '-'}`,
            `Proof bundle: ${reviewPackProof.textContent || '-'}`,
            `Replay score: ${replayScore.textContent || '-'}`,
            '',
            'Fast routes',
            '- /api/runtime/brief',
            '- /api/review-pack',
            '- /api/evals/replays',
            '',
            'Artifacts',
            ...(artifacts.length > 0 ? artifacts.map((item) => `- ${item}`) : ['- Review artifacts unavailable.']),
            '',
            'Review sequence',
            ...(sequence.length > 0 ? sequence.slice(0, 5).map((item) => `- ${item}`) : ['- Review sequence unavailable.']),
        ].join('\n');

        try {
            await copyTextToClipboard(text);
            flashButtonLabel(copyProofBundleBtn, 'Proof Bundle', 'Copied');
        } catch (error) {
            console.warn('copy proof bundle failed', error);
            flashButtonLabel(copyProofBundleBtn, 'Proof Bundle', 'Copy failed');
        }
    }

    function loadTopReplayCase() {
        const topCase = latestReplaySuite?.runs?.[0];
        if (!topCase) {
            flashButtonLabel(loadReplayBtn, 'Load Replay', 'Unavailable');
            return;
        }
        focusReplayCase(topCase);
        flashButtonLabel(loadReplayBtn, 'Load Replay', 'Loaded');
    }

    async function copyTopReplaySummary() {
        const topCase = latestReplaySuite?.runs?.[0];
        if (!topCase) {
            flashButtonLabel(copyTopReplayBtn, 'Top Replay', 'Unavailable');
            return;
        }

        const report = topCase.report || {};
        const evidence = Array.isArray(report.supporting_evidence) ? report.supporting_evidence : [];
        const actions = Array.isArray(report.immediate_actions) ? report.immediate_actions : [];
        const text = [
            'Aegis-Air top replay summary',
            `Title: ${topCase.title || '-'}`,
            `Severity: ${topCase.severity || report.severity || '-'}`,
            `Failure bucket: ${topCase.failure_bucket || report.failure_bucket || '-'}`,
            `Checks: ${topCase.passed_checks || 0}/${topCase.total_checks || 0}`,
            `Summary: ${report.summary || 'No summary available.'}`,
            '',
            'Evidence',
            ...(evidence.length > 0 ? evidence.map((item) => `- ${item}`) : ['- No evidence captured.']),
            '',
            'Actions',
            ...(actions.length > 0 ? actions.map((item) => `- ${item}`) : ['- No actions generated.']),
        ].join('\n');

        try {
            await copyTextToClipboard(text);
            flashButtonLabel(copyTopReplayBtn, 'Top Replay', 'Copied');
        } catch (error) {
            console.warn('copy top replay failed', error);
            flashButtonLabel(copyTopReplayBtn, 'Top Replay', 'Copy failed');
        }
    }

    async function loadRuntimeBrief() {
        try {
            const { data, source } = await fetchJsonWithFallback('/api/runtime/brief', DEMO_RUNTIME_BRIEF_URL);
            renderRuntimeBrief(data, source);
            return data;
        } catch (error) {
            readinessSource.textContent = 'Unavailable';
            appendToTerminal(`[Error] Failed to load runtime brief: ${error.message}`, 'critical');
            return null;
        }
    }

    async function loadReviewPack() {
        try {
            const data = await fetchJson('/api/review-pack');
            renderReviewPack(data);
        } catch (_) {
            if (latestRuntimeBrief) {
                renderReviewPack(deriveReviewPackFromRuntime(latestRuntimeBrief));
                return;
            }
            reviewPackHeadline.textContent = 'Review pack unavailable.';
            renderList(reviewPackArtifacts, ['No review artifacts available.']);
            renderList(reviewPackSequence, ['Load /api/runtime/brief or /api/review-pack when the engine is available.']);
            renderList(reviewPackDelivery, ['No delivery modes available.']);
            reviewPackProof.textContent = '--';
            reviewPackTarget.textContent = '--';
        }
    }

    async function loadReplaySuite() {
        replayRefreshState.textContent = 'Loading...';
        try {
            const { data, source } = await fetchJsonWithFallback('/api/evals/replays', DEMO_REPLAY_URL);
            renderReplaySuite(data, source);
            return data;
        } catch (error) {
            replayRefreshState.textContent = 'Unavailable';
            replayCases.innerHTML = '<div class="empty-state">Replay cases could not be loaded.</div>';
            appendToTerminal(`[Error] Failed to load replay suite: ${error.message}`, 'critical');
            return null;
        }
    }

    async function loadReplayDriftBoard() {
        try {
            const data = await fetchJson('/api/replay-drift-board');
            renderReplayDriftBoard(data);
            return data;
        } catch (_) {
            if (latestReplaySuite) {
                const derived = deriveReplayDriftBoardFromReplaySuite(latestReplaySuite);
                renderReplayDriftBoard(derived);
                return derived;
            }
            renderList(driftReviewActions, ['Replay drift board unavailable.']);
            driftItems.innerHTML = '<div class="empty-state">Replay drift board unavailable.</div>';
            return null;
        }
    }

    async function playRecordedReview() {
        try {
            const { data: report } = await fetchJsonWithFallback(DEMO_REPORT_URL, DEMO_REPORT_URL);

            terminalOutput.innerHTML = '';
            appendToTerminal('[System] Running recorded incident review.', 'system');
            updateStatus('review', 'REPLAY');
            metricLatency.textContent = '--';
            metricError.textContent = '--';

            const scriptedLogs = [
                '[Replay] Loading checkout database connection loss scenario.\n',
                '[Probe 1] -> GET https://checkout.example/api/checkout\n',
                '      SUCCESS 200 in 82 ms\n',
                '[Probe 2] -> GET https://checkout.example/api/checkout\n',
                '      INCIDENT SIGNAL 500: database connection lost to postgres-primary\n',
                '[Probe 3] -> GET https://checkout.example/api/checkout\n',
                '      INCIDENT SIGNAL 500: checkout transaction failed after dependency disconnect\n',
                '\n[Aegis-Air] Structured incident report loaded from recorded data.\n',
                '[Aegis-Air] Drafting concise operator handoff.\n\n',
            ];

            for (const message of scriptedLogs) {
                appendToTerminal(message, message.includes('INCIDENT') ? 'critical' : 'system');
                await delay(180);
            }

            renderReport(report, 'Recorded review');
            currentLine = appendToTerminal('', 'ai-token');
            for (const chunk of chunkText(report.rca_report || '')) {
                currentLine.textContent += chunk;
                terminalOutput.scrollTop = terminalOutput.scrollHeight;
                await delay(18);
            }

            currentLine = null;
            appendToTerminal('\n[System] Recorded review complete.', 'system');
            updateStatus('review', 'READY');
        } catch (error) {
            appendToTerminal(`[Error] Recorded review failed to load: ${error.message}`, 'critical');
            updateStatus('danger', 'UNAVAILABLE');
        } finally {
            isChaosActive = false;
            chaosBtn.disabled = false;
            chaosBtn.textContent = runtimeMode === 'demo' ? 'RUN RECORDED REVIEW' : 'RUN INCIDENT REVIEW';
        }
    }

    chaosBtn.addEventListener('click', () => {
        if (isChaosActive) return;

        isChaosActive = true;
        currentLine = null;
        chaosBtn.disabled = true;
        chaosBtn.textContent = 'RUNNING REVIEW...';
        updateStatus('review', 'SAMPLING');
        metricLatency.textContent = '--';
        metricError.textContent = '--';
        terminalOutput.innerHTML = '';
        appendToTerminal('[Admin] Incident review started.', 'system');

        if (runtimeMode === 'demo') {
            playRecordedReview();
            return;
        }

        const eventSource = new EventSource('/api/chaos/trigger');
        let reportSeen = false;

        eventSource.onmessage = function (event) {
            const data = JSON.parse(event.data);

            if (data.type === 'log') {
                const message = data.content || '';
                const variant = message.includes('INCIDENT') || message.includes('Structured incident report')
                    ? 'critical'
                    : 'system';
                appendToTerminal(message, variant);
                currentLine = null;
                return;
            }

            if (data.type === 'token') {
                if (!currentLine) {
                    currentLine = appendToTerminal('', 'ai-token');
                }
                currentLine.textContent += data.content;
                terminalOutput.scrollTop = terminalOutput.scrollHeight;
                return;
            }

            if (data.type === 'report') {
                reportSeen = true;
                currentLine = null;
                renderReport(data.content, 'Live probe');
                updateStatus('danger', 'INCIDENT REVIEWED');
                appendToTerminal('[System] Structured report published to the incident panel.', 'system');
                return;
            }

            if (data.type === 'done') {
                eventSource.close();
                isChaosActive = false;
                chaosBtn.disabled = false;
                chaosBtn.textContent = 'RUN INCIDENT REVIEW';
                if ((data.content || {}).status === 'no-incident') {
                    updateStatus('healthy', 'NO INCIDENT');
                } else {
                    updateStatus('review', 'READY');
                }
                appendToTerminal('[System] Stream terminated.', 'system');
            }
        };

        eventSource.onerror = function () {
            eventSource.close();
            if (!reportSeen) {
                runtimeMode = 'demo';
                appendToTerminal('[System] Live API unavailable. Switching to recorded review.', 'system');
                playRecordedReview();
                return;
            }
            appendToTerminal('[Error] Connection to Aegis-Air was lost. Verify the engine is running on port 8001.', 'critical');
            isChaosActive = false;
            chaosBtn.disabled = false;
            chaosBtn.textContent = 'RUN INCIDENT REVIEW';
            updateStatus('danger', 'DISCONNECTED');
        };
    });

    detectRuntimeMode().then(() => {
        if (shouldAutorun && !isChaosActive) {
            chaosBtn.click();
        }
    });
    Promise.all([loadRuntimeBrief(), loadReplaySuite()]).then(() => {
        loadReviewPack();
        loadReplayDriftBoard();
    });
    renderLensCards();
    copyReviewPathBtn.addEventListener('click', copyReviewPath);
    copyReviewRoutesBtn.addEventListener('click', copyReviewRoutes);
    copyReviewPackBtn.addEventListener('click', copyReviewPackSummary);
    copyProofBundleBtn.addEventListener('click', copyProofBundle);
    copyHandoffBtn.addEventListener('click', copyHandoffSnapshot);
    copyCommanderBriefBtn.addEventListener('click', copyCommanderBrief);
    copyReadinessClaimBtn.addEventListener('click', copyReadinessClaim);
    copyTopReplayBtn.addEventListener('click', copyTopReplaySummary);
    loadReplayBtn.addEventListener('click', loadTopReplayCase);
    lensReviewerBtn?.addEventListener('click', () => { currentLens = 'reviewer'; renderLensCards(); });
    lensCommanderBtn?.addEventListener('click', () => { currentLens = 'commander'; renderLensCards(); });
    lensRecoveryBtn?.addEventListener('click', () => { currentLens = 'recovery'; renderLensCards(); });
    document.addEventListener('keydown', (event) => {
        const tag = String(event.target?.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select' || event.metaKey || event.ctrlKey || event.altKey) {
            return;
        }
        const key = event.key.toLowerCase();
        if (key === '?') {
            if (reviewpackHotkeys) {
                reviewpackHotkeys.textContent = 'Keyboard: R routes · P pack · B proof bundle · X commander brief · T top replay · L load replay.';
            }
            return;
        }
        if (key === 'c') {
            event.preventDefault();
            chaosBtn.click();
        }
        if (key === 'l') {
            event.preventDefault();
            loadReplayBtn.click();
        }
        if (key === 'r') {
            event.preventDefault();
            copyReviewRoutesBtn.click();
        }
        if (key === 'p') {
            event.preventDefault();
            copyReviewPackBtn.click();
        }
        if (key === 'b') {
            event.preventDefault();
            copyProofBundleBtn.click();
        }
        if (key === 'x') {
            event.preventDefault();
            copyCommanderBriefBtn.click();
        }
    });
});
