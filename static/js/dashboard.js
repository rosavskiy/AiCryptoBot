// AI Crypto Bot Dashboard JavaScript

// Initialize Socket.IO connection
const socket = io();

// State
let pnlChart = null;
let config = {};
let startTime = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeChart();
    setupEventListeners();
    loadConfig();
    connectWebSocket();
});

// Setup event listeners
function setupEventListeners() {
    document.getElementById('btn-start').addEventListener('click', startBot);
    document.getElementById('btn-pause').addEventListener('click', pauseBot);
    document.getElementById('btn-stop').addEventListener('click', stopBot);
    document.getElementById('btn-clear-logs').addEventListener('click', clearLogs);
}

// WebSocket connection
function connectWebSocket() {
    socket.on('connect', () => {
        console.log('Connected to server');
        updateConnectionStatus(true);
        socket.emit('request_update');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        updateConnectionStatus(false);
    });

    socket.on('status_update', (data) => {
        updateDashboard(data);
    });

    socket.on('trade_update', (data) => {
        handleTradeUpdate(data);
        addLog('success', `Trade update: ${data.symbol} - ${data.side}`);
    });

    socket.on('log_update', (data) => {
        addLog(data.level.toLowerCase(), data.message);
    });
}

// Load configuration
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        config = await response.json();
        updateConfigDisplay();
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

// Update config display
function updateConfigDisplay() {
    document.getElementById('info-symbol').textContent = config.symbols?.[0] || 'BTC/USDT';
    document.getElementById('info-interval').textContent = config.interval || '15m';
    document.getElementById('info-ml-threshold').textContent = `${(config.ml_threshold * 100).toFixed(0)}%`;
    document.getElementById('info-risk').textContent = `${(config.risk_per_trade * 100).toFixed(1)}%`;
}

// Update dashboard with new data
function updateDashboard(data) {
    // Update status
    updateStatus(data.status);
    
    // Update balance
    document.getElementById('balance').textContent = `$${data.balance.toFixed(2)}`;
    const balanceChange = ((data.balance - data.initial_balance) / data.initial_balance * 100);
    const balanceChangeEl = document.getElementById('balance-change');
    balanceChangeEl.textContent = `${balanceChange >= 0 ? '+' : ''}${balanceChange.toFixed(2)}%`;
    balanceChangeEl.className = `stat-change ${balanceChange >= 0 ? 'positive' : 'negative'}`;
    
    // Update PnL
    document.getElementById('total-pnl').textContent = `$${data.total_pnl.toFixed(2)}`;
    const pnlChangeEl = document.getElementById('pnl-change');
    pnlChangeEl.textContent = `${data.total_pnl_pct >= 0 ? '+' : ''}${data.total_pnl_pct.toFixed(2)}%`;
    pnlChangeEl.className = `stat-change ${data.total_pnl >= 0 ? 'positive' : 'negative'}`;
    
    // Update trades
    document.getElementById('total-trades').textContent = data.total_trades;
    document.getElementById('win-trades').textContent = `${data.winning_trades}W`;
    document.getElementById('loss-trades').textContent = `${data.losing_trades}L`;
    document.getElementById('win-rate').textContent = `${data.win_rate.toFixed(1)}%`;
    document.getElementById('sharpe').textContent = `Sharpe: ${data.sharpe_ratio.toFixed(2)}`;
    
    // Update drawdown
    document.getElementById('info-max-dd').textContent = `${data.max_drawdown.toFixed(2)}%`;
    document.getElementById('info-current-dd').textContent = `${data.current_drawdown.toFixed(2)}%`;
    
    // Update uptime
    if (data.start_time) {
        updateUptime(data.start_time);
    }
    
    // Update positions
    updatePositions(data.open_positions);
    
    // Update trades history
    updateTradesHistory(data.closed_trades);
    
    // Update last signal
    if (data.last_signal) {
        updateLastSignal(data.last_signal);
    }
    
    // Update chart
    updateChart(data);
    
    // Update last update time
    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
}

// Update bot status
function updateStatus(status) {
    const statusBadge = document.getElementById('bot-status');
    const infoStatus = document.getElementById('info-status');
    const btnStart = document.getElementById('btn-start');
    const btnPause = document.getElementById('btn-pause');
    const btnStop = document.getElementById('btn-stop');
    
    statusBadge.className = `status-badge ${status}`;
    
    if (status === 'running') {
        statusBadge.innerHTML = '<i class="fas fa-circle"></i><span>Работает</span>';
        infoStatus.textContent = 'Работает';
        btnStart.disabled = true;
        btnPause.disabled = false;
        btnStop.disabled = false;
    } else if (status === 'paused') {
        statusBadge.innerHTML = '<i class="fas fa-circle"></i><span>Пауза</span>';
        infoStatus.textContent = 'Пауза';
        btnStart.disabled = false;
        btnPause.disabled = true;
        btnStop.disabled = false;
    } else {
        statusBadge.innerHTML = '<i class="fas fa-circle"></i><span>Остановлен</span>';
        infoStatus.textContent = 'Остановлен';
        btnStart.disabled = false;
        btnPause.disabled = true;
        btnStop.disabled = true;
    }
}

// Update connection status
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connection-status');
    statusEl.textContent = connected ? '✓' : '✗';
    statusEl.className = connected ? 'connected' : 'disconnected';
}

// Update uptime
function updateUptime(startTimeStr) {
    if (!startTimeStr) return;
    
    const startTime = new Date(startTimeStr);
    const now = new Date();
    const diff = now - startTime;
    
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    
    document.getElementById('info-uptime').textContent = 
        `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// Update positions table
function updatePositions(positions) {
    const tbody = document.getElementById('positions-body');
    const count = document.getElementById('positions-count');
    
    count.textContent = positions.length;
    
    if (positions.length === 0) {
        tbody.innerHTML = '<tr class="empty-state"><td colspan="6">Нет открытых позиций</td></tr>';
        return;
    }
    
    tbody.innerHTML = positions.map(pos => `
        <tr>
            <td>${pos.symbol}</td>
            <td class="side-${pos.side.toLowerCase()}">${pos.side.toUpperCase()}</td>
            <td>$${pos.entry_price.toFixed(2)}</td>
            <td>$${pos.current_price?.toFixed(2) || '--'}</td>
            <td class="${pos.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}">
                ${pos.pnl >= 0 ? '+' : ''}$${pos.pnl?.toFixed(2) || '0.00'}
                (${pos.pnl_pct >= 0 ? '+' : ''}${pos.pnl_pct?.toFixed(2) || '0.00'}%)
            </td>
            <td>${new Date(pos.entry_time).toLocaleTimeString()}</td>
        </tr>
    `).join('');
}

// Update trades history
function updateTradesHistory(trades) {
    const tbody = document.getElementById('trades-body');
    
    if (!trades || trades.length === 0) {
        tbody.innerHTML = '<tr class="empty-state"><td colspan="6">Нет завершённых сделок</td></tr>';
        return;
    }
    
    tbody.innerHTML = trades.slice(-20).reverse().map(trade => `
        <tr>
            <td>${new Date(trade.exit_time).toLocaleTimeString()}</td>
            <td>${trade.symbol}</td>
            <td class="side-${trade.side.toLowerCase()}">${trade.side.toUpperCase()}</td>
            <td class="${trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}">
                ${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)}
            </td>
            <td class="${trade.pnl_pct >= 0 ? 'pnl-positive' : 'pnl-negative'}">
                ${trade.pnl_pct >= 0 ? '+' : ''}${trade.pnl_pct.toFixed(2)}%
            </td>
            <td>${trade.exit_reason}</td>
        </tr>
    `).join('');
}

// Update last signal
function updateLastSignal(signal) {
    const container = document.getElementById('last-signal');
    
    container.innerHTML = `
        <div class="signal-item">
            <span class="signal-label">Время:</span>
            <span class="signal-value">${new Date(signal.timestamp).toLocaleString()}</span>
        </div>
        <div class="signal-item">
            <span class="signal-label">Сигнал:</span>
            <span class="signal-value side-${signal.signal === 'buy' ? 'long' : 'short'}">
                ${signal.signal.toUpperCase()}
            </span>
        </div>
        <div class="signal-item">
            <span class="signal-label">ML Confidence:</span>
            <span class="signal-value">${(signal.ml_confidence * 100).toFixed(1)}%</span>
        </div>
        <div class="signal-item">
            <span class="signal-label">Sentiment:</span>
            <span class="signal-value">${signal.sentiment?.toFixed(2) || 'N/A'}</span>
        </div>
    `;
}

// Initialize chart
function initializeChart() {
    const ctx = document.getElementById('pnl-chart').getContext('2d');
    
    pnlChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'P&L ($)',
                data: [],
                borderColor: '#00d9ff',
                backgroundColor: 'rgba(0, 217, 255, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: '#e0e0e0'
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#a0a0a0'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#a0a0a0',
                        callback: function(value) {
                            return '$' + value.toFixed(0);
                        }
                    }
                }
            }
        }
    });
}

// Update chart
function updateChart(data) {
    if (!pnlChart) return;
    
    // Add new data point
    const timestamp = new Date().toLocaleTimeString();
    
    pnlChart.data.labels.push(timestamp);
    pnlChart.data.datasets[0].data.push(data.total_pnl);
    
    // Keep only last 50 points
    if (pnlChart.data.labels.length > 50) {
        pnlChart.data.labels.shift();
        pnlChart.data.datasets[0].data.shift();
    }
    
    pnlChart.update('none'); // Update without animation for better performance
}

// Add log entry
function addLog(level, message) {
    const container = document.getElementById('logs-container');
    const time = new Date().toLocaleTimeString();
    
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${level}`;
    logEntry.innerHTML = `
        <span class="log-time">[${time}]</span>
        <span class="log-message">${message}</span>
    `;
    
    container.appendChild(logEntry);
    
    // Auto-scroll to bottom
    container.scrollTop = container.scrollHeight;
    
    // Keep only last 100 logs
    while (container.children.length > 100) {
        container.removeChild(container.firstChild);
    }
}

// Clear logs
function clearLogs() {
    const container = document.getElementById('logs-container');
    container.innerHTML = '<div class="log-entry info"><span class="log-time">[--:--:--]</span><span class="log-message">Логи очищены</span></div>';
}

// Bot control functions
async function startBot() {
    try {
        addLog('info', 'Запуск бота...');
        const response = await fetch('/api/control/start', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            addLog('success', 'Бот запущен');
            // Request immediate update
            socket.emit('request_update');
        } else {
            addLog('error', `Ошибка запуска: ${data.error}`);
        }
    } catch (error) {
        addLog('error', `Ошибка запуска: ${error.message}`);
    }
}

async function pauseBot() {
    try {
        addLog('info', 'Остановка бота...');
        const response = await fetch('/api/control/pause', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            addLog('warning', 'Бот поставлен на паузу');
            // Request immediate update
            socket.emit('request_update');
        } else {
            addLog('error', `Ошибка паузы: ${data.error}`);
        }
    } catch (error) {
        addLog('error', `Ошибка паузы: ${error.message}`);
    }
}

async function stopBot() {
    try {
        addLog('info', 'Остановка бота...');
        const response = await fetch('/api/control/stop', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            addLog('info', 'Бот остановлен');
            // Request immediate update
            socket.emit('request_update');
        } else {
            addLog('error', `Ошибка остановки: ${data.error}`);
        }
    } catch (error) {
        addLog('error', `Ошибка остановки: ${error.message}`);
    }
}

// Handle trade update
function handleTradeUpdate(data) {
    // Refresh trades and positions
    socket.emit('request_update');
}

// Auto-refresh every 2 seconds when running
setInterval(() => {
    const statusBadge = document.getElementById('bot-status');
    if (statusBadge.classList.contains('running')) {
        // Update uptime if running
        const uptimeEl = document.getElementById('info-uptime');
        const currentUptime = uptimeEl.textContent;
        if (currentUptime && currentUptime !== '--') {
            const parts = currentUptime.split(':');
            let seconds = parseInt(parts[2]) + 1;
            let minutes = parseInt(parts[1]);
            let hours = parseInt(parts[0]);
            
            if (seconds >= 60) {
                seconds = 0;
                minutes++;
            }
            if (minutes >= 60) {
                minutes = 0;
                hours++;
            }
            
            uptimeEl.textContent = 
                `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
    }
}, 1000);
