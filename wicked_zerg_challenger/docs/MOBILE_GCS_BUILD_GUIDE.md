# Mobile GCS (Ground Control Station) 구축 가이드

**작성 일시**: 2026-01-14  
**상태**: ? **구축 가이드 완료**

---

## ? Mobile GCS 구축 방법

Mobile GCS를 만드는 방법은 크게 3가지가 있습니다:

### 1. **PWA (Progressive Web App)** ? 추천
- **장점**: 빠른 구현, 크로스 플랫폼 (Android/iOS), 앱스토어 배포 불필요
- **단점**: 네이티브 기능 제한 (카메라, 센서 등)
- **구현 시간**: 1-2시간
- **추천 대상**: 빠른 프로토타입, 실전 사용

### 2. **React Native**
- **장점**: JavaScript로 개발, 크로스 플랫폼
- **단점**: 초기 설정 복잡, 성능 오버헤드
- **구현 시간**: 1-2일
- **추천 대상**: 복잡한 UI, 네이티브 기능 필요

### 3. **네이티브 Android (Java/Kotlin)**
- **장점**: 최고 성능, 모든 Android 기능 사용 가능
- **단점**: Android 전용, 개발 시간 길음
- **구현 시간**: 3-5일
- **추천 대상**: 프로덕션 배포, Google Play Store 배포

---

## ? 방법 1: PWA (Progressive Web App) - 추천

기존 웹 대시보드를 PWA로 변환하여 모바일 앱처럼 사용할 수 있게 만듭니다.

### 단계 1: Manifest 파일 생성

`monitoring/static/manifest.json` 파일을 생성합니다:

```json
{
  "name": "SC2 Zerg Bot Monitor",
  "short_name": "SC2 Monitor",
  "description": "StarCraft II Zerg Bot Mobile Ground Control Station",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#16213e",
  "theme_color": "#16213e",
  "orientation": "portrait",
  "icons": [
    {
      "src": "/static/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "categories": ["games", "utilities"],
  "screenshots": [],
  "shortcuts": [
    {
      "name": "Game State",
      "short_name": "State",
      "description": "View current game state",
      "url": "/?tab=units",
      "icons": [{ "src": "/static/icon-192.png", "sizes": "192x192" }]
    }
  ]
}
```

### 단계 2: 아이콘 생성

아이콘 이미지가 필요합니다. 다음 중 하나를 선택:

**옵션 A: 온라인 아이콘 생성기 사용**
- https://www.pwabuilder.com/imageGenerator
- https://realfavicongenerator.net/

**옵션 B: Python 스크립트로 생성** (PIL/Pillow 필요)
```python
from PIL import Image, ImageDraw

# 192x192 아이콘
icon_192 = Image.new('RGB', (192, 192), color='#16213e')
draw = ImageDraw.Draw(icon_192)
draw.ellipse([20, 20, 172, 172], fill='#00ff00')
icon_192.save('monitoring/static/icon-192.png')

# 512x512 아이콘
icon_512 = Image.new('RGB', (512, 512), color='#16213e')
draw = ImageDraw.Draw(icon_512)
draw.ellipse([50, 50, 462, 462], fill='#00ff00')
icon_512.save('monitoring/static/icon-512.png')
```

### 단계 3: Service Worker 업데이트

`monitoring/static/sw.js`를 업데이트하여 오프라인 지원을 강화합니다.

### 단계 4: HTML에 PWA 메타 태그 추가

`monitoring/dashboard.html`에 이미 PWA 메타 태그가 포함되어 있습니다:
- ? `manifest.json` 링크
- ? Apple Touch Icon
- ? Theme Color
- ? Viewport 설정

### 단계 5: Service Worker 등록

`monitoring/dashboard.html`에 Service Worker 등록 코드를 추가합니다.

---

## ? 방법 2: React Native 앱

### 초기 설정

```bash
# React Native CLI 설치
npm install -g react-native-cli

# 프로젝트 생성
cd wicked_zerg_challenger
npx react-native init MobileGCS --template react-native-template-typescript

# 의존성 설치
cd MobileGCS
npm install axios @react-native-async-storage/async-storage
```

### 주요 컴포넌트

1. **API 클라이언트** (`src/api/client.ts`):
```typescript
import axios from 'axios';

const API_BASE = 'http://YOUR_SERVER_IP:8000';

export const fetchGameState = async () => {
  const response = await axios.get(`${API_BASE}/api/game-state`);
  return response.data;
};
```

2. **메인 화면** (`src/screens/Dashboard.tsx`):
```typescript
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { fetchGameState } from '../api/client';

export default function Dashboard() {
  const [gameState, setGameState] = useState(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      const state = await fetchGameState();
      setGameState(state);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <View style={styles.container}>
      <Text>Minerals: {gameState?.minerals || 0}</Text>
      <Text>Vespene: {gameState?.vespene || 0}</Text>
    </View>
  );
}
```

---

## ? 방법 3: 네이티브 Android 앱

### 초기 설정

```bash
# Android Studio 설치 필요
# 프로젝트 생성
cd wicked_zerg_challenger/monitoring
mkdir -p mobile_app_android
cd mobile_app_android

# Android 프로젝트 구조 생성
# (Android Studio에서 "New Project" > "Empty Activity" 선택)
```

### 주요 파일

1. **MainActivity.kt**:
```kotlin
package com.wickedzerg.mobilegcs

import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import kotlinx.coroutines.*
import okhttp3.*
import org.json.JSONObject

class MainActivity : AppCompatActivity() {
    private val client = OkHttpClient()
    private val apiBase = "http://YOUR_SERVER_IP:8000"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // 실시간 업데이트
        CoroutineScope(Dispatchers.Main).launch {
            while (true) {
                updateGameState()
                delay(1000)
            }
        }
    }

    private suspend fun updateGameState() = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("$apiBase/api/game-state")
            .build()
        
        client.newCall(request).execute().use { response ->
            val json = JSONObject(response.body?.string() ?: "{}")
            withContext(Dispatchers.Main) {
                findViewById<TextView>(R.id.minerals).text = 
                    "Minerals: ${json.optInt("minerals", 0)}"
            }
        }
    }
}
```

2. **activity_main.xml**:
```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp"
    android:background="#16213e">

    <TextView
        android:id="@+id/minerals"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Minerals: 0"
        android:textColor="#00ff00"
        android:textSize="24sp" />

    <TextView
        android:id="@+id/vespene"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Vespene: 0"
        android:textColor="#00ff00"
        android:textSize="24sp" />
</LinearLayout>
```

---

## ? PWA 완성 가이드 (상세)

### 1. Manifest.json 생성

`monitoring/static/manifest.json` 파일을 생성합니다.

### 2. 아이콘 생성

아이콘 이미지 파일이 필요합니다:
- `icon-192.png` (192x192)
- `icon-512.png` (512x512)

### 3. Service Worker 등록

`dashboard.html`에 Service Worker 등록 코드 추가.

### 4. HTTPS 설정 (프로덕션)

PWA는 HTTPS가 필요합니다:
- **로컬 개발**: `localhost`는 HTTPS 없이도 작동
- **프로덕션**: `ngrok` 또는 Let's Encrypt 사용

---

## ? 현재 시스템 상태

### ? 이미 구현된 기능
- 웹 대시보드 (`dashboard.html`)
- REST API 엔드포인트 (`/api/game-state`, `/api/combat-stats`, etc.)
- FastAPI 백엔드 (`dashboard_api.py`)
- Service Worker (`sw.js`)
- PWA 메타 태그 (일부)

### ? 추가로 필요한 것
- `manifest.json` 파일 생성
- 아이콘 이미지 생성
- Service Worker 등록 코드 추가
- 모바일 최적화 CSS 개선

---

## ? 추천 구현 순서

1. **PWA 완성** (1-2시간) - 가장 빠르고 실용적
2. **모바일 최적화** (CSS 개선)
3. **오프라인 지원 강화** (Service Worker 개선)
4. **앱스토어 배포** (선택 사항)

---

## ? 다음 단계

PWA를 완성하려면 다음 파일들을 생성/수정해야 합니다:
1. `monitoring/static/manifest.json` 생성
2. 아이콘 이미지 생성
3. `dashboard.html`에 Service Worker 등록 코드 추가

이 가이드를 따라 진행하시겠습니까?
