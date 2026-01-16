/**
 * SC2 AI 대시보드 테스트 데이터 생성 스크립트 (API 버전)
 * 
 * 사용법:
 * node scripts/seed-test-data-api.mjs [--url https://your-domain.manus.space]
 * 
 * 예시:
 * node scripts/seed-test-data-api.mjs
 * node scripts/seed-test-data-api.mjs --url https://sc2aidash-bncleqgg.manus.space
 * 
 * 이 스크립트는 웹 대시보드의 tRPC API를 통해 다음 데이터를 생성합니다:
 * - 게임 세션 (20개)
 * - 학습 에피소드 (50개)
 * - 봇 설정 (5개)
 * - AI Arena 경기 기록 (30개)
 */

// 기본 설정
const DASHBOARD_URL = process.argv.includes('--url')
  ? process.argv[process.argv.indexOf('--url') + 1]
  : 'http://localhost:3000';

const API_BASE = `${DASHBOARD_URL}/api/trpc`;

// 유틸리티 함수들
const randomInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
const randomFloat = (min, max) => Math.random() * (max - min) + min;
const randomChoice = (arr) => arr[Math.floor(Math.random() * arr.length)];

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const maps = [
  'Automaton LE',
  'Catalyst LE',
  'Cerulean Fall LE',
  'Disco Bloodbath LE',
  'Ephemeron LE',
  'Frozen Temple LE',
  'Golden Wall LE',
  'Hardwire LE',
];

const races = ['Protoss', 'Terran', 'Zerg'];
const difficulties = ['Easy', 'Medium', 'Hard', 'Harder', 'Insane'];
const strategies = ['Aggressive', 'Defensive', 'Balanced', 'Economic', 'Rush'];

// API 호출 함수
async function callApi(endpoint, data) {
  try {
    const response = await fetch(`${API_BASE}/${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        json: data,
      }),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    const result = await response.json();
    return result.result?.data;
  } catch (error) {
    console.error(`❌ API 호출 실패 (${endpoint}):`, error.message);
    return null;
  }
}

// 게임 세션 생성
async function createGameSessions() {
  console.log('📊 게임 세션 생성 중...');
  
  let created = 0;
  
  for (let i = 0; i < 20; i++) {
    const isVictory = Math.random() > 0.4; // 60% 승률
    const duration = randomInt(600, 3600); // 10분 ~ 60분
    
    const sessionData = {
      mapName: randomChoice(maps),
      enemyRace: randomChoice(races),
      difficulty: randomChoice(difficulties),
      gamePhase: randomChoice(['Early Game', 'Mid Game', 'Late Game', 'Finished']),
      result: isVictory ? 'Victory' : 'Defeat',
      finalMinerals: randomInt(100, 2000),
      finalGas: randomInt(50, 1500),
      finalSupply: randomInt(50, 200),
      unitsKilled: isVictory ? randomInt(50, 200) : randomInt(10, 100),
      unitsLost: isVictory ? randomInt(10, 80) : randomInt(30, 150),
      duration,
    };
    
    const result = await callApi('game.createSession', sessionData);
    if (result) {
      created++;
      process.stdout.write(`\r   생성됨: ${created}/20`);
    }
    
    await sleep(100); // API 레이트 제한 회피
  }
  
  console.log(`\n✅ ${created}개의 게임 세션 생성됨`);
}

// 학습 에피소드 생성
async function createTrainingEpisodes() {
  console.log('🧠 학습 에피소드 생성 중...');
  
  let created = 0;
  
  for (let i = 0; i < 50; i++) {
    const episodeNumber = i + 1;
    const gamesPlayed = randomInt(5, 20);
    const wins = randomInt(Math.floor(gamesPlayed * 0.4), gamesPlayed);
    const winRate = wins / gamesPlayed;
    
    // 에피소드가 진행될수록 성능 개선
    const improvementFactor = i / 50;
    const baseReward = 100 + improvementFactor * 200;
    const totalReward = baseReward + randomFloat(-50, 50);
    const averageReward = totalReward / gamesPlayed;
    const loss = Math.max(0.1, 2 - improvementFactor * 1.5 + randomFloat(-0.5, 0.5));
    
    const episodeData = {
      episodeNumber,
      totalReward: parseFloat(totalReward.toFixed(2)),
      averageReward: parseFloat(averageReward.toFixed(2)),
      winRate: parseFloat(winRate.toFixed(3)),
      gamesPlayed,
      loss: parseFloat(loss.toFixed(4)),
      notes: i % 5 === 0 ? `에피소드 ${episodeNumber} 완료 - 성능 개선됨` : null,
    };
    
    const result = await callApi('training.createEpisode', episodeData);
    if (result) {
      created++;
      process.stdout.write(`\r   생성됨: ${created}/50`);
    }
    
    await sleep(50);
  }
  
  console.log(`\n✅ ${created}개의 학습 에피소드 생성됨`);
}

// 봇 설정 생성
async function createBotConfigs() {
  console.log('🤖 봇 설정 생성 중...');
  
  const configs = [
    {
      name: '공격형 저글링 러시',
      strategy: 'Aggressive',
      buildOrder: JSON.stringify({ units: ['Drone', 'Drone', 'Overlord', 'Zergling', 'Zergling'] }),
      description: '초반 저글링 러시로 상대를 압박하는 공격형 전략',
    },
    {
      name: '방어형 뮤탈리스크',
      strategy: 'Defensive',
      buildOrder: JSON.stringify({ units: ['Drone', 'Overlord', 'Hatchery', 'Mutalisk'] }),
      description: '안정적인 경제 운영으로 뮤탈리스크 빌드를 완성하는 전략',
    },
    {
      name: '균형형 하이브',
      strategy: 'Balanced',
      buildOrder: JSON.stringify({ units: ['Drone', 'Overlord', 'Hatchery', 'Hydralisk', 'Ultralisk'] }),
      description: '경제와 군사력의 균형을 맞춘 중반 전략',
    },
    {
      name: '경제형 확장',
      strategy: 'Economic',
      buildOrder: JSON.stringify({ units: ['Drone', 'Drone', 'Hatchery', 'Hatchery'] }),
      description: '다중 해처리로 경제를 극대화하는 전략',
    },
    {
      name: '초반 러시 (6풀)',
      strategy: 'Rush',
      buildOrder: JSON.stringify({ units: ['Drone', 'Overlord', 'Spawning Pool', 'Zergling'] }),
      description: '6드론 풀로 초반 압박을 가하는 극공격형 전략',
    },
  ];
  
  let created = 0;
  
  for (const config of configs) {
    const result = await callApi('bot.createConfig', config);
    if (result) {
      created++;
      console.log(`   ✓ "${config.name}" 생성됨`);
    }
    await sleep(100);
  }
  
  console.log(`✅ ${created}개의 봇 설정 생성됨`);
}

// AI Arena 경기 기록 생성
async function createArenaMatches() {
  console.log('🏆 AI Arena 경기 기록 생성 중...');
  
  let created = 0;
  let elo = 1600;
  let wins = 0;
  let losses = 0;
  
  for (let i = 0; i < 30; i++) {
    const isWin = Math.random() > 0.45; // 55% 승률
    const eloChange = isWin ? randomInt(10, 30) : randomInt(-30, -10);
    elo += eloChange;
    
    if (isWin) wins++;
    else losses++;
    
    const matchData = {
      matchId: `match-${Date.now()}-${i}`,
      opponentName: `Bot-${randomInt(1000, 9999)}`,
      opponentRace: randomChoice(races),
      mapName: randomChoice(maps),
      result: isWin ? 'Win' : 'Loss',
      elo,
    };
    
    const result = await callApi('arena.createMatch', matchData);
    if (result) {
      created++;
      process.stdout.write(`\r   생성됨: ${created}/30`);
    }
    
    await sleep(50);
  }
  
  const winRate = ((wins / (wins + losses)) * 100).toFixed(1);
  console.log(`\n✅ ${created}개의 Arena 경기 기록 생성됨 (최종 ELO: ${elo}, 승률: ${winRate}%)`);
}

// 메인 함수
async function main() {
  try {
    console.log('\n🚀 SC2 AI 대시보드 테스트 데이터 생성 시작\n');
    console.log(`📍 대시보드 URL: ${DASHBOARD_URL}\n`);
    
    // 연결 확인
    console.log('🔗 대시보드 연결 확인 중...');
    const healthCheck = await fetch(`${DASHBOARD_URL}/api/trpc/auth.me`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ json: {} }),
    });
    
    if (!healthCheck.ok) {
      throw new Error(`대시보드에 연결할 수 없습니다 (상태: ${healthCheck.status})`);
    }
    console.log('✅ 대시보드 연결 성공\n');
    
    // 데이터 생성
    await createGameSessions();
    await createTrainingEpisodes();
    await createBotConfigs();
    await createArenaMatches();
    
    console.log('\n✨ 모든 테스트 데이터 생성 완료!\n');
    console.log('📊 생성된 데이터 요약:');
    console.log(`   - 게임 세션: 20개`);
    console.log(`   - 학습 에피소드: 50개`);
    console.log(`   - 봇 설정: 5개`);
    console.log(`   - Arena 경기: 30개`);
    console.log(`\n🌐 대시보드에서 확인하세요: ${DASHBOARD_URL}\n`);
    
  } catch (error) {
    console.error('\n❌ 오류 발생:', error.message);
    process.exit(1);
  }
}

main();
