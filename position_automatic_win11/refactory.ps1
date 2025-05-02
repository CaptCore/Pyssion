# PowerShell 스크립트: refactor-pyssion.ps1

# 이동 대상 폴더 설정
$libDir = "pyssion_lib"
$exampleDir = "examples"
$scriptDir = "scripts"
$testDir = "tests"

# 새 폴더 생성
New-Item -ItemType Directory -Path $libDir -Force
New-Item -ItemType Directory -Path $exampleDir -Force
New-Item -ItemType Directory -Path $scriptDir -Force
New-Item -ItemType Directory -Path $testDir -Force

# Pyssion 라이브러리 코드 이동
Move-Item -Path "pyssion" -Destination "$libDir/pyssion" -Force

# 테스트 / tmp 코드 분리
$exampleFiles = @("tmp.py", "tmp2.py", "tmp3.py", "tmp4.py", "archiveCode\test")
foreach ($file in $exampleFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination $exampleDir -Force
    }
}

# 테스트 환경 분리
if (Test-Path "archiveCode\runner_container") {
    Move-Item -Path "archiveCode\runner_container" -Destination $scriptDir -Force
}
if (Test-Path "archiveCode\minio") {
    Move-Item -Path "archiveCode\minio" -Destination "$libDir/pyssion/storage" -Force
}

# .egg-info, .cache 등 제거 (원하면 주석 해제)
# Remove-Item -Recurse -Force "pyssion.egg-info"
# Remove-Item -Force ".pyssioncache"

# 리포트
Write-Host "✅ 리팩토링 완료"
Write-Host "📂 라이브러리: $libDir"
Write-Host "📂 예제 코드: $exampleDir"
Write-Host "📂 유틸 스크립트: $scriptDir"
