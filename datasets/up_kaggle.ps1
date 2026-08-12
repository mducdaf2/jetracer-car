$ErrorActionPreference = "Stop"
$env:KAGGLE_CONFIG_DIR = "C:\Users\ADMIN\.kaggle"

$stagingDir = ".\upload_staging"

try {
    Write-Host "1/3. Dang chuan bi du lieu..." -ForegroundColor Green
    
    # Tao thu muc tam
    if (Test-Path $stagingDir) { Remove-Item -Path $stagingDir -Recurse -Force }
    New-Item -ItemType Directory -Path $stagingDir -Force | Out-Null

    # Copy 2 thu muc dataset va metadata vao thu muc tam
    Copy-Item -Path ".\lane_dataset", ".\sign_dataset" -Destination $stagingDir -Recurse -Force
    Copy-Item -Path ".\dataset-metadata.json" -Destination $stagingDir -Force

    Write-Host "2/3. Dang day version moi len Kaggle..." -ForegroundColor Green
    kaggle datasets version -p $stagingDir -m "Auto update dataset" --dir-mode zip

    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n=== CAP NHAT THANH CONG LEN KAGGLE! ===" -ForegroundColor Cyan
    }
}
catch {
    Write-Host "`n[LOI] Quá trình cập nhật thất bại:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}
finally {
    # Luon luon xoa thu muc tam sau khi xong
    if (Test-Path $stagingDir) {
        Remove-Item -Path $stagingDir -Recurse -Force
    }
}