Chart.defaults.color = '#8E95A3';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.scale.grid.color = 'rgba(142, 149, 163, 0.1)';

document.addEventListener('DOMContentLoaded', () => {
    fetchDashboardData();
    
    // Sidebar Navigation Logic
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            // Remove active from all
            navItems.forEach(n => n.classList.remove('active'));
            
            // Add active to clicked item
            const current = e.currentTarget;
            current.classList.add('active');
            
            // Update the top brand title to reflect current "page"
            const title = current.getAttribute('title');
            if(title) {
                const brandH1 = document.querySelector('.brand h1');
                brandH1.textContent = `RetailMind Agent - ${title}`;
                
                // Show a fake loading state just to make it feel functional
                brandH1.style.opacity = '0.5';
                setTimeout(() => {
                    brandH1.style.opacity = '1';
                }, 300);
            }
        });
    });
});

let charts = {};

async function fetchDashboardData() {
    try {
        const response = await fetch('http://localhost:8000/api/dashboard_data');
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        
        if (data.error) {
            document.getElementById('reportSummary').textContent = "Pipeline executing machine learning models... Please wait (refreshing in 5s).";
            document.getElementById('reportInsights').textContent = "Running DBSCAN, SHAP, SVM, and SARIMA...";
            document.getElementById('reportActions').textContent = "Waiting...";
            setTimeout(fetchDashboardData, 5000);
            return;
        }
        
        updateKPIs(data.metrics);
        renderShapChart(data.shapImportance);
        renderSarimaChart(data.sarimaForecast);
        renderClusterChart(data.clusters);
        updateActionLog(data.actionLog);
        updateReport(data.report);

    } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
        document.getElementById('reportSummary').textContent = "Network error. Is the backend running?";
        setTimeout(fetchDashboardData, 5000);
    }
}

function updateKPIs(metrics) {
    document.getElementById('kpiTotalProducts').textContent = metrics.totalProducts.toLocaleString();
    document.getElementById('kpiTotalChange').textContent = metrics.totalProductsChange;
    document.getElementById('kpiCriticalAlerts').textContent = metrics.criticalAlerts;
    document.getElementById('kpiCriticalChange').textContent = metrics.criticalAlertsChange;
    document.getElementById('kpiForecastAccuracy').textContent = metrics.forecastAccuracy;
    document.getElementById('kpiAccuracyChange').textContent = metrics.forecastAccuracyChange;
    document.getElementById('kpiEmailsSent').textContent = metrics.emailsSent;
    document.getElementById('kpiEmailsChange').textContent = metrics.emailsSentChange;
}

function renderShapChart(data) {
    const ctx = document.getElementById('shapChart').getContext('2d');
    if (charts.shap) charts.shap.destroy();
    
    charts.shap = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'SHAP Value',
                data: data.values,
                backgroundColor: '#3E8BFF',
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
                x: { grid: { display: false }, ticks: { maxTicksLimit: 5 } },
                y: { grid: { display: false } }
            }
        }
    });
}

function renderSarimaChart(data) {
    const ctx = document.getElementById('sarimaChart').getContext('2d');
    if (charts.sarima) charts.sarima.destroy();

    let gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(62, 139, 255, 0.5)');
    gradient.addColorStop(1, 'rgba(62, 139, 255, 0.0)');

    charts.sarima = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Forecast',
                data: data.values,
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
            plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false, } },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 15 } },
                y: { grid: { color: 'rgba(142, 149, 163, 0.1)' } }
            }
        }
    });
}

function renderClusterChart(data) {
    const ctx = document.getElementById('clusterChart').getContext('2d');
    if (charts.cluster) charts.cluster.destroy();
    
    const colorMap = {
        'Stable': '#23C16B', 'Seasonal': '#FFC933', 'Volatile': '#FF9B26', 'Critical': '#FF4D4D'
    };

    const datasets = Object.keys(colorMap).map(status => {
        return {
            label: status,
            data: data.filter(d => d.status === status),
            backgroundColor: colorMap[status],
            pointRadius: 4,
            borderWidth: 0
        };
    });

    charts.cluster = new Chart(ctx, {
        type: 'scatter',
        data: { datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } } },
            scales: {
                x: { grid: { color: 'rgba(142, 149, 163, 0.1)' } },
                y: { grid: { color: 'rgba(142, 149, 163, 0.1)' } }
            }
        }
    });
}

function updateActionLog(logData) {
    const tbody = document.getElementById('actionLogTable');
    tbody.innerHTML = '';
    
    logData.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${row.timestamp}</td>
            <td>${row.product}</td>
            <td>${row.store}</td>
            <td><span class="badge-state ${row.state}">${row.state}</span></td>
            <td>${row.action}</td>
        `;
        tbody.appendChild(tr);
    });
}

function updateReport(reportData) {
    document.getElementById('reportSummary').textContent = reportData.summary;
    document.getElementById('reportInsights').textContent = reportData.insights;
    document.getElementById('reportActions').textContent = reportData.actions;
}
