from pathlib import Path
import os
import ctypes
from ctypes import wintypes

# SHFileOperation constants
FO_MOVE = 0x0001
FO_COPY = 0x0002
FO_DELETE = 0x0003
FO_RENAME = 0x0004

FOF_SILENT = 0x0004
FOF_NOCONFIRMATION = 0x0010
FOF_ALLOWUNDO = 0x0040
FOF_NOCONFIRMMKDIR = 0x0200
FOF_NOERRORUI = 0x0400
FOF_WANTMAPPINGHANDLE = 0x0020

class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", wintypes.WORD),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", wintypes.LPVOID),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]

def _shell_op(op, src_path, dst_path=None, flags=FOF_ALLOWUNDO):
    """Internal helper to execute SHFileOperationW."""
    # Paths must be double-null terminated
    src = str(Path(src_path).absolute()) + "\0\0"
    dst = (str(Path(dst_path).absolute()) + "\0\0") if dst_path else None

    # SHFILEOPSTRUCTW instance
    fileop = SHFILEOPSTRUCTW()
    fileop.hwnd = None
    fileop.wFunc = op
    fileop.pFrom = src
    fileop.pTo = dst
    fileop.fFlags = flags

    # Use shell32.SHFileOperationW
    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
    
    # 0 means success, but check for aborption
    if result == 0 and not fileop.fAnyOperationsAborted:
        return True
    return False

def shell_move(src, dst):
    """Move file/folder using Windows Shell API (supports UAC)."""
    return _shell_op(FO_MOVE, src, dst)

def shell_rename(src, dst):
    """Rename file/folder using Windows Shell API (supports UAC)."""
    return _shell_op(FO_RENAME, src, dst)

def get_safe_path(path: Path, max_attempts: int = 999) -> Path:
    """
    Return a non-conflicting path by appending _01, _02, ... before the suffix.
    Preserves the original stem/suffix for readability.
    """
    path = Path(path)
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix

    for idx in range(1, max_attempts + 1):
        candidate = path.with_name(f"{stem}_{idx:02d}{suffix}")
        if not candidate.exists():
            return candidate

    # Fallback: timestamp-based name if all attempts exhausted
    return path.with_name(f"{stem}_safe{suffix}")
