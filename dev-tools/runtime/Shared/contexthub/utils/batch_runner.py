import os
import time
import hashlib
import tempfile
from pathlib import Path

# Debug log file
DEBUG_LOG = Path(tempfile.gettempdir()) / "CreatorTools_Locks" / "debug.log"

def _log(msg):
    try:
        DEBUG_LOG.parent.mkdir(exist_ok=True)
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.time():.3f}: {msg}\n")
    except:
        pass

def collect_batch_context(item_id: str, target_path: str, timeout: float = 1.5) -> list[Path] | None:
    """
    Coordinates multiple processes launched by Windows Context Menu into a single batch.
    Uses dynamic waiting - keeps waiting while new files are still being added.
    
    Returns a list of Paths if this process is the 'leader'.
    Returns None if this process is a 'follower' (should exit).
    """
    try:
        target = Path(target_path).resolve()
        parent = target.parent
        
        _log(f"START: {target.name} for {item_id}")
        
        # Unique key for this batch operation
        key_str = f"{item_id}_{parent}".encode('utf-8')
        key = hashlib.md5(key_str).hexdigest()
        
        lock_dir = Path(tempfile.gettempdir()) / "CreatorTools_Locks"
        lock_dir.mkdir(exist_ok=True)
        
        lock_file = lock_dir / f"{key}.txt"
        
        # 1. Register myself
        start_time = time.time()
        registered = False
        while time.time() - start_time < 0.5:
            try:
                with open(lock_file, "a", encoding="utf-8") as f:
                    f.write(f"{target}\n")
                registered = True
                _log(f"REGISTERED: {target.name}")
                break
            except PermissionError:
                time.sleep(0.01)
            except Exception:
                time.sleep(0.01)
                
        if not registered:
            _log(f"FAILED TO REGISTER: {target.name}")
            return [target]
            
        # 2. Dynamic wait - keep waiting as long as new files are appearing
        # stable_threshold: If no new files for this long, we assume we have them all.
        # hard_max: Physical safety limit to prevent infinite loops.
        _log(f"WAITING (dynamic stabilization)...")
        
        last_count = 0
        last_change_time = time.time()
        check_interval = 0.05
        stable_threshold = 0.2 
        hard_max = max(5.0, timeout) # Allow up to 5s or requested timeout for massive sets
        
        wait_start = time.time()
        while time.time() - wait_start < hard_max:
            try:
                with open(lock_file, "r", encoding="utf-8") as f:
                    current_count = len([l for l in f.readlines() if l.strip()])
                
                if current_count > last_count:
                    _log(f"New files detected: {last_count} -> {current_count}")
                    last_count = current_count
                    last_change_time = time.time()
                else:
                    # Proceed if no change for stable_threshold
                    if time.time() - last_change_time >= stable_threshold:
                        _log(f"Stable at {current_count} files, proceeding...")
                        break
            except:
                pass
            
            time.sleep(check_interval)
        
        # 3. Read and Determine Leader
        try:
            # Final tiny grace
            time.sleep(0.05)
            
            if not lock_file.exists():
                _log(f"FOLLOWER (file gone): {target.name}")
                return None
                
            with open(lock_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            _log(f"READ {len(lines)} entries")
            
            paths = sorted(list(set([Path(p).resolve() for p in lines])))
            
            if not paths:
                _log(f"NO PATHS")
                return None
                
            if target == paths[0]:
                _log(f"LEADER: {target.name} with {len(paths)} files")
                time.sleep(0.1) # Let others finish reading
                try:
                    lock_file.unlink()
                except:
                    pass
                return paths
            else:
                _log(f"FOLLOWER: {target.name} (leader is {paths[0].name})")
                return None
                
        except Exception as e:
            _log(f"ERROR reading: {e}")
            return [target]
            
    except Exception as e:
        _log(f"EXCEPTION: {e}")
        print(f"Batch runner error: {e}")
        return [Path(target_path)]
