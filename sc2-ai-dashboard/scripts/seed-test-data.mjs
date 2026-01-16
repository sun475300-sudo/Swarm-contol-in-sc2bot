/**
 * SC2 AI 대시보드 테스트 데이터 생성 스크립트
 * 
 * 사용법:
 * node scripts/seed-test-data.mjs
 * 
 * 이 스크립트는 다음 데이터를 생성합니다:
 * - 게임 세션 (20개)
 * - 전투 기록 (각 게임당 여러 개)
 * - 학습 에피소드 (50개)
 * - 봇 설정 (5개)
 * - AI Arena 경기 기록 (30개)
 */

import mysql from 'mysql2/promise';
import { config } from 'dotenv';

config();

const pool = mysql.createPool({
  host: process.env.DB_HOST || 'localhost',
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASSWORD || '',
  database: process.env.DB_NAME || 'sc2_dashboard',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
});

// 유틸리티 함수들
const randomInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
const randomFloat = (min, max) => Math.random() * (max - min) + min;
const randomChoice = (arr) => arr[Math.floor(Math.random() * arr.length)];

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

// 게임 세션 생성
async function createGameSessions(connection) {
  console.log('📊 게임 세션 생성 중...');
  
  const sessions = [];
  const now = Date.now();
  
  for (let i = 0; i < 20; i++) {
    const isVictory = Math.random() > 0.4; // 60% 승률
    const duration = randomInt(600, 3600); // 10분 ~ 60분
    
    const session = {
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
      createdAt: new Date(now - i * 3600000), // 1시간씩 이전
    };
    
    const [result] = await connection.execute(
      `INSERT INTO game_sessions (mapName, enemyRace, difficulty, gamePhase, result, finalMinerals, finalGas, finalSupply, unitsKilled, unitsLost, duration, createdAt)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        session.mapName,
        session.enemyRace,
        session.difficulty,
        session.gamePhase,
        session.result,
        session.finalMinerals,
        session.finalGas,
        session.finalSupply,
        session.unitsKilled,
        session.unitsLost,
        session.duration,
        session.createdAt,
      ]
    );
    
    sessions.push({ id: result.insertId, ...session });
  }
  
  console.log(`✅ ${sessions.length}개의 게임 세션 생성됨`);
  return sessions;
}

// 학습 에피소드 생성
async function createTrainingEpisodes(connection) {
  console.log('🧠 학습 에피소드 생성 중...');
  
  const episodes = [];
  const now = Date.now();
  
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
    
    const episode = {
      episodeNumber,
      totalReward: parseFloat(totalReward.toFixed(2)),
      averageReward: parseFloat(averageReward.toFixed(2)),
      winRate: parseFloat(winRate.toFixed(3)),
      gamesPlayed,
      loss: parseFloat(loss.toFixed(4)),
      notes: i % 5 === 0 ? `에피소드 ${episodeNumber} 완료 - 성능 개선됨` : null,
      createdAt: new Date(now - (50 - i) * 3600000), // 1시간씩 이전
    };
    
    const [result] = await connection.execute(
      `INSERT INTO training_episodes (episodeNumber, totalReward, averageReward, winRate, gamesPlayed, loss, notes, createdAt)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        episode.episodeNumber,
        episode.totalReward,
        episode.averageReward,
        episode.winRate,
        episode.gamesPlayed,
        episode.loss,
        episode.notes,
        episode.createdAt,
      ]
    );
    
    episodes.push({ id: result.insertId, ...episode });
  }
  
  console.log(`✅ ${episodes.length}개의 학습 에피소드 생성됨`);
  return episodes;
}

// 봇 설정 생성
async function createBotConfigs(connection) {
  console.log('🤖 봇 설정 생성 중...');
  
  const configs = [
    {
      name: '공격형 저글링 러시',
      strategy: 'Aggressive',
      buildOrder: JSON.stringify({ units: ['Drone', 'Drone', 'Overlord', 'Zergling', 'Zergling'] }),
      description: '초반 저글링 러시로 상대를 압박하는 공격형 전략',
      isActive: true,
    },
    {
      name: '방어형 뮤탈리스크',
      strategy: 'Defensive',
      buildOrder: JSON.stringify({ units: ['Drone', 'Overlord', 'Hatchery', 'Mutalisk'] }),
      description: '안정적인 경제 운영으로 뮤탈리스크 빌드를 완성하는 전략',
      isActive: false,
    },
    {
      name: '균형형 하이브',
      strategy: 'Balanced',
      buildOrder: JSON.stringify({ units: ['Drone', 'Overlord', 'Hatchery', 'Hydralisk', 'Ultralisk'] }),
      description: '경제와 군사력의 균형을 맞춘 중반 전략',
      isActive: false,
    },
    {
      name: '경제형 확장',
      strategy: 'Economic',
      buildOrder: JSON.stringify({ units: ['Drone', 'Drone', 'Hatchery', 'Hatchery'] }),
      description: '다중 해처리로 경제를 극대화하는 전략',
      isActive: false,
    },
    {
      name: '초반 러시 (6풀)',
      strategy: 'Rush',
      buildOrder: JSON.stringify({ units: ['Drone', 'Overlord', 'Spawning Pool', 'Zergling'] }),
      description: '6드론 풀로 초반 압박을 가하는 극공격형 전략',
      isActive: false,
    },
  ];
  
  const createdConfigs = [];
  
  for (const config of configs) {
    const [result] = await connection.execute(
      `INSERT INTO bot_configs (name, strategy, buildOrder, description, isActive, createdAt)
       VALUES (?, ?, ?, ?, ?, NOW())`,
      [config.name, config.strategy, config.buildOrder, config.description, config.isActive ? 1 : 0]
    );
    
    createdConfigs.push({ id: result.insertId, ...config });
  }
  
  console.log(`✅ ${createdConfigs.length}개의 봇 설정 생성됨`);
  return createdConfigs;
}

// AI Arena 경기 기록 생성
async function createArenaMatches(connection) {
  console.log('🏆 AI Arena 경기 기록 생성 중...');
  
  const matches = [];
  const now = Date.now();
  let elo = 1600;
  let wins = 0;
  let losses = 0;
  
  for (let i = 0; i < 30; i++) {
    const isWin = Math.random() > 0.45; // 55% 승률
    const eloChange = isWin ? randomInt(10, 30) : randomInt(-30, -10);
    elo += eloChange;
    
    if (isWin) wins++;
    else losses++;
    
    const match = {
      matchId: `match-${Date.now()}-${i}`,
      opponentName: `Bot-${randomInt(1000, 9999)}`,
      opponentRace: randomChoice(races),
      mapName: randomChoice(maps),
      result: isWin ? 'Win' : 'Loss',
      elo,
      createdAt: new Date(now - i * 86400000), // 1일씩 이전
    };
    
    const [result] = await connection.execute(
      `INSERT INTO arena_matches (matchId, opponentName, opponentRace, mapName, result, elo, createdAt)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [match.matchId, match.opponentName, match.opponentRace, match.mapName, match.result, match.elo, match.createdAt]
    );
    
    matches.push({ id: result.insertId, ...match });
  }
  
  console.log(`✅ ${matches.length}개의 Arena 경기 기록 생성됨 (최종 ELO: ${elo}, 승률: ${((wins / (wins + losses)) * 100).toFixed(1)}%)`);
  return matches;
}

// 메인 함수
async function main() {
  let connection;
  
  try {
    console.log('\n🚀 SC2 AI 대시보드 테스트 데이터 생성 시작\n');
    
    connection = await pool.getConnection();
    
    // 기존 데이터 삭제 (선택사항)
    const deleteExisting = process.argv.includes('--clean');
    if (deleteExisting) {
      console.log('🗑️  기존 데이터 삭제 중...');
      await connection.execute('DELETE FROM arena_matches');
      await connection.execute('DELETE FROM training_episodes');
      await connection.execute('DELETE FROM bot_configs');
      await connection.execute('DELETE FROM game_sessions');
      console.log('✅ 기존 데이터 삭제 완료\n');
    }
    
    // 데이터 생성
    const sessions = await createGameSessions(connection);
    const episodes = await createTrainingEpisodes(connection);
    const configs = await createBotConfigs(connection);
    const matches = await createArenaMatches(connection);
    
    console.log('\n✨ 모든 테스트 데이터 생성 완료!\n');
    console.log('📊 생성된 데이터 요약:');
    console.log(`   - 게임 세션: ${sessions.length}개`);
    console.log(`   - 학습 에피소드: ${episodes.length}개`);
    console.log(`   - 봇 설정: ${configs.length}개`);
    console.log(`   - Arena 경기: ${matches.length}개`);
    console.log('\n🌐 대시보드에서 확인하세요: https://sc2aidash-bncleqgg.manus.space\n');
    
  } catch (error) {
    console.error('❌ 오류 발생:', error);
    process.exit(1);
  } finally {
    if (connection) {
      await connection.release();
    }
    await pool.end();
  }
}

main();
