// Dashboard-specific JavaScript functionality
import { Chart, registerables } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { da } from 'date-fns/locale';

// Register Chart.js components
Chart.register(...registerables);

// Chart instances storage
const charts = {};

// State management
let currentPackage = '';
let packages = [];

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initialized');
    
    // Initialize date inputs
    initializeDateInputs();
    
    // Load initial data
    loadInitialData();
    
    // Set up event listeners
    setupEventListeners();
});

function setupEventListeners() {
    const refreshBtn = document.getElementById('refresh-data');
    const packageFilter = document.getElementById('package-filter');
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshData);
    }
    
    if (packageFilter) {
        packageFilter.addEventListener('change', function() {
            currentPackage = this.value;
            refreshData();
        });
    }
}

function initializeDateInputs() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);
    
    const endDateInput = document.getElementById('end-date');
    const startDateInput = document.getElementById('start-date');
    
    if (endDateInput) endDateInput.value = endDate.toISOString().split('T')[0];
    if (startDateInput) startDateInput.value = startDate.toISOString().split('T')[0];
}

async function loadInitialData() {
    try {
        showLoading();
        
        await Promise.all([
            loadOverviewData(),
            loadTimeSeriesData(),
            loadPythonVersionData(),
            loadOSData()
        ]);
        
        hideLoading();
    } catch (error) {
        console.error('Dashboard loading error:', error);
        showError('Failed to load dashboard data: ' + error.message);
        hideLoading();
    }
}

async function refreshData() {
    clearError();
    const refreshBtn = document.getElementById('refresh-data');
    
    if (!refreshBtn) return;
    
    const icon = refreshBtn.querySelector('i');
    
    // Add loading animation
    if (icon) icon.classList.add('fa-spin');
    refreshBtn.disabled = true;
    
    try {
        await loadInitialData();
    } finally {
        // Remove loading animation
        if (icon) icon.classList.remove('fa-spin');
        refreshBtn.disabled = false;
    }
}

async function loadOverviewData() {
    const params = new URLSearchParams();
    if (currentPackage) params.append('package_name', currentPackage);
    
    const response = await fetch(`/api/dashboard/overview?${params}`);
    if (!response.ok) throw new Error('Failed to load overview data');
    
    const data = await response.json();
    renderOverviewStats(data);
    updatePackageFilter(data);
}

async function loadTimeSeriesData() {
    const params = new URLSearchParams();
    if (currentPackage) params.append('package_name', currentPackage);
    
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    
    if (startDateInput?.value) params.append('start_date', startDateInput.value);
    if (endDateInput?.value) params.append('end_date', endDateInput.value);
    
    const response = await fetch(`/api/dashboard/timeseries?${params}`);
    if (!response.ok) throw new Error('Failed to load time series data');
    
    const data = await response.json();
    renderTimeSeriesChart(data);
}

async function loadPythonVersionData() {
    const params = new URLSearchParams();
    if (currentPackage) params.append('package_name', currentPackage);
    
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    
    if (startDateInput?.value) params.append('start_date', startDateInput.value);
    if (endDateInput?.value) params.append('end_date', endDateInput.value);
    
    const response = await fetch(`/api/dashboard/python-versions?${params}`);
    if (!response.ok) throw new Error('Failed to load Python version data');
    
    const data = await response.json();
    renderPythonVersionChart(data);
}

async function loadOSData() {
    const params = new URLSearchParams();
    if (currentPackage) params.append('package_name', currentPackage);
    
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    
    if (startDateInput?.value) params.append('start_date', startDateInput.value);
    if (endDateInput?.value) params.append('end_date', endDateInput.value);
    
    const response = await fetch(`/api/dashboard/operating-systems?${params}`);
    if (!response.ok) throw new Error('Failed to load OS data');
    
    const data = await response.json();
    renderOSChart(data);
}

function renderOverviewStats(data) {
    const container = document.getElementById('overview-stats');
    if (!container) return;
    
    if (!data || data.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">
                    <i class="fas fa-chart-bar"></i>
                </div>
                <h3>No Analytics Data Yet</h3>
                <p>Start collecting analytics by creating API keys and integrating the Klyne SDK into your packages.</p>
                <a href="/dashboard" class="cta-button">
                    <i class="fas fa-key"></i>
                    Create API Key
                </a>
            </div>
        `;
        return;
    }
    
    // Aggregate totals across all packages
    const totals = data.reduce((acc, pkg) => ({
        events: acc.events + pkg.total_events,
        sessions: acc.sessions + pkg.total_sessions,
        packages: acc.packages + 1,
        avgDaily: acc.avgDaily + pkg.avg_daily_events
    }), { events: 0, sessions: 0, packages: 0, avgDaily: 0 });
    
    container.innerHTML = `
        <div class="stat-card fade-in">
            <div class="stat-icon">
                <i class="fas fa-box"></i>
            </div>
            <div class="stat-value">${totals.packages}</div>
            <div class="stat-label">Active Packages</div>
            <div class="stat-change">
                <i class="fas fa-info-circle"></i>
                Tracking ${totals.packages} package${totals.packages !== 1 ? 's' : ''}
            </div>
        </div>
        <div class="stat-card fade-in">
            <div class="stat-icon">
                <i class="fas fa-chart-line"></i>
            </div>
            <div class="stat-value">${formatNumber(totals.events)}</div>
            <div class="stat-label">Total Events</div>
            <div class="stat-change positive">
                <i class="fas fa-arrow-up"></i>
                All time activity
            </div>
        </div>
        <div class="stat-card fade-in">
            <div class="stat-icon">
                <i class="fas fa-users"></i>
            </div>
            <div class="stat-value">${formatNumber(totals.sessions)}</div>
            <div class="stat-label">Total Sessions</div>
            <div class="stat-change positive">
                <i class="fas fa-arrow-up"></i>
                Unique user sessions
            </div>
        </div>
        <div class="stat-card fade-in">
            <div class="stat-icon">
                <i class="fas fa-calendar-day"></i>
            </div>
            <div class="stat-value">${Math.round(totals.avgDaily / totals.packages || 0)}</div>
            <div class="stat-label">Avg Daily Events</div>
            <div class="stat-change">
                <i class="fas fa-chart-bar"></i>
                Per package average
            </div>
        </div>
    `;
}

function updatePackageFilter(data) {
    const select = document.getElementById('package-filter');
    if (!select) return;
    
    packages = data.map(pkg => pkg.package_name);
    
    // Clear and repopulate options
    select.innerHTML = '<option value="">All Packages</option>';
    packages.forEach(pkg => {
        const option = document.createElement('option');
        option.value = pkg;
        option.textContent = pkg;
        if (pkg === currentPackage) option.selected = true;
        select.appendChild(option);
    });
}

function renderTimeSeriesChart(data) {
    const canvas = document.getElementById('timeseries-chart');
    if (!canvas) {
        console.error('Timeseries chart canvas not found');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        console.error('Could not get canvas context');
        return;
    }
    
    // Destroy existing chart
    if (charts.timeseries) {
        charts.timeseries.destroy();
    }
    
    if (!data.dates || data.dates.length === 0) {
        canvas.parentElement.innerHTML = `
            <div class="no-data">
                <div class="no-data-icon">
                    <i class="fas fa-chart-area"></i>
                </div>
                <h3>No time series data available</h3>
                <p>Data will appear here once you start receiving analytics events</p>
            </div>
        `;
        return;
    }

    charts.timeseries = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [
                {
                    label: 'Events',
                    data: data.events,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Sessions',
                    data: data.sessions,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    align: 'end'
                },
                title: {
                    display: false
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM dd'
                        }
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

function renderPythonVersionChart(data) {
    const canvas = document.getElementById('python-chart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    if (charts.python) {
        charts.python.destroy();
    }

    console.log('Python version data:', data);
    
    // Handle both array format and object format
    let versions, counts;
    
    if (Array.isArray(data)) {
        // API returns array of objects with python_version and event_count
        if (data.length === 0) {
            canvas.parentElement.innerHTML = `
                <div class="no-data">
                    <div class="no-data-icon">
                        <i class="fab fa-python"></i>
                    </div>
                    <h3>No Python version data</h3>
                    <p>Version distribution will appear here</p>
                </div>
            `;
            return;
        }
        
        versions = data.map(item => item.python_version);
        counts = data.map(item => item.event_count);
    }
    
    charts.python = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: versions,
            datasets: [{
                data: counts,
                backgroundColor: [
                    '#6366f1', '#8b5cf6', '#06b6d4', '#10b981', 
                    '#f59e0b', '#ef4444', '#ec4899', '#84cc16'
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true
                    }
                }
            }
        }
    });
}

function renderOSChart(data) {
    const canvas = document.getElementById('os-chart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    if (charts.os) {
        charts.os.destroy();
    }
    
    console.log('OS data:', data);
    
    // Handle both array format and object format
    let operating_systems, counts;
    
    if (Array.isArray(data)) {
        // API returns array of objects with operating_system and event_count
        if (data.length === 0) {
            canvas.parentElement.innerHTML = `
                <div class="no-data">
                    <div class="no-data-icon">
                        <i class="fas fa-desktop"></i>
                    </div>
                    <h3>No OS data available</h3>
                    <p>Operating system distribution will appear here</p>
                </div>
            `;
            return;
        }
        
        operating_systems = data.map(item => item.os_type);
        counts = data.map(item => item.event_count);
    }
    
    charts.os = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: operating_systems,
            datasets: [{
                data: counts,
                backgroundColor: [
                    '#6366f1', '#8b5cf6', '#06b6d4', '#10b981',
                    '#f59e0b', '#ef4444', '#ec4899', '#84cc16'
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true
                    }
                }
            }
        }
    });
}

// Utility functions
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function showLoading() {
    // Add loading state to dashboard
    console.log('Loading data...');
}

function hideLoading() {
    // Remove loading state
    console.log('Loading complete');
}

function showError(message) {
    console.error('Dashboard error:', message);
    // You could add a toast notification here
}

function clearError() {
    // Clear any existing error messages
}