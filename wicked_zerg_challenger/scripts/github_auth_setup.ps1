# GitHub 인증 설정 스크립트
# Windows Credential Manager를 통한 GitHub 토큰 인증

Write-Host "`n" -ForegroundColor Cyan
Write-Host "??????????????????????????????????????????????????????????????" -ForegroundColor Cyan
Write-Host "?     GitHub 인증 설정 (Personal Access Token)             ?" -ForegroundColor Cyan
Write-Host "??????????????????????????????????????????????????????????????" -ForegroundColor Cyan
Write-Host ""

# 1. 현재 자격증명 확인
Write-Host "1??  현재 GitHub 자격증명 확인 중..." -ForegroundColor Yellow
$gitConfig = git config --list | Select-String "github"
if ($gitConfig) {
    Write-Host "   현재 설정:" -ForegroundColor Green
    $gitConfig | ForEach-Object { Write-Host "   $_" }
} else {
    Write-Host "   설정된 자격증명 없음" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "2??  GitHub 인증 방법:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   옵션 A: Personal Access Token (권장)" -ForegroundColor Cyan
Write-Host "   1. https://github.com/settings/tokens 에서 토큰 생성" -ForegroundColor Gray
Write-Host "   2. Scopes: repo, workflow 선택" -ForegroundColor Gray
Write-Host "   3. 토큰 복사 및 아래에 입력" -ForegroundColor Gray
Write-Host ""
Write-Host "   옵션 B: SSH 키" -ForegroundColor Cyan
Write-Host "   1. https://github.com/settings/ssh 에서 SSH 키 추가" -ForegroundColor Gray
Write-Host "   2. ssh-keygen 으로 로컬 키 생성" -ForegroundColor Gray
Write-Host ""
Write-Host "   옵션 C: Git Credential Manager (자동)" -ForegroundColor Cyan
Write-Host "   1. https://github.com/git-ecosystem/git-credential-manager" -ForegroundColor Gray
Write-Host ""

Write-Host "? 현재 상태:" -ForegroundColor Yellow
Write-Host "   - GitHub 이메일: sun475300@naver.com (확인 필요)" -ForegroundColor Gray
Write-Host "   - Repository: https://github.com/sun475300-sudo/sc2AIagent.git" -ForegroundColor Gray
Write-Host "   - 오류: HTTP 403 (권한 없음)" -ForegroundColor Red
Write-Host ""

Write-Host "? 자동 설정 옵션:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   $ git config --global credential.helper wincred" -ForegroundColor Cyan
Write-Host "   위 명령으로 Windows Credential Manager 활성화" -ForegroundColor Gray
Write-Host ""

Write-Host "또는 수동으로 아래 명령 실행:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   1. GitHub 이메일 인증:" -ForegroundColor Cyan
Write-Host "   https://github.com/settings/emails" -ForegroundColor Green
Write-Host ""
Write-Host "   2. 토큰 생성:" -ForegroundColor Cyan
Write-Host "   https://github.com/settings/tokens/new" -ForegroundColor Green
Write-Host ""
Write-Host "   3. 로컬 저장소 원격 URL 업데이트:" -ForegroundColor Cyan
Write-Host "   git remote set-url origin https://<TOKEN>@github.com/sun475300-sudo/sc2AIagent.git" -ForegroundColor Green
Write-Host ""
Write-Host "   또는" -ForegroundColor Gray
Write-Host ""
Write-Host "   4. SSH 설정 (권장):" -ForegroundColor Cyan
Write-Host "   git remote set-url origin git@github.com:sun475300-sudo/sc2AIagent.git" -ForegroundColor Green
Write-Host ""
