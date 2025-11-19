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
let currentAggregation = 'day';
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
    const aggregationSelector = document.getElementById('aggregation-period');

    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshData);
    }

    if (packageFilter) {
        packageFilter.addEventListener('change', function() {
            currentPackage = this.value;
            refreshData();
        });
    }

    if (aggregationSelector) {
        aggregationSelector.addEventListener('change', function() {
            currentAggregation = this.value;
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
            loadOSData(),
            loadCustomEvents()
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
    if (currentAggregation) params.append('aggregation', currentAggregation);

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
        uniqueUsers: acc.uniqueUsers + (pkg.total_unique_users || 0),
        packages: acc.packages + 1,
        avgDaily: acc.avgDaily + pkg.avg_daily_events
    }), { events: 0, sessions: 0, uniqueUsers: 0, packages: 0, avgDaily: 0 });
    
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
                <i class="fas fa-user-check"></i>
            </div>
            <div class="stat-value">${formatNumber(totals.uniqueUsers)}</div>
            <div class="stat-label">Unique Users</div>
            <div class="stat-change positive">
                <i class="fas fa-fingerprint"></i>
                Distinct installations
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
                },
                {
                    label: 'Unique Users',
                    data: data.unique_users || [],
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
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

// ============================================================================
// CUSTOM EVENTS TRACKING
// ============================================================================

let selectedEventTypes = new Set();
let customEventsChart = null;

function buildQueryParams() {
    const params = new URLSearchParams();

    if (currentPackage) {
        params.append('package_name', currentPackage);
    }

    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');

    if (startDateInput?.value) {
        params.append('start_date', startDateInput.value);
    }
    if (endDateInput?.value) {
        params.append('end_date', endDateInput.value);
    }

    return params;
}

async function loadCustomEvents() {
    try {
        // Show loading
        document.getElementById('custom-events-loading').style.display = 'block';
        document.getElementById('custom-events-empty').style.display = 'none';
        document.getElementById('custom-events-selector').style.display = 'none';
        document.getElementById('custom-events-chart-container').style.display = 'none';
        document.getElementById('custom-events-properties').style.display = 'none';

        // Get event types
        const params = buildQueryParams();
        const response = await fetch(`/api/dashboard/custom-events/types?${params}`);

        if (!response.ok) {
            throw new Error('Failed to load custom events');
        }

        const eventTypes = await response.json();

        // Hide loading
        document.getElementById('custom-events-loading').style.display = 'none';

        if (eventTypes.length === 0) {
            // Show empty state
            document.getElementById('custom-events-empty').style.display = 'block';
            return;
        }

        // Show selector and render event chips
        document.getElementById('custom-events-selector').style.display = 'block';
        renderEventTypeChips(eventTypes);

        // Select all events by default
        selectedEventTypes = new Set(eventTypes.map(e => e.event_type));

        // Load time series data
        await loadCustomEventsTimeseries();

    } catch (error) {
        console.error('Error loading custom events:', error);
        document.getElementById('custom-events-loading').style.display = 'none';
        document.getElementById('custom-events-empty').style.display = 'block';
    }
}

function renderEventTypeChips(eventTypes) {
    const container = document.getElementById('event-type-chips');
    container.innerHTML = '';

    eventTypes.forEach(eventType => {
        const chip = document.createElement('button');
        chip.className = 'event-type-chip';
        chip.dataset.eventType = eventType.event_type;
        chip.innerHTML = `
            <span class="event-name">${eventType.event_type}</span>
            <span class="event-count">${eventType.total_count}</span>
        `;

        chip.style.cssText = `
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: #6366f1;
            color: white;
            border: 2px solid #6366f1;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        `;

        chip.querySelector('.event-count').style.cssText = `
            background: rgba(255, 255, 255, 0.2);
            padding: 0.125rem 0.5rem;
            border-radius: 9999px;
            font-size: 0.75rem;
        `;

        chip.addEventListener('click', () => toggleEventType(eventType.event_type, chip));
        container.appendChild(chip);
    });
}

async function toggleEventType(eventType, chipElement) {
    if (selectedEventTypes.has(eventType)) {
        selectedEventTypes.delete(eventType);
        chipElement.style.background = 'white';
        chipElement.style.color = '#6366f1';
    } else {
        selectedEventTypes.add(eventType);
        chipElement.style.background = '#6366f1';
        chipElement.style.color = 'white';
    }

    // Reload timeseries if at least one event is selected
    if (selectedEventTypes.size > 0) {
        await loadCustomEventsTimeseries();
    } else {
        // Hide chart if no events selected
        document.getElementById('custom-events-chart-container').style.display = 'none';
        document.getElementById('custom-events-properties').style.display = 'none';
    }
}

async function loadCustomEventsTimeseries() {
    if (selectedEventTypes.size === 0) return;

    try {
        const params = buildQueryParams();
        const eventTypesParam = Array.from(selectedEventTypes).join(',');

        // Add aggregation parameter
        if (currentAggregation) {
            params.append('aggregation', currentAggregation);
        }

        const response = await fetch(`/api/dashboard/custom-events/timeseries?event_types=${encodeURIComponent(eventTypesParam)}&${params}`);

        if (!response.ok) {
            throw new Error('Failed to load timeseries');
        }

        const data = await response.json();

        // Show chart container
        document.getElementById('custom-events-chart-container').style.display = 'block';

        // Render chart
        renderCustomEventsChart(data);

        // Load properties for first selected event
        if (selectedEventTypes.size > 0) {
            const firstEvent = Array.from(selectedEventTypes)[0];
            await loadEventProperties(firstEvent);
        }

    } catch (error) {
        console.error('Error loading custom events timeseries:', error);
    }
}

function renderCustomEventsChart(data) {
    const canvas = document.getElementById('customEventsChart');
    const ctx = canvas.getContext('2d');

    // Destroy existing chart
    if (customEventsChart) {
        customEventsChart.destroy();
    }

    // Prepare datasets
    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];
    const datasets = data.event_types.map((eventType, index) => {
        const color = colors[index % colors.length];
        return {
            label: eventType,
            data: data.series_data[eventType] || [],
            borderColor: color,
            backgroundColor: color + '20',
            tension: 0.4,
            fill: true,
            pointRadius: 4,
            pointHoverRadius: 6
        };
    });

    // Determine time unit based on aggregation
    let timeUnit = 'day';
    let displayFormat = 'MMM d';

    if (currentAggregation === 'week') {
        timeUnit = 'week';
        displayFormat = 'MMM d';
    } else if (currentAggregation === 'month') {
        timeUnit = 'month';
        displayFormat = 'MMM yyyy';
    }

    // Create chart
    customEventsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 13
                    },
                    bodyFont: {
                        size: 12
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: timeUnit,
                        displayFormats: {
                            day: 'MMM d',
                            week: 'MMM d',
                            month: 'MMM yyyy'
                        }
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

async function loadEventProperties(eventType) {
    try {
        const params = buildQueryParams();
        const response = await fetch(`/api/dashboard/custom-events/${encodeURIComponent(eventType)}/details?${params}`);

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        if (data.sample_properties.length === 0) {
            return;
        }

        // Show properties section
        document.getElementById('custom-events-properties').style.display = 'block';

        // Render properties (using textContent to prevent XSS)
        const container = document.getElementById('event-properties-content');
        container.innerHTML = ''; // Clear existing content

        // Create header paragraph safely
        const header = document.createElement('p');
        header.style.cssText = 'color: #6b7280; margin-bottom: 1rem; font-family: system-ui';

        const headerText = document.createTextNode('Showing recent examples for ');
        const strongElement = document.createElement('strong');
        strongElement.textContent = eventType;
        const countText = document.createTextNode(` (${data.total_count} total events)`);

        header.appendChild(headerText);
        header.appendChild(strongElement);
        header.appendChild(countText);
        container.appendChild(header);

        // Render each property sample safely
        data.sample_properties.forEach((sample, index) => {
            const propertyDiv = document.createElement('div');
            propertyDiv.style.cssText = 'margin-bottom: 1rem; padding: 1rem; background: #f9fafb; border-radius: 6px; border: 1px solid #e5e7eb';

            // Timestamp header (safe - using textContent)
            const timestampDiv = document.createElement('div');
            timestampDiv.style.cssText = 'color: #6b7280; font-size: 0.7rem; margin-bottom: 0.5rem; font-family: system-ui';
            timestampDiv.textContent = new Date(sample.timestamp).toLocaleString();
            propertyDiv.appendChild(timestampDiv);

            // JSON display (safe - using textContent to prevent XSS)
            const pre = document.createElement('pre');
            pre.style.cssText = 'margin: 0; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word';
            pre.textContent = JSON.stringify(sample.properties, null, 2);
            propertyDiv.appendChild(pre);

            container.appendChild(propertyDiv);
        });

    } catch (error) {
        console.error('Error loading event properties:', error);
    }
}