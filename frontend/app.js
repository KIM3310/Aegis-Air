document.addEventListener('DOMContentLoaded', () => {
    const chaosBtn = document.getElementById('chaos-btn');
    const terminalOutput = document.getElementById('terminal-output');
    const statusDot = document.getElementById('target-status');
    const metricLatency = document.getElementById('metric-latency');
    const metricError = document.getElementById('metric-error');

    let isChaosActive = false;

    // Simulate baseline polling of target stats
    setInterval(() => {
        if (!isChaosActive) {
            metricLatency.textContent = Math.floor(Math.random() * 15 + 10) + 'ms';
        }
    }, 2000);

    function appendToTerminal(text, type = 'system') {
        const div = document.createElement('div');
        div.className = `log-line ${type}`;
        div.textContent = text;
        terminalOutput.appendChild(div);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
        return div;
    }

    chaosBtn.addEventListener('click', () => {
        if (isChaosActive) return;

        isChaosActive = true;
        chaosBtn.disabled = true;
        chaosBtn.textContent = 'SYSTEM COMPROMISED...';

        statusDot.className = 'status danger';
        statusDot.textContent = '● DEGRADED';
        metricError.textContent = '30.5%';
        metricLatency.textContent = '2450ms';

        terminalOutput.innerHTML = ''; // clear
        appendToTerminal('[Admin] Manual chaos override authorized.', 'system');
        appendToTerminal('[System] Connecting to Aegis-Air Zero-Trust Engine webhook...', 'system');

        // Connect to SSE Endpoint
        const eventSource = new EventSource('/api/chaos/trigger');

        let currentLine = null;

        eventSource.onmessage = function (event) {
            const data = JSON.parse(event.data);

            if (data.type === 'log') {
                if (data.content.includes("CRITICAL") || data.content.includes("INCIDENT")) {
                    appendToTerminal(data.content, 'critical');
                } else {
                    appendToTerminal(data.content, 'system');
                }
                currentLine = null; // Next token goes on a new line theoretically, or we create a fresh span
            }
            else if (data.type === 'token') {
                if (!currentLine) {
                    currentLine = appendToTerminal('', 'ai-token');
                }
                currentLine.textContent += data.content;
                terminalOutput.scrollTop = terminalOutput.scrollHeight;
            }
            else if (data.type === 'done') {
                eventSource.close();
                isChaosActive = false;
                chaosBtn.disabled = false;
                chaosBtn.textContent = 'UNLEASH CHAOS';

                statusDot.className = 'status healthy';
                statusDot.textContent = '● ONLINE';
                metricError.textContent = '0.0%';

                appendToTerminal('\n[System] Link terminated. RCA generation complete.', 'system');
            }
        };

        eventSource.onerror = function (err) {
            console.error("EventSource failed:", err);
            appendToTerminal('[Error] Connection to Engine lost. Make sure port 8001 is running.', 'critical');
            eventSource.close();
            isChaosActive = false;
            chaosBtn.disabled = false;
            chaosBtn.textContent = 'UNLEASH CHAOS';
        };
    });
});
