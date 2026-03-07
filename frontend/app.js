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

    let isChaosActive = false;
    let currentLine = null;

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

    function renderReplaySuite(data) {
        const summary = data.summary || {};
        replayRefreshState.textContent = 'Loaded';
        replayScore.textContent = `${summary.score_pct || 0}%`;
        replayChecks.textContent = `${summary.passed_checks || 0}/${summary.total_checks || 0}`;
        replaySeverityAccuracy.textContent = `${summary.severity_accuracy_pct || 0}%`;
        replayTaxonomy.textContent = `${summary.taxonomy_coverage_pct || 0}%`;

        replayCases.innerHTML = '';
        (data.runs || []).forEach((run) => {
            const article = document.createElement('article');
            article.className = 'replay-case';
            article.innerHTML = `
                <div class="replay-case__top">
                    <h3>${run.title}</h3>
                    <span class="mini-badge">${run.score_pct}%</span>
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
            const response = await fetch('/api/evals/replays');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            renderReplaySuite(data);
        } catch (error) {
            replayRefreshState.textContent = 'Unavailable';
            replayCases.innerHTML = '<div class="empty-state">Replay cases could not be loaded.</div>';
            appendToTerminal(`[Error] Failed to load replay suite: ${error.message}`, 'critical');
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

        const eventSource = new EventSource('/api/chaos/trigger');

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
            appendToTerminal('[Error] Connection to Aegis-Air was lost. Verify the engine is running on port 8001.', 'critical');
            eventSource.close();
            isChaosActive = false;
            chaosBtn.disabled = false;
            chaosBtn.textContent = 'RUN INCIDENT REVIEW';
            updateStatus('danger', 'DISCONNECTED');
        };
    });

    loadReplaySuite();
});
