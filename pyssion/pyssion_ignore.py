import os
import fnmatch
from pathlib import Path

def load_ignore_patterns(directory: Path) -> list:
    ignore_file = directory / '.pyssionignore'
    patterns = []
    if ignore_file.exists():
        with ignore_file.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
    return patterns

def should_ignore(relative_path: Path, ignore_patterns: list) -> bool:
    rel_str = relative_path.as_posix()
    for pattern in ignore_patterns:
        if pattern.endswith('/'):
            base_pattern = pattern.rstrip('/')
            if rel_str == base_pattern or rel_str.startswith(pattern):
                return True
        else:
            if fnmatch.fnmatch(rel_str, pattern):
                return True
    return False

def upload_directory(directory_path, client, bucket, prefix=""):
    directory = Path(directory_path)
    
    ignore_file = directory / '.pyssionignore'
    ignore_patterns = []
    if ignore_file.exists():
        with ignore_file.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    ignore_patterns.append(line)
    
    for root, dirs, files in os.walk(directory):
            directory = Path(directory_path)
    ignore_patterns = load_ignore_patterns(directory)
    
    for root, dirs, files in os.walk(directory):
        relative_root = Path(root).relative_to(directory)
        
        for dir_name in dirs[:]:
            rel_dir = relative_root / dir_name
            if should_ignore(rel_dir, ignore_patterns):
                print(f"📂 skipped dirrectory: {rel_dir.as_posix()}")
                dirs.remove(dir_name)
        
        for file_name in files:
            rel_file = relative_root / file_name
            if should_ignore(rel_file, ignore_patterns):
                print(f"📤 skipped files: {rel_file.as_posix()}")
                continue
            
            object_name = f"{prefix}/{rel_file.as_posix()}".lstrip("/")
            full_path = Path(root) / file_name
            client.fput_object(bucket, object_name, str(full_path))
            print(f"📤 Upload: {object_name}")
