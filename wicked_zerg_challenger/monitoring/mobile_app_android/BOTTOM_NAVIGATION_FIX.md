# BottomNavigationView 오류 해결

**오류**: `Maximum number of items supported by BottomNavigationView is 5`

**작성일**: 2026-01-15

---

## 🔍 오류 분석

### 발생 원인

`BottomNavigationView`는 Material Design 가이드라인에 따라 최대 5개의 아이템만 지원합니다.

**문제**:
- 메뉴에 6개의 아이템이 있었음:
  1. Home
  2. Monitor
  3. Battles
  4. Training
  5. Bot Config
  6. AI Arena

---

## ✅ 해결 방법

### 방법 1: 메뉴 아이템 제거 (적용됨) ⭐

**변경 사항**:
- `nav_bot_config` 아이템을 Bottom Navigation 메뉴에서 제거
- `nav_graph.xml`에는 유지 (프로그래밍 방식으로 접근 가능)

**수정된 메뉴** (5개):
1. Home
2. Monitor
3. Battles
4. Training
5. AI Arena

**Bot Config 접근 방법**:
- HomeFragment에서 버튼으로 접근
- 또는 프로그래밍 방식으로 네비게이션

---

### 방법 2: Navigation Rail 사용 (선택사항)

더 많은 아이템이 필요하다면 `NavigationRailView`를 사용할 수 있습니다:

```xml
<com.google.android.material.navigationrail.NavigationRailView
    android:id="@+id/navigation_rail"
    android:layout_width="wrap_content"
    android:layout_height="match_parent"
    app:menu="@menu/bottom_navigation_menu" />
```

**장점**: 5개 이상의 아이템 지원  
**단점**: 화면 공간을 더 많이 사용

---

## 📝 수정된 파일

### `bottom_navigation_menu.xml`

**변경 전**: 6개 아이템  
**변경 후**: 5개 아이템 (Bot Config 제거)

**제거된 아이템**:
```xml
<item
    android:id="@+id/nav_bot_config"
    android:icon="@android:drawable/ic_menu_preferences"
    android:title="Bot Config" />
```

---

## 🔄 Bot Config 접근 방법

### 옵션 1: HomeFragment에서 접근

`HomeFragment.kt`에 버튼을 추가하여 Bot Config로 네비게이션:

```kotlin
// HomeFragment.kt
val botConfigButton = view.findViewById<Button>(R.id.botConfigButton)
botConfigButton.setOnClickListener {
    findNavController().navigate(R.id.nav_bot_config)
}
```

### 옵션 2: 프로그래밍 방식 네비게이션

어떤 Fragment에서든:

```kotlin
findNavController().navigate(R.id.nav_bot_config)
```

---

## ✅ 확인 사항

### 메뉴 아이템 수 확인

```xml
<!-- 현재: 5개 아이템 ✅ -->
<menu>
    <item id="nav_home" />
    <item id="nav_monitor" />
    <item id="nav_battles" />
    <item id="nav_training" />
    <item id="nav_arena" />
</menu>
```

### nav_graph.xml 확인

`nav_graph.xml`에는 모든 Fragment가 유지되어 있습니다:
- ✅ `nav_home`
- ✅ `nav_monitor`
- ✅ `nav_battles`
- ✅ `nav_training`
- ✅ `nav_bot_config` (메뉴에서 제거되었지만 네비게이션 그래프에는 유지)
- ✅ `nav_arena`

---

## 🚀 다음 단계

1. **앱 재빌드 및 실행**
   ```powershell
   .\gradlew.bat assembleDebug
   ```

2. **Bot Config 접근 방법 구현** (선택사항)
   - HomeFragment에 버튼 추가
   - 또는 다른 Fragment에서 접근 가능하도록 구현

---

## 📚 참고 자료

- [Material Design - Bottom Navigation](https://material.io/components/bottom-navigation)
- [Navigation Rail](https://material.io/components/navigation-rail)
- Android Navigation Component 문서

---

**마지막 업데이트**: 2026-01-15  
**상태**: ✅ 수정 완료
