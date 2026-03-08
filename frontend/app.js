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
    const copyTopReplayBtn = document.getElementById('copy-top-replay-btn');
    const loadReplayBtn = document.getElementById('load-replay-btn');

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
            '',
            'Review sequence',
            ...(sequence.length > 0 ? sequence.map((item) => `- ${item}`) : ['- Review sequence unavailable']),
        ].join('\n');

        try {
            await copyTextToClipboard(text);
            flashButtonLabel(copyReviewPathBtn, 'Copy Review Path', 'Copied');
        } catch (error) {
            console.warn('copy review path failed', error);
            flashButtonLabel(copyReviewPathBtn, 'Copy Review Path', 'Copy failed');
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
            flashButtonLabel(copyReviewRoutesBtn, 'Copy Review Routes', 'Copied');
        } catch (error) {
            console.warn('copy review routes failed', error);
            flashButtonLabel(copyReviewRoutesBtn, 'Copy Review Routes', 'Copy failed');
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
            flashButtonLabel(copyReviewPackBtn, 'Copy Review Pack', 'Copied');
        } catch (error) {
            console.warn('copy review pack failed', error);
            flashButtonLabel(copyReviewPackBtn, 'Copy Review Pack', 'Copy failed');
        }
    }

    function loadTopReplayCase() {
        const topCase = latestReplaySuite?.runs?.[0];
        if (!topCase) {
            flashButtonLabel(loadReplayBtn, 'Load Top Replay', 'Unavailable');
            return;
        }
        focusReplayCase(topCase);
        flashButtonLabel(loadReplayBtn, 'Load Top Replay', 'Loaded');
    }

    async function copyTopReplaySummary() {
        const topCase = latestReplaySuite?.runs?.[0];
        if (!topCase) {
            flashButtonLabel(copyTopReplayBtn, 'Copy Top Replay', 'Unavailable');
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
            flashButtonLabel(copyTopReplayBtn, 'Copy Top Replay', 'Copied');
        } catch (error) {
            console.warn('copy top replay failed', error);
            flashButtonLabel(copyTopReplayBtn, 'Copy Top Replay', 'Copy failed');
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
        } catch (error) {
            replayRefreshState.textContent = 'Unavailable';
            replayCases.innerHTML = '<div class="empty-state">Replay cases could not be loaded.</div>';
            appendToTerminal(`[Error] Failed to load replay suite: ${error.message}`, 'critical');
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
    loadRuntimeBrief().then(() => loadReviewPack());
    loadReplaySuite();
    copyReviewPathBtn.addEventListener('click', copyReviewPath);
    copyReviewRoutesBtn.addEventListener('click', copyReviewRoutes);
    copyReviewPackBtn.addEventListener('click', copyReviewPackSummary);
    copyTopReplayBtn.addEventListener('click', copyTopReplaySummary);
    loadReplayBtn.addEventListener('click', loadTopReplayCase);
});
