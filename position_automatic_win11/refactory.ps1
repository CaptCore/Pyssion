param (
    [string]$LibraryDir = "lib",           # Directory for library source code
    [string]$ExampleDir = "examples",      # Directory for example/demo scripts
    [string]$ScriptDir = "scripts",        # Directory for utility or setup scripts
    [string]$TestDir = "tests"             # Directory for test files
)

# Create target directories if they do not exist
$dirsToCreate = @($LibraryDir, $ExampleDir, $ScriptDir, $TestDir)
foreach ($dir in $dirsToCreate) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }
}

# Move Python package directories (those containing __init__.py) to library directory
$topLevelDirs = Get-ChildItem -Directory
foreach ($d in $topLevelDirs) {
    if (Test-Path "$($d.FullName)\__init__.py") {
        Write-Host "📦 Moving library folder: $($d.Name)"
        Move-Item -Path $d.FullName -Destination "$LibraryDir\$($d.Name)" -Force
    }
}

# Move temporary, test, or archive-related folders/files to examples
$examplePatterns = @("tmp*", "*test*", "archive*")
foreach ($pattern in $examplePatterns) {
    Get-ChildItem -Path . -Recurse -Include $pattern -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            Move-Item $_.FullName -Destination $ExampleDir -Force
            Write-Host "🧪 Moving to examples: $($_.Name)"
        } catch {
            Write-Warning "⚠️ Failed to move: $($_.FullName)"
        }
    }
}

# Move shell scripts, Docker and Kubernetes YAMLs to scripts directory
Get-ChildItem -Path . -Recurse -Include *.sh,*.yml,docker-compose.* | ForEach-Object {
    try {
        Move-Item $_.FullName -Destination $ScriptDir -Force
        Write-Host "📜 Moving script file: $($_.Name)"
    } catch {
        Write-Warning "⚠️ Failed to move: $($_.FullName)"
    }
}

# Move test_*.py files to tests directory
Get-ChildItem -Recurse -Include "test_*.py" | ForEach-Object {
    Move-Item $_.FullName -Destination $TestDir -Force
    Write-Host "🧪 Moving test: $($_.Name)"
}

Write-Host "`n✅ Project structure refactoring completed:"
Write-Host "   - Library: $LibraryDir"
Write-Host "   - Examples: $ExampleDir"
Write-Host "   - Scripts: $ScriptDir"
Write-Host "   - Tests: $TestDir"
