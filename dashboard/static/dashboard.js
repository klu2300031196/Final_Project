
/**
 * DevOps Continuous Testing Dashboard - Frontend Controller
 * Connects to live SSE stream, renders Quality Gate rules,
 * coverage bars, KPIs, and pipeline run history.
 */

let eventSource = null;
let reconnectTimer = null;

document.addEventListener("DOMContentLoaded", () => {
    initSSE();
    fetchStatus();
    fetchLatestReport();
    fetchHistory();

    setInterval(fetchStatus, 3000);
});

function initSSE() {
    if (eventSource) {
        eventSource.close();
    }

    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }

    eventSource = new EventSource("/api/pipeline/logs/stream");

    eventSource.onmessage = (event) => {
        if (!event.data || event.data.startsWith(":")) return;

        appendConsoleLine(event.data);

        const message = event.data;

        if (message.includes("[STAGE 1/5]")) {
            highlightStage("step-sast");
        }
        if (message.includes("[STAGE 2/5]")) {
            highlightStage("step-tests");
        }
        if (message.includes("[STAGE 3/5]")) {
            highlightStage("step-cov");
        }
        if (message.includes("[STAGE 4/5]")) {
            highlightStage("step-perf");
        }
        if (message.includes("[STAGE 5/5]")) {
            highlightStage("step-gate");
        }

        if (
            message.includes("[SUCCESS] PIPELINE FINISHED") ||
            message.includes("[COMPLETE]")
        ) {
            setTimeout(() => {
                fetchLatestReport();
                fetchHistory();
                fetchStatus();
                resetStepperSuccess();
            }, 800);
        }

        if (message.includes("[ERROR]")) {
            fetchStatus();
        }
    };

    eventSource.onerror = () => {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }

        reconnectTimer = setTimeout(() => {
            initSSE();
        }, 5000);
    };
}

function appendConsoleLine(message) {
    const consoleBox = document.getElementById("console-output");

    if (!consoleBox) return;

    const line = document.createElement("div");
    line.className = "terminal-line";

    if (
        message.includes("[STAGE") ||
        message.includes("-->") ||
        message.includes("====")
    ) {
        line.classList.add("line-info");
    } else if (
        message.includes("PASSED") ||
        message.includes("[SUCCESS]") ||
        message.includes("satisfied")
    ) {
        line.classList.add("line-success");
    } else if (
        message.includes("FAILED") ||
        message.includes("ERROR") ||
        message.includes("failed")
    ) {
        line.classList.add("line-error");
    } else if (message.includes("WARNING")) {
        line.classList.add("line-warn");
    }

    line.innerText = message;
    consoleBox.appendChild(line);
    consoleBox.scrollTop = consoleBox.scrollHeight;
}

function clearConsole() {
    const consoleBox = document.getElementById("console-output");

    if (!consoleBox) return;

    consoleBox.innerHTML =
        '<div class="terminal-line">[SYSTEM] Console cleared.</div>';
}

async function fetchStatus() {
    try {
        const response = await fetch("/api/status");
        if (!response.ok) {
            throw new Error(`Status request failed: ${response.status}`);
        }

        const data = await response.json();

        const autText = document.getElementById("aut-status-text");
        const runnerDot = document.getElementById("runner-dot");
        const runnerText = document.getElementById("runner-status-text");
        const button = document.getElementById("btn-trigger");

        if (autText) {
            autText.innerText = `AUT: ${data.aut_status}`;
        }

        if (data.pipeline_running) {
            if (runnerDot) {
                runnerDot.className = "status-dot dot-running";
            }

            if (runnerText) {
                runnerText.innerText = "RUNNER: EXECUTING";
            }

            if (button) {
                button.disabled = true;
                button.style.opacity = "0.6";
                button.innerText = "Running Pipeline...";
            }
        } else {
            if (runnerDot) {
                runnerDot.className = "status-dot dot-idle";
            }

            if (runnerText) {
                runnerText.innerText = "RUNNER: IDLE";
            }

            if (button) {
                button.disabled = false;
                button.style.opacity = "1";
                button.innerHTML =
                    '<span class="play-icon">▶</span> Run Full Testing Pipeline';
            }
        }
    } catch (error) {
        console.error("Status fetch error:", error);
    }
}

async function triggerPipeline() {
    const button = document.getElementById("btn-trigger");

    if (!button || button.disabled) return;

    button.disabled = true;
    button.innerText = "Initiating Pipeline...";

    clearConsole();

    appendConsoleLine(
        "[USER] Pipeline triggered from Web Dashboard."
    );

    resetStepperRunning();

    try {
        const response = await fetch("/api/pipeline/trigger", {
            method: "POST"
        });

        const data = await response.json();

        if (!response.ok) {
            appendConsoleLine(
                `[ERROR] ${data.error || "Failed to trigger pipeline"}`
            );
            await fetchStatus();
            return;
        }

        appendConsoleLine(
            "[SYSTEM] Pipeline execution request accepted."
        );
    } catch (error) {
        appendConsoleLine(`[ERROR] Network error: ${error.message}`);
        await fetchStatus();
    }
}

async function fetchLatestReport() {
    try {
        const response = await fetch("/api/latest-report");

        if (!response.ok) {
            console.warn("Latest report is not available yet.");
            return;
        }

        const data = await response.json();
        renderReportData(data);
    } catch (error) {
        console.error("Report fetch error:", error);
    }
}

function renderReportData(data) {
    const qualityGate = data.quality_gate || {};
    const verdict = qualityGate.verdict || "UNKNOWN";

    // Actual report structure: metrics are stored inside stages.
    const stages = data.stages || {};

    const coverage =
        stages.code_coverage || data.coverage || {};

    const performance =
        stages.performance || data.performance || {};

    const security =
        stages.security_sast || data.security || {};

    const functional =
        stages.functional_tests || {};

    // 1. Global Quality Gate verdict
    const globalVerdict = document.getElementById("global-verdict");

    if (globalVerdict) {
        globalVerdict.innerText = `GATE: ${verdict}`;

        globalVerdict.className =
            verdict === "PASSED"
                ? "verdict-tag tag-passed"
                : "verdict-tag tag-running";
    }

    // 2. Test and performance KPI cards
    const totalTests =
        functional.total ?? data.total_tests ?? 0;

    const passedTests =
        functional.passed ?? totalTests;

    const coveragePercentage =
        coverage.overall_coverage_pct ?? 0;

    const p95Latency =
        performance.p95_latency_ms ?? 0;

    const throughput =
        performance.requests_per_second ?? 0;

    const securityFindings =
        security.critical_or_high ?? 0;

    const testsElement = document.getElementById("kpi-tests");
    const coverageElement = document.getElementById("kpi-coverage");
    const latencyElement = document.getElementById("kpi-latency");
    const throughputElement = document.getElementById("kpi-rps");
    const securityElement = document.getElementById("kpi-security");

    if (testsElement) {
        testsElement.innerText =
            `${passedTests} / ${totalTests}`;
    }

    if (coverageElement) {
        coverageElement.innerText =
            `${coveragePercentage}%`;
    }

    if (latencyElement) {
        latencyElement.innerText =
            `${p95Latency} ms`;
    }

    if (throughputElement) {
        throughputElement.innerText =
            `Throughput: ~${throughput} RPS`;
    }

    if (securityElement) {
        securityElement.innerText =
            `${securityFindings} HIGH`;
    }

    // 3. Quality Gate scorecard
    const tableBody = document.querySelector(
        "#gate-rules-table tbody"
    );

    if (tableBody) {
        tableBody.innerHTML = "";

        (qualityGate.checks || []).forEach((check) => {
            const row = document.createElement("tr");

            const statusClass =
                check.status === "PASSED"
                    ? "rule-pass"
                    : "rule-fail";

            const ruleCell = document.createElement("td");
            ruleCell.style.fontWeight = "600";
            ruleCell.textContent = check.rule ?? "";

            const thresholdCell = document.createElement("td");
            thresholdCell.style.color = "var(--text-muted)";
            thresholdCell.textContent = check.threshold ?? "";

            const actualCell = document.createElement("td");
            actualCell.style.fontWeight = "700";
            actualCell.textContent = check.actual ?? "";

            const statusCell = document.createElement("td");
            const statusPill = document.createElement("span");
            statusPill.className = `rule-pill ${statusClass}`;
            statusPill.textContent = check.status ?? "UNKNOWN";

            statusCell.appendChild(statusPill);

            row.appendChild(ruleCell);
            row.appendChild(thresholdCell);
            row.appendChild(actualCell);
            row.appendChild(statusCell);

            tableBody.appendChild(row);
        });
    }

    // 4. Module-level code coverage
    const coverageBox = document.getElementById(
        "coverage-progress-container"
    );

    if (coverageBox) {
        coverageBox.innerHTML = "";

        (coverage.modules || []).forEach((module) => {
            const item = document.createElement("div");
            item.className = "cov-item";

            const header = document.createElement("div");
            header.className = "cov-item-header";

            const moduleName = document.createElement("span");
            moduleName.className = "cov-module-name";
            moduleName.textContent = module.module ?? "Unknown module";

            const modulePercentage = document.createElement("span");
            modulePercentage.textContent =
                `${module.coverage_pct ?? 0}% ` +
                `(${module.covered_statements ?? 0}/` +
                `${module.total_statements ?? 0})`;

            header.appendChild(moduleName);
            header.appendChild(modulePercentage);

            const barBackground = document.createElement("div");
            barBackground.className = "cov-bar-bg";

            const barFill = document.createElement("div");
            barFill.className = "cov-bar-fill";

            const percentage = Number(module.coverage_pct) || 0;

            barFill.style.width =
                `${Math.min(100, Math.max(0, percentage))}%`;

            barBackground.appendChild(barFill);

            item.appendChild(header);
            item.appendChild(barBackground);

            coverageBox.appendChild(item);
        });
    }
}

async function fetchHistory() {
    try {
        const response = await fetch("/api/history");

        if (!response.ok) {
            throw new Error(`History request failed: ${response.status}`);
        }

        const data = await response.json();

        const tableBody = document.querySelector(
            "#history-table tbody"
        );

        if (!tableBody) return;

        tableBody.innerHTML = "";

        (data.runs || []).slice(0, 5).forEach((run) => {
            const row = document.createElement("tr");

            const idCell = document.createElement("td");
            const idCode = document.createElement("code");
            idCode.textContent = run.id ?? "Unknown";
            idCell.appendChild(idCode);

            const timeCell = document.createElement("td");
            timeCell.textContent = run.timestamp
                ? new Date(run.timestamp).toLocaleTimeString()
                : "Just now";

            const durationCell = document.createElement("td");
            durationCell.textContent =
                `${run.duration ?? 0}s`;

            const verdictCell = document.createElement("td");
            const verdictPill = document.createElement("span");

            verdictPill.className =
                `rule-pill ${
                    run.verdict === "PASSED"
                        ? "rule-pass"
                        : "rule-fail"
                }`;

            verdictPill.textContent = run.verdict ?? "UNKNOWN";

            verdictCell.appendChild(verdictPill);

            row.appendChild(idCell);
            row.appendChild(timeCell);
            row.appendChild(durationCell);
            row.appendChild(verdictCell);

            tableBody.appendChild(row);
        });
    } catch (error) {
        console.error("History fetch error:", error);
    }
}

function highlightStage(stageId) {
    document.querySelectorAll(".stage-step").forEach((step) => {
        step.classList.remove("active-step");
    });

    const target = document.getElementById(stageId);

    if (target) {
        target.classList.add("active-step");
    }
}

function resetStepperRunning() {
    document.querySelectorAll(".stage-step").forEach((step) => {
        step.classList.remove("active-step");
        step.classList.remove("success-step");
    });

    highlightStage("step-sast");
}

function resetStepperSuccess() {
    document.querySelectorAll(".stage-step").forEach((step) => {
        step.classList.remove("active-step");
        step.classList.add("success-step");
    });
}
