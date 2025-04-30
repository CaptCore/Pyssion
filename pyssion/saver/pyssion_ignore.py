import fnmatch
from pathlib import Path
import hashlib

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

def get_local_etag(file_path: str) -> str:
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
