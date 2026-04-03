# タスクスケジューラ設定スクリプト
# 管理者権限で実行: powershell -ExecutionPolicy Bypass -File scripts/setup_scheduler.ps1

$taskName = "AffiliateBlogAutoPost"
$projectDir = "F:\Claude Code\affiliate_site"
$pythonPath = (Get-Command python).Source
$scriptPath = "$projectDir\scripts\generate_article.py"

# 既存タスクがあれば削除
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# タスク設定
$action = New-ScheduledTaskAction `
    -Execute $pythonPath `
    -Argument "$scriptPath --news --auto" `
    -WorkingDirectory $projectDir

# 毎日9:00に実行（PC起動していなくても次回起動時に実行）
$trigger = New-ScheduledTaskTrigger -Daily -At "09:00"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# 環境変数（ANTHROPIC_API_KEY）を引き継ぐ
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "アフィリエイトブログ記事自動生成（毎日）"

Write-Host "タスク登録完了: $taskName"
Write-Host "毎日9:00に自動実行（PC未起動の場合は次回起動時）"
