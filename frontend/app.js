// ─── Chart Defaults ──────────────────────────────────────────────────────────
Chart.defaults.color = '#8E95A3';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.scale.grid.color = 'rgba(142, 149, 163, 0.1)';

// ─── State ────────────────────────────────────────────────────────────────────
let charts = {};
const POLL_INTERVAL_MS = 5000;
let lastData = null;

// ─── Boot ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    setupNav();
    console.log('[RetailMind] Dashboard booting. Starting poll loop every', POLL_INTERVAL_MS, 'ms');
    fetchDashboardData();
    setInterval(fetchDashboardData, POLL_INTERVAL_MS);
});

// ─── Navigation ──────────────────────────────────────────────────────────────
function setupNav() {
    const navItems = document.querySelectorAll('.nav-item');
    const views = {
        Dashboard: document.getElementById('dashboard-view'),
        Analytics:  document.getElementById('analytics-view'),
        Reports:    document.getElementById('reports-view'),
        Trends:     document.getElementById('trends-view'),
        Auditing:   document.getElementById('auditing-view'),
    };
    const incomingSection = document.querySelector('.incoming-data-section');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');
            const title = item.getAttribute('title');

            // Hide all views
            Object.values(views).forEach(v => { if (v) v.style.display = 'none'; });
            if (incomingSection) incomingSection.style.display = 'none';

            if (title === 'Dashboard') {
                if (views.Dashboard) views.Dashboard.style.display = 'block';
                if (incomingSection) incomingSection.style.display = 'block';
                // Re-render charts after display (needed because hidden canvas has 0 size)
                if (lastData) { renderAllCharts(lastData); }
            } else if (views[title]) {
                views[title].style.display = 'block';
                if (title === 'Analytics' && lastData) setTimeout(() => renderCategoryChart(), 100);
                if (title === 'Trends'    && lastData) setTimeout(() => renderMarketTrendsChart(lastData), 100);
            }

            document.querySelector('.brand h1').textContent = `RetailMind Agent - ${title}`;
        });
    });
}

// ─── Data Fetch ───────────────────────────────────────────────────────────────
async function fetchDashboardData() {
    console.log('[RetailMind] Fetching data from backend...');
    try {
        const response = await fetch('http://localhost:8000/api/dashboard_data');
        if (!response.ok) {
            console.warn('[RetailMind] HTTP error:', response.status, response.statusText);
            setStatus('Backend returned error ' + response.status);
            return;
        }
        const data = await response.json();
        console.log('[RetailMind] Data received. is_ready:', data.is_ready, '| telemetry:', data.telemetry, '| actionLog len:', (data.actionLog||[]).length);

        if (data.error) {
            console.warn('[RetailMind] Pipeline still loading:', data.error);
            setStatus('Pipeline loading… retrying');
            return;
        }

        lastData = data;
        updateDashboard(data);
        setStatus('Last updated ' + new Date().toLocaleTimeString());
    } catch (err) {
        console.error('[RetailMind] Fetch failed:', err);
        setStatus('❌ Cannot reach backend — is uvicorn running?');
    }
}

function setStatus(msg) {
    const el = document.getElementById('lastUpdated');
    if (el) el.textContent = msg;
}

// ─── Dashboard Update ─────────────────────────────────────────────────────────
function updateDashboard(data) {
    renderAllCharts(data);
    updateKPIs(data.metrics || {});
    updateZone2(data);
    updateZone3(data);
    updateZone6(data);
    updateScrapeLog(data);
    updateReportsView(data);
    updateAnalyticsView(data);
}

// ─── Zone 2: Live Scoring Feed ────────────────────────────────────────────────
function updateZone2(data) {
    const tel = data.telemetry || {};
    console.log('[Zone 2] telemetry:', tel);

    setText('sigS',      tel.s_severity !== undefined ? tel.s_severity : '--');
    setText('sigGap',    tel.gap        !== undefined ? tel.gap        : '--');
    setText('sigMu',     tel.mu         !== undefined ? tel.mu         : '--');
    setText('sigArima',  tel.arima_trend!== undefined ? tel.arima_trend: '--');
    setText('sigShap',   tel.reliability!== undefined ? tel.reliability: '--');
    setText('sigTotal',  tel.score      !== undefined ? tel.score      : '--');

    if (data.egypt) {
        setText('sigEgp',    data.egypt.egp_rate || '--');
        const w = data.egypt.weather || {};
        setText('sigWeather', w.temp ? `${w.temp}°C, ${w.condition}` : '--');
    }
}

// ─── Zone 3: ReAct Dispatch ───────────────────────────────────────────────────
function updateZone3(data) {
    const tel = data.telemetry || {};
    setText('latestActionDisplay', tel.action ? `Latest Action: ${tel.action}` : 'Latest Action: Waiting...');
    setText('agentThoughts', data.thoughts ? `"${data.thoughts}"` : '"Statistical analysis running..."');
}

// ─── Zone 6: Alerts & Action Log ─────────────────────────────────────────────
function updateZone6(data) {
    const tel    = data.telemetry || {};
    const logs   = data.actionLog || [];
    console.log('[Zone 6] outcome:', data.outcome, '| actionLog entries:', logs.length);

    const driftEl = document.getElementById('driftStatus');
    if (driftEl) {
        driftEl.textContent = 'Status: ' + (data.outcome || 'Steady');
        driftEl.style.color = (data.outcome || '').includes('Drift') ? '#EE5D50' : '#05CD99';
    }
    setText('outcomeLog', 'Outcome: ' + (data.outcome || 'Observant'));

    const tbody = document.getElementById('miniActionLog');
    const fullLogBody = document.getElementById('fullAuditLogTable');
    
    if (tbody) {
        tbody.innerHTML = '';
        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="color:var(--text-sec); text-align:center;">No actions logged yet</td></tr>';
        } else {
            logs.slice(-5).reverse().forEach(entry => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${entry.product || '--'}</td><td>${entry.action || '--'}</td><td>${entry.score !== undefined ? entry.score : (tel.intensity || '--')}</td>`;
                tbody.appendChild(tr);
            });
        }
    }
    
    // Update Full Audit Table
    if (fullLogBody) {
        if (logs.length === 0) {
            fullLogBody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 20px; color: var(--text-sec);">Waiting for inner loops to run...</td></tr>';
        } else {
            if (fullLogBody.children.length === 1 && fullLogBody.innerHTML.includes('Waiting')) {
                 fullLogBody.innerHTML = '';
            }
            
            fullLogBody.innerHTML = '';
            logs.slice().reverse().forEach((entry, idx) => {
                const tr = document.createElement('tr');
                tr.style.borderBottom = '1px solid rgba(142, 149, 163, 0.1)';
                
                let signalsStr = 'S:-- | Gap:-- | μ:-- | Trend:-- | Cos:--';
                let thoughtsStr = entry.thoughts || "Strategic routing executed.";
                
                if (entry.telemetry) {
                     signalsStr = `S:${entry.telemetry.s_severity || 0} | G:${entry.telemetry.gap || 0} | μ:${entry.telemetry.mu || 0} | T:${entry.telemetry.arima_trend || 0} | C:${entry.telemetry.reliability || 0}`;
                }
                
                let actionColor = 'var(--text-primary)';
                if (entry.action.includes('Restock') || entry.action.includes('High-Priority')) actionColor = 'var(--color-green)';
                else if (entry.action.includes('Human') || entry.action.includes('Escalate') || entry.action.includes('Audit')) actionColor = 'var(--color-red)';
                else if (entry.action.includes('Monitoring')) actionColor = 'var(--text-sec)';

                tr.innerHTML = `
                    <td style="padding: 12px; color: var(--text-sec);">${entry.timestamp || '--'}</td>
                    <td style="padding: 12px; font-weight: 500;">
                        <span class="clickable-product" onclick="showTraceModal(${logs.length - 1 - idx})">${entry.product || '--'}</span>
                    </td>
                    <td style="padding: 12px; color: var(--accent-blue);">${entry.path || '--'}</td>
                    <td style="padding: 12px; font-weight: bold; color: ${actionColor};">${entry.action || '--'}</td>
                    <td style="padding: 12px; color: var(--color-orange); font-weight: 600;">${entry.dominant_feature || 'None'}</td>
                    <td style="padding: 12px;"><strong>${entry.score !== undefined ? entry.score : '--'}</strong></td>
                    <td style="padding: 12px; color: var(--text-sec); font-family: monospace; font-size: 0.85em;">${signalsStr}</td>
                    <td style="padding: 12px; font-style: italic; color: #a3a8b3;">${thoughtsStr}</td>
                `;
                fullLogBody.appendChild(tr);
            });
        }
    }
}

// ─── Modal Logic ──────────────────────────────────────────────────────────────
function showTraceModal(logIdx) {
    if (!lastData || !lastData.actionLog || !lastData.actionLog[logIdx]) return;
    const entry = lastData.actionLog[logIdx];
    const modal = document.getElementById('traceModal');
    
    document.getElementById('modalProductTitle').textContent = entry.product || 'Unknown Product';
    document.getElementById('modalActionSubtitle').textContent = `Cycle Action: ${entry.action}`;
    
    // 1. Trace List
    const traceList = document.getElementById('modalTraceList');
    traceList.innerHTML = '';
    if (entry.telemetry && entry.telemetry.trace) {
        entry.telemetry.trace.forEach(step => {
            const li = document.createElement('li');
            li.textContent = step;
            traceList.appendChild(li);
        });
    }

    // 2. Decision Weights with Interpretation
    const weightsDiv = document.getElementById('modalWeightsBreakdown');
    weightsDiv.innerHTML = '';
    if (entry.weights) {
        Object.entries(entry.weights).forEach(([label, val]) => {
            let impact = "Inert";
            let color = "var(--text-sec)";
            if (val >= 0.20) { impact = "Crucial"; color = "var(--color-red)"; }
            else if (val >= 0.15) { impact = "Major"; color = "var(--color-orange)"; }
            else if (val >= 0.10) { impact = "Mild"; color = "var(--accent-blue)"; }
            else if (val > 0) { impact = "Minor"; color = "var(--color-green)"; }

            const width = Math.min(val * 400, 100); 
            const row = document.createElement('div');
            row.className = 'weight-row';
            row.innerHTML = `
                <div class="weight-label">${label} <span style="font-size:10px; color:${color}; font-weight:bold; margin-left:5px;">[${impact}]</span></div>
                <div class="weight-bar-bg"><div class="weight-bar-fill" style="width: ${width}%; background:${color};"></div></div>
                <div class="weight-val">+${val.toFixed(2)}</div>
            `;
            weightsDiv.appendChild(row);
        });
    }

    // 3. SHAP Details
    const shapDiv = document.getElementById('modalShapDetails');
    shapDiv.innerHTML = '';
    const labels = entry.shap_feature_names || ['mean_sales', 'std_sales', 'promo_impact'];
    const vals = entry.shap_values || [0,0,0];
    labels.forEach((label, i) => {
        const val = vals[i] || 0;
        const width = Math.min(Math.abs(val) * 200, 100);
        const row = document.createElement('div');
        row.className = 'shap-bar-row';
        row.innerHTML = `
            <div class="shap-label">${label}</div>
            <div class="shap-bar-bg"><div class="shap-bar-fill" style="width: ${width}%;"></div></div>
            <div class="shap-val">${val.toFixed(4)}</div>
        `;
        shapDiv.appendChild(row);
    });

    // 4. Conditional RAG EvidenceSection
    const ragSection = document.getElementById('modalRagSection');
    const ragMetrics = document.getElementById('modalRagMetrics');
    if (entry.rag_consensus > 0) {
        ragSection.style.display = 'block';
        ragMetrics.innerHTML = `<strong>Consensus:</strong> ${entry.rag_consensus}/5 Neighbors Agreement<br><strong>Similarity Score:</strong> ${entry.rag_similarity}`;
    } else {
        ragSection.style.display = 'none';
    }

    document.getElementById('modalThought').textContent = `"${entry.thoughts || 'No strategic summary available.'}"`;
    modal.style.display = "block";
    
    const span = document.getElementsByClassName("close-modal")[0];
    span.onclick = () => modal.style.display = "none";
}

// Update the full log table
function updateFullAuditTable(log) {
    const tableBody = document.getElementById('fullAuditLogTable');
    if (!tableBody) return;
    tableBody.innerHTML = '';
    
    log.slice().reverse().forEach((entry, idx) => {
        const actualIdx = log.length - 1 - idx;
        const tr = document.createElement('tr');
        
        const signals = entry.telemetry ? 
            `${entry.telemetry.s_severity} | ${entry.telemetry.gap} | ${entry.telemetry.mu} | ${entry.telemetry.arima_trend} | ${entry.telemetry.reliability}` : '--';
        
        tr.innerHTML = `
            <td>${entry.timestamp}</td>
            <td class="clickable-product" onclick="showTraceModal(${actualIdx})">${entry.product}</td>
            <td>${entry.path}</td>
            <td><strong>${entry.action}</strong></td>
            <td style="color:var(--color-orange);">${entry.dominant_feature}</td>
            <td>${entry.score}</td>
            <td style="font-size:10px; color:var(--text-sec);">${signals}</td>
            <td style="font-style:italic;">${entry.thoughts}</td>
        `;
        tableBody.appendChild(tr);
    });
}

// ─── Incoming Data / Scrape Feed ──────────────────────────────────────────────
function updateScrapeLog(data) {
    const ul = document.getElementById('scrapedDataList');
    if (!ul) return;

    if (ul.innerHTML.includes('Loading live')) ul.innerHTML = '';

    const ts = new Date().toLocaleTimeString();
    const addLine = (src, label, val) => {
        const li = document.createElement('li');
        li.innerHTML = `<span>[${ts}]</span> ${src} <span>| ${label}:</span> ${val}`;
        ul.insertBefore(li, ul.firstChild);
    };

    if (data.live_oil_price) addLine('MarketWatch', 'WTI Crude', `$${data.live_oil_price}/bbl`);
    if (data.egypt?.egp_rate)  addLine('Bank of Egypt', 'USD/EGP', `${data.egypt.egp_rate} EGP`);
    if (data.egypt?.weather?.temp) addLine('OpenWeather', 'Cairo', `${data.egypt.weather.temp}°C, ${data.egypt.weather.condition}`);
    if (data.telemetry?.score !== undefined) addLine('RetailMind AI', 'Agent Score', data.telemetry.score);

    while (ul.children.length > 10) ul.removeChild(ul.lastChild);
}

// ─── KPIs ─────────────────────────────────────────────────────────────────────
function updateKPIs(metrics) {
    console.log('[KPIs] metrics:', metrics);
    setText('kpiTotalProducts',  (metrics.totalProducts  || 0).toLocaleString());
    setText('kpiTotalChange',     metrics.totalProductsChange  || '--');
    setText('kpiCriticalAlerts',  metrics.criticalAlerts  ?? '--');
    setText('kpiCriticalChange',  metrics.criticalAlertsChange || '--');
    setText('kpiForecastAccuracy',metrics.forecastAccuracy !== undefined ? metrics.forecastAccuracy + '%' : '--');
    setText('kpiAccuracyChange',  metrics.forecastAccuracyChange || '--');
    setText('kpiEmailsSent',      metrics.emailsSent      ?? '--');
    setText('kpiEmailsChange',    metrics.emailsSentChange || '--');
}

// ─── Reports View ─────────────────────────────────────────────────────────────
function updateReportsView(data) {
    if (!data.report) return;
    const el = document.getElementById('reportGeminiContent');
    if (el) {
        el.innerHTML = `
            <p><strong>📋 Summary:</strong> ${data.report.summary || '--'}</p>
            <p style="margin-top:12px;"><strong>🔍 Insights:</strong> ${data.report.insights || '--'}</p>
            <p style="margin-top:12px;"><strong>⚡ Actions:</strong> ${data.report.actions || '--'}</p>
        `;
    }
    setText('reportConf', data.telemetry?.score || '--');
    setText('reportRisk',  data.metrics?.criticalAlerts || '--');
}

// ─── Analytics View ───────────────────────────────────────────────────────────
function updateAnalyticsView(data) {
    if (!data.egypt) return;
    setText('analyticEgp',       data.egypt.egp_rate || '--');
    const w = data.egypt.weather || {};
    setText('analyticWeather',   w.temp ? `${w.temp}°C, ${w.condition}` : '--');
    setText('analyticInflation', data.egypt.cbe?.inflation ?? '--');
    setText('analyticInterest',  data.egypt.cbe?.interest_rate ?? '--');
}

// ─── Charts ───────────────────────────────────────────────────────────────────
function renderAllCharts(data) {
    if (data.clusters)      renderClusterChart(data.clusters);
    if (data.shapImportance) renderShapChart(data);
    if (data.sarimaForecast) renderSarimaChart(data.sarimaForecast);
    if (data.actionLog)     renderDispatchChart(data);
}

function renderShapChart(payload) {
    const data = payload.shapImportance || {};
    const tel = payload.telemetry || {};
    const logs = payload.actionLog || [];

    const ctx = getCtx('shapChart');
    if (!ctx) { console.warn('[Zone 4] shapChart canvas not found'); return; }
    if (charts.shap) charts.shap.destroy();

    let uncertain = logs.filter(l => l.telemetry && l.telemetry.reliability < 0.55).length;
    let pct = logs.length > 0 ? ((uncertain / logs.length) * 100).toFixed(1) : 0;
    setText('shapCosineText', tel.reliability !== undefined ? tel.reliability : '--');
    setText('shapUncertainText', pct);

    const vals = (data.values || []).map(v => Math.abs(v));
    const maxVal = Math.max(...vals);
    console.log('[Zone 4] SHAP values:', vals, '| max:', maxVal);

    // If all zeros, show a placeholder message
    if (maxVal === 0) {
        console.warn('[Zone 4] SHAP values are all zero — backend may still be computing');
    }

    charts.shap = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || ['Feature 1', 'Feature 2', 'Feature 3'],
            datasets: [{
                label: 'Abs SHAP Value',
                data: vals.length ? vals : [0.3, 0.2, 0.1],
                backgroundColor: ['#4318FF', '#3E8BFF', '#23C16B'],
                borderRadius: 4,
                barPercentage: 0.6
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 5 }, beginAtZero: true },
                y: { grid: { display: false } }
            }
        }
    });
    renderCategoryChart();
}

function renderDispatchChart(data) {
    const ctx = getCtx('dispatchChart');
    if (!ctx) return;
    if (charts.dispatch) charts.dispatch.destroy();

    const logs = data.actionLog || [];
    let counts = { 'Direct Exec': 0, 'Verify/RAG': 0, 'Human/Wait': 0, 'Routine Monitoring': 0 };

    logs.forEach(log => {
        if (!log.path) return;
        if (log.path.includes('Step 1')) counts['Direct Exec']++;
        else if (log.path.includes('Step 2') || log.path.includes('Step 3')) counts['Verify/RAG']++;
        else if (log.path.includes('Step 4') || log.path.includes('Step 5') || log.path.includes('Tie')) counts['Human/Wait']++;
        else counts['Routine Monitoring']++;
    });

    charts.dispatch = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(counts),
            datasets: [{
                data: Object.values(counts),
                backgroundColor: ['#23C16B', '#3E8BFF', '#FF9B26', '#EE5D50'],
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: 'rgba(142, 149, 163, 0.1)' }, beginAtZero: true },
                y: { grid: { display: false } }
            }
        }
    });
}

function renderCategoryChart() {
    const ctx = getCtx('categoryChart');
    if (!ctx) return;
    if (charts.category) charts.category.destroy();
    charts.category = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Grocery', 'Beverages', 'Cleaning', 'Personal Care', 'Dairy'],
            datasets: [{
                data: [40, 25, 15, 12, 8],
                backgroundColor: ['#4318FF', '#3E8BFF', '#23C16B', '#FF9B26', '#EE5D50'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'right', labels: { font: { size: 11 } } } }
        }
    });
}

function renderSarimaChart(data) {
    const ctx = getCtx('sarimaChart');
    if (!ctx) { console.warn('[Zone 5] sarimaChart canvas not found'); return; }
    if (charts.sarima) charts.sarima.destroy();

    let gradient;
    try {
        gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(62, 139, 255, 0.5)');
        gradient.addColorStop(1, 'rgba(62, 139, 255, 0.0)');
    } catch(e) { gradient = 'rgba(62, 139, 255, 0.2)'; }

    charts.sarima = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: '30-Day Sales Forecast',
                data: data.values || [],
                borderColor: '#3E8BFF',
                backgroundColor: gradient,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } },
                y: { grid: { color: 'rgba(142, 149, 163, 0.1)' } }
            }
        }
    });
}

function renderClusterChart(data) {
    const ctx = getCtx('clusterChart');
    if (!ctx) { console.warn('[Zone 1] clusterChart canvas not found'); return; }
    if (charts.cluster) charts.cluster.destroy();

    const colorMap = {
        Stable:   '#23C16B',
        Seasonal: '#FFCE20',
        Volatile: '#FF9B26',
        Critical: '#EE5D50',
        'At-Risk': '#FF9B26'
    };

    const allStatuses = [...new Set(data.map(d => d.status))];
    const datasets = allStatuses.map(status => ({
        label: status,
        data: data.filter(d => d.status === status),
        backgroundColor: colorMap[status] || '#8E95A3',
        pointRadius: 4,
        borderWidth: 0
    }));

    charts.cluster = new Chart(ctx, {
        type: 'scatter',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8, font: { size: 10 } } } },
            scales: {
                x: { 
                    type: 'logarithmic',
                    grid: { color: 'rgba(142, 149, 163, 0.1)' },
                    title: { display: true, text: 'Mean Sales (Log)', font: { size: 10 } },
                    min: 0.1
                },
                y: { 
                    type: 'logarithmic',
                    grid: { color: 'rgba(142, 149, 163, 0.1)' },
                    title: { display: true, text: 'Sales Std Dev (Log)', font: { size: 10 } },
                    min: 0.1
                }
            }
        }
    });
}

function renderMarketTrendsChart(data) {
    const ctx = getCtx('marketTrendsChart');
    if (!ctx) return;
    if (charts.marketTrends) charts.marketTrends.destroy();

    const labels = data.sarimaForecast?.labels || Array.from({length: 30}, (_, i) => i + 1);
    const sales  = data.sarimaForecast?.values || [];
    const egpLine= Array.from({length: labels.length}, () => data.egypt?.egp_rate || 48);

    charts.marketTrends = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: 'Sales Forecast', data: sales, borderColor: '#4318FF', yAxisID: 'y', pointRadius: 0, tension: 0.4 },
                { label: 'USD/EGP Rate',   data: egpLine, borderColor: '#EE5D50', borderDash: [5, 5], yAxisID: 'y1', pointRadius: 0 }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y:  { type: 'linear', display: true, position: 'left' },
                y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false } }
            }
        }
    });
}

// ─── Utility ──────────────────────────────────────────────────────────────────
function setText(id, val) {
    const el = document.getElementById(id);
    if (el) { el.textContent = val; }
    else { console.warn('[RetailMind] Element not found:', id); }
}

function getCtx(id) {
    const canvas = document.getElementById(id);
    if (!canvas) { console.warn('[RetailMind] Canvas not found:', id); return null; }
    return canvas.getContext('2d');
}
