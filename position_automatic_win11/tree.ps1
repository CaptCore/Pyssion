<#
.SYNOPSIS
  현재 디렉터리 트리 구조를 출력하는 스크립트
.PARAMETER Path
  구조를 출력할 시작 폴더 (기본: 현재 폴더)
.PARAMETER Depth
  재귀 깊이 제한 (기본: 제한 없음)
#>

param(
    [string]$Path = ".",
    [int]$Depth = [int]::MaxValue
)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
function Print-Tree {
    param(
        [string]$CurrentPath,
        [int]$Level,
        [int]$MaxDepth
    )
    if ($Level -gt $MaxDepth) { return }

    $items = Get-ChildItem -LiteralPath $CurrentPath | Sort-Object Name
    for ($i = 0; $i -lt $items.Count; $i++) {
        $item = $items[$i]
        $isLast = ($i -eq $items.Count - 1)
        $branch = if ($isLast) { "└── " } else { "├── " }
        $indent = "    " * $Level
        Write-Host "$indent$branch$item"
        if ($item.PSIsContainer) {
            Print-Tree -CurrentPath $item.FullName -Level ($Level + 1) -MaxDepth $MaxDepth
        }
    }
}

# 스크립트 시작
Print-Tree -CurrentPath $Path -Level 0 -MaxDepth $Depth
