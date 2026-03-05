"""
Optimized Finder Scanner Module
Performance improvements:
- xxhash for 10x faster hashing (with MD5 fallback)
- os.scandir for faster directory traversal
- Cached file stats to avoid redundant I/O
- Generator patterns for memory efficiency
- Optimized thread pool usage
"""
import os
import time
import re
from pathlib import Path
from typing import List, Callable, Optional, Dict, Generator, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import FinderGroup

# Try to use xxhash (10x faster than MD5), fallback to hashlib
try:
    import xxhash
    def _hash_bytes(data: bytes) -> str:
        return xxhash.xxh64(data).hexdigest()
    HASH_TYPE = "xxhash"
except ImportError:
    import hashlib
    def _hash_bytes(data: bytes) -> str:
        return hashlib.md5(data).hexdigest()
    HASH_TYPE = "md5"


def _get_file_hash(path: Path, chunk_size: int = 65536) -> str:
    """Full file hash using xxhash (fast) or MD5 (fallback)."""
    if HASH_TYPE == "xxhash":
        hasher = xxhash.xxh64()
    else:
        import hashlib
        hasher = hashlib.md5()
    
    try:
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, IOError):
        return ""


def _get_partial_hash(path: Path, size: int, chunk_size: int = 8192) -> str:
    """
    Fast partial hash: first + last chunks only.
    Reuses cached size to avoid extra stat() calls.
    """
    try:
        with open(path, "rb") as f:
            if size < chunk_size * 2:
                # Small file - hash entire content
                return _hash_bytes(f.read())
            
            # Read first and last chunks
            chunk_start = f.read(chunk_size)
            f.seek(-chunk_size, 2)
            chunk_end = f.read(chunk_size)
            return _hash_bytes(chunk_start + chunk_end)
    except (OSError, IOError):
        return ""


def _fast_scandir(path: Path, excludes: set) -> Generator[Tuple[Path, int], None, None]:
    """
    Generator-based directory scanner using os.scandir (faster than os.walk).
    Yields (file_path, file_size) tuples to avoid redundant stat() calls.
    """
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    if entry.name not in excludes:
                        yield from _fast_scandir(Path(entry.path), excludes)
                elif entry.is_file(follow_symlinks=False):
                    try:
                        stat = entry.stat()
                        yield (Path(entry.path), stat.st_size)
                    except OSError:
                        pass
    except (OSError, PermissionError):
        pass


def scan_worker(
    target_path: Path, 
    mode: str = "simple", 
    criteria: Optional[Dict[str, bool]] = None, 
    status_callback: Optional[Callable[[str], None]] = None
) -> List[FinderGroup]:
    """
    Optimized scanning logic.
    mode: 'simple' or 'smart'
    criteria: dict with keys 'name', 'size', 'hash' (used in simple mode)
    """
    if criteria is None:
        criteria = {}
    
    if status_callback:
        status_callback("Indexing files...")
    
    path = Path(target_path)
    EXCLUDES = {'.git', 'node_modules', '__pycache__', '$RECYCLE.BIN', 
                'System Volume Information', '.svn', '.hg', 'venv', '.venv'}
    
    # Collect files with cached stats (avoids redundant stat calls)
    file_list = []  # List of (path, size) tuples
    count = 0
    
    for file_path, file_size in _fast_scandir(path, EXCLUDES):
        file_list.append((file_path, file_size))
        count += 1
        if count % 10000 == 0:
            if status_callback:
                status_callback(f"Indexing: {count} files...")
            time.sleep(0.001)  # Yield to UI
    
    total_files = len(file_list)
    if status_callback:
        status_callback(f"Analyzing {total_files} files...")
    
    groups_data: Dict[str, List[Path]] = {}
    
    if mode == "simple":
        use_name = criteria.get('name', True)
        use_size = criteria.get('size', True)
        use_hash = criteria.get('hash', False)
        
        # Group by cheap criteria (Name/Size) using cached stats
        pre_groups = defaultdict(list)
        
        for i, (f, size) in enumerate(file_list):
            if i % 5000 == 0:
                time.sleep(0.001)
            
            key_parts = []
            if use_name:
                key_parts.append(f.name)
            if use_size:
                key_parts.append(size)
            
            if not key_parts:
                key_parts.append(f.name)
            
            pre_groups[tuple(key_parts)].append((f, size))
        
        # Filter candidates with more than 1 file
        candidates = [(k, v) for k, v in pre_groups.items() if len(v) > 1]
        
        if use_hash:
            total_groups = len(candidates)
            processed_groups = 0
            
            def process_hash_group(items):
                """Process a group of potential duplicates with 2-phase hashing."""
                # Phase 1: Partial hash to quickly filter
                partial_map = defaultdict(list)
                for f, size in items:
                    ph = _get_partial_hash(f, size)
                    if ph:
                        partial_map[ph].append(f)
                
                # Phase 2: Full hash only for partial collisions
                final_map = defaultdict(list)
                for ph, files in partial_map.items():
                    if len(files) < 2:
                        continue
                    
                    for f in files:
                        fh = _get_file_hash(f)
                        if fh:
                            final_map[fh].append(f)
                
                return {h: files for h, files in final_map.items() if len(files) > 1}
            
            # Process in parallel with thread pool
            with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 4)) as executor:
                futures = {executor.submit(process_hash_group, v): k for k, v in candidates}
                
                for fut in as_completed(futures):
                    processed_groups += 1
                    if status_callback and processed_groups % 20 == 0:
                        status_callback(f"Hashing: {processed_groups}/{total_groups}")
                    
                    try:
                        result_map = fut.result()
                        for h, files in result_map.items():
                            groups_data[f"HASH: {h[:8]}..."] = files
                    except Exception:
                        pass
        else:
            # Return name/size matches directly
            for key, items in candidates:
                files = [f for f, _ in items]
                name_str = " | ".join(map(str, key))
                groups_data[f"Match: {name_str}"] = files
    
    elif mode == "smart":
        # Pattern for versioned files
        pattern = re.compile(r"^(.*?)[-_ .]*(?:v|V)?(\d+)[-_ .]*(\.[a-zA-Z0-9]+)$")
        raw_groups = defaultdict(list)
        
        for i, (f, size) in enumerate(file_list):
            if i % 2000 == 0:
                if status_callback:
                    status_callback(f"Pattern matching: {i}/{total_files}")
                time.sleep(0.001)
            
            try:
                match = pattern.match(f.name)
                if match:
                    base, ver, ext = match.groups()
                    if not base:
                        base = "root"
                    key = (str(f.parent), base.lower(), ext.lower())
                    raw_groups[key].append(f)
            except Exception:
                pass
        
        # Analyze groups
        for key, flist in raw_groups.items():
            if len(flist) < 2:
                continue
            
            # Heuristic: Many files = sequence, few = versions
            is_sequence = len(flist) > 12
            if not is_sequence:
                try:
                    match = pattern.match(flist[0].name)
                    if match and len(match.group(2)) >= 3:
                        is_sequence = True
                except Exception:
                    pass
            
            group_type = "SEQ" if is_sequence else "VER"
            base_name = f"{Path(key[0]).name}/{key[1]}"
            
            # Sort appropriately
            if is_sequence:
                flist.sort(key=lambda x: x.name)
            else:
                try:
                    flist.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                except Exception:
                    pass
            
            groups_data[f"{group_type}: {base_name}"] = flist
    
    # Convert to FinderGroup objects
    final_groups = [FinderGroup(name, flist) for name, flist in groups_data.items()]
    
    # Sort by count (descending) by default as requested
    final_groups.sort(key=lambda x: len(x.items), reverse=True)
    
    if status_callback:
        hash_info = f" ({HASH_TYPE})" if criteria.get('hash') else ""
        status_callback(f"Ready{hash_info}")
    
    return final_groups
