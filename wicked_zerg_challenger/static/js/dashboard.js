/* Wicked Zerg AI Dashboard - JavaScript */

// API 베이스 URL (로컬 개발용)
const API_BASE = 'http://localhost:8001';

// 시간 업데이트
setInterval(() => {
    const now = new Date();
    document.getElementById('current-time').textContent = now.toLocaleTimeString('ko-KR');
}, 1000);

// Fetch 헬퍼 함수
async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API 오류 (${endpoint}):`, error);
        return null;
    }
}

async function postAPI(endpoint, data) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API 오류 (${endpoint}):`, error);
        return null;
    }
}

// 게임 상태 업데이트
async function updateGameState() {
    const data = await fetchAPI('/api/game-state');
    if (!data) return;
    
    // 게임 상태
    const statusMap = {
        'READY': '준비 중',
        'PLAYING': '진행 중',
        'PAUSED': '일시정지',
        'STOPPED': '중지',
        'FINISHED': '종료'
    };
    document.getElementById('game-status').textContent = statusMap[data.game_status] || data.game_status;
    document.getElementById('game-frame').textContent = data.current_frame.toLocaleString();
    document.getElementById('game-map').textContent = data.map_name;
    document.getElementById('threat-level').textContent = data.threat_level;
    
    // 자원
    document.getElementById('mineral-value').textContent = data.minerals.toLocaleString();
    document.getElementById('vespene-value').textContent = data.vespene.toLocaleString();
    document.getElementById('supply-value').textContent = `${data.supply_used}/${data.supply_cap}`;
    
    // 자원 바
    const mineralPercent = Math.min((data.minerals / 500) * 100, 100);
    const vespenePercent = Math.min((data.vespene / 500) * 100, 100);
    document.getElementById('mineral-bar').style.width = mineralPercent + '%';
    document.getElementById('vespene-bar').style.width = vespenePercent + '%';
    
    // 유닛
    document.getElementById('zergling-count').textContent = data.units.zerglings;
    document.getElementById('roach-count').textContent = data.units.roaches;
    document.getElementById('hydra-count').textContent = data.units.hydralisks;
    
    // 마지막 업데이트
    const now = new Date();
    document.getElementById('refresh-time').textContent = 
        `마지막 업데이트: ${now.toLocaleTimeString('ko-KR')}`;
}

// 전투 통계 업데이트
async function updateCombatStats() {
    const data = await fetchAPI('/api/combat-stats');
    if (!data) return;
    
    document.getElementById('win-rate').textContent = data.win_rate.toFixed(1) + '%';
    document.getElementById('win-count').textContent = data.wins;
    document.getElementById('loss-count').textContent = data.losses;
    document.getElementById('kda-ratio').textContent = data.kda_ratio.toFixed(2);
    document.getElementById('avg-army-supply').textContent = data.avg_army_supply.toFixed(1);
    document.getElementById('enemy-killed-supply').textContent = data.enemy_killed_supply.toLocaleString();
    document.getElementById('supply-lost').textContent = data.supply_lost.toLocaleString();
    
    // 승률 차트
    updateWinRateChart([35.2, 38.1, 41.5, 42.8, data.win_rate]);
}

// 학습 진행 업데이트
async function updateLearningProgress() {
    const data = await fetchAPI('/api/learning-progress');
    if (!data) return;
    
    document.getElementById('episode-progress').textContent = 
        `${data.episode} / ${data.total_episodes}`;
    document.getElementById('episode-bar').style.width = data.progress_percent + '%';
    document.getElementById('episode-percent').textContent = data.progress_percent.toFixed(1) + '%';
    
    document.getElementById('avg-reward').textContent = data.average_reward.toFixed(1);
    document.getElementById('loss-value').textContent = data.loss.toFixed(4);
    document.getElementById('training-hours').textContent = data.training_hours.toFixed(1) + 'h';
    
    // 학습 차트
    updateLearningChart(data.win_rate_trend);
    
    // 훈련 로그 업데이트
    updateTrainingLogs(data.training_logs);
}

// 봇 설정 로드
async function loadBotConfig() {
    const data = await fetchAPI('/api/bot-config');
    if (!data) return;
    
    document.getElementById('strategy-select').value = data.strategy_mode.toLowerCase();
    document.getElementById('auto-mode').checked = data.auto_mode;
    document.getElementById('aggressive-mode').checked = data.aggressive_mode;
}

// 훈련 로그 업데이트
function updateTrainingLogs(logs) {
    const logContainer = document.getElementById('training-log');
    logContainer.innerHTML = '';
    
    logs.forEach(log => {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.innerHTML = `
            <span class="log-time">[${log.time}]</span>
            <span class="log-text">${log.message}</span>
        `;
        logContainer.appendChild(entry);
    });
}

// Win Rate Chart
let winRateChart = null;
function updateWinRateChart(data) {
    const ctx = document.getElementById('winRateChart');
    if (!ctx) return;
    
    if (winRateChart) {
        winRateChart.data.datasets[0].data = data;
        winRateChart.update();
    } else {
        winRateChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['1주일 전', '5일 전', '3일 전', '어제', '오늘'],
                datasets: [{
                    label: '승률 (%)',
                    data: data,
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 6,
                    pointBackgroundColor: '#00ff88',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        labels: { color: '#00d4ff', font: { size: 12 } }
                    }
                },
                scales: {
                    y: {
                        ticks: { color: '#888' },
                        grid: { color: 'rgba(0, 212, 255, 0.1)' },
                        max: 100
                    },
                    x: {
                        ticks: { color: '#888' },
                        grid: { color: 'rgba(0, 212, 255, 0.1)' }
                    }
                }
            }
        });
    }
}

// Learning Chart
let learningChart = null;
function updateLearningChart(data) {
    const ctx = document.getElementById('learningChart');
    if (!ctx) return;
    
    if (learningChart) {
        learningChart.data.datasets[0].data = data;
        learningChart.update();
    } else {
        learningChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map((_, i) => `${i + 1}번째`),
                datasets: [{
                    label: '승률 추이 (%)',
                    data: data,
                    backgroundColor: data.map((val, i) => {
                        if (i < 2) return 'rgba(255, 107, 107, 0.7)';
                        if (i < 3) return 'rgba(255, 187, 0, 0.7)';
                        return 'rgba(0, 255, 136, 0.7)';
                    }),
                    borderColor: '#00ff88',
                    borderWidth: 2,
                    borderRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        labels: { color: '#00d4ff', font: { size: 12 } }
                    }
                },
                scales: {
                    y: {
                        ticks: { color: '#888' },
                        grid: { color: 'rgba(0, 212, 255, 0.1)' },
                        max: 100
                    },
                    x: {
                        ticks: { color: '#888' },
                        grid: { color: 'rgba(0, 212, 255, 0.1)' }
                    }
                }
            }
        });
    }
}

// 버튼 이벤트 핸들러
document.getElementById('btn-play').addEventListener('click', async () => {
    const result = await postAPI('/api/control', { type: 'play' });
    if (result?.status === 'success') {
        alert(result.message);
    }
});

document.getElementById('btn-pause').addEventListener('click', async () => {
    const result = await postAPI('/api/control', { type: 'pause' });
    if (result?.status === 'success') {
        alert(result.message);
    }
});

document.getElementById('btn-stop').addEventListener('click', async () => {
    const result = await postAPI('/api/control', { type: 'stop' });
    if (result?.status === 'success') {
        alert(result.message);
    }
});

// 전략 선택
document.getElementById('strategy-select').addEventListener('change', async (e) => {
    const strategy = e.target.value.toUpperCase();
    const result = await postAPI('/api/control', { type: 'strategy', value: strategy });
    if (result?.status === 'success') {
        console.log(result.message);
    }
});

// 자동 모드 토글
document.getElementById('auto-mode').addEventListener('change', async (e) => {
    await postAPI('/api/bot-config/update', {
        auto_mode: e.target.checked
    });
});

// 공격적 모드 토글
document.getElementById('aggressive-mode').addEventListener('change', async (e) => {
    await postAPI('/api/bot-config/update', {
        aggressive_mode: e.target.checked
    });
});

// 초기화 및 주기적 업데이트
(async () => {
    // 초기 로드
    await loadBotConfig();
    await updateGameState();
    await updateCombatStats();
    await updateLearningProgress();
    
    // 2초마다 업데이트
    setInterval(async () => {
        await updateGameState();
        await updateCombatStats();
        await updateLearningProgress();
    }, 2000);
})();

