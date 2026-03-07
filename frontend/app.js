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

    const DEMO_REPLAY_URL = './demo-data/replay-suite.json';
    const DEMO_REPORT_URL = './demo-data/sample-report.json';
    const shouldAutorun = new URLSearchParams(window.location.search).get('autorun') === '1';

    let isChaosActive = false;
    let currentLine = null;
    let runtimeMode = 'checking';

    function appendToTerminal(text, type = 'system') {
        const div = document.createElement('div');
        div.className = `log-line ${type}`;
        div.textContent = text;
        terminalOutput.appendChild(div);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
        return div;
    }

    function renderList(target, items) {
        target.innerHTML = '';
        items.forEach((item) => {
            const li = document.createElement('li');
            li.textContent = item;
            target.appendChild(li);
        });
    }

    function updateStatus(state, label) {
        statusDot.className = `status ${state}`;
        statusDot.textContent = `● ${label}`;
    }

    function delay(ms) {
        return new Promise((resolve) => window.setTimeout(resolve, ms));
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
            const response = await fetch(primaryUrl, { headers: { Accept: 'application/json' } });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return { data: await response.json(), source: 'live' };
        } catch (_) {
            const fallback = await fetch(fallbackUrl, { headers: { Accept: 'application/json' } });
            if (!fallback.ok) throw new Error(`Fallback HTTP ${fallback.status}`);
            return { data: await fallback.json(), source: 'demo' };
        }
    }

    async function detectRuntimeMode() {
        try {
            const response = await fetch('/api/meta', { headers: { Accept: 'application/json' } });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
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
            article.className = 'replay-case';
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
            `;
            replayCases.appendChild(article);
        });
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
    loadReplaySuite();
});
