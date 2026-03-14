import sys
from pathlib import Path
import time
import json
import os

try:
    import win32com.client
except ImportError:
    win32com = None

def get_history_file():
    return Path(__file__).parent.parent / "history.json"

def save_history(path_str):
    """Save path to history.json"""
    try:
        p = Path(path_str).resolve()
        if p.is_file():
            p = p.parent
        
        history_file = get_history_file()
        history = []
        
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []
        
        # Add to top, remove duplicates
        str_p = str(p)
        if str_p in history:
            history.remove(str_p)
        history.insert(0, str_p)
        
        # Limit to 20
        history = history[:20]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
            
    except Exception:
        pass

def get_selected_files():
    """
    Returns a list of Path objects representing the selected files in the active Explorer window.
    If no selection or error, returns empty list.
    """
    if not win32com:
        return []

    try:
        shell = win32com.client.Dispatch("Shell.Application")
        windows = shell.Windows()
        pass
        
    except Exception:
        return []
    return []

def get_selection_from_explorer(anchor_path: str):
    """
    Finds the Explorer window containing 'anchor_path' and returns all selected items in that window.
    If anchor_path is a directory, it might be the folder itself or a file inside.
    Also saves the accessed folder to history.
    """
    
    # Save history
    save_history(anchor_path)

    if not win32com:
        return [Path(anchor_path)]

    # Initialize COM safely
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except: pass

    # Use abspath instead of resolve to prevent .lnk files from being dereferenced
    import os
    anchor = Path(os.path.abspath(anchor_path))
    # If anchor is a file, parent is the folder.
    # If anchor is a folder, it might be the folder open in Explorer OR a selected folder.
    
    selected_paths = []
    
    try:
        shell = win32com.client.Dispatch("Shell.Application")
        # Retry logic or robust loop
        windows = shell.Windows()
        for i in range(windows.Count):
            try:
                window = windows.Item(i)
                if not window: continue
                
                # window.LocationURL might be empty or fail
                doc = window.Document
                if not doc: continue
                
                folder = doc.Folder
                if not folder: continue
                
                folder_path = folder.Self.Path
                if not folder_path: continue
                
                folder_path_obj = Path(folder_path).resolve()
                folder_path_str = str(folder_path).lower().replace('/', '\\')
                
                # Check if this window is relevant
                # Match by path string to be robust
                anchor_parent_str = str(anchor.parent).lower().replace('/', '\\')
                anchor_str = str(anchor).lower().replace('/', '\\')
                
                is_match = False
                
                # Direct path match
                if anchor_parent_str == folder_path_str:
                    is_match = True
                elif anchor_str == folder_path_str:
                    is_match = True
                    
                # URL Match Fallback
                if not is_match:
                    try:
                        loc_url = window.LocationURL
                        if loc_url and loc_url.lower().startswith("file:///"):
                            from urllib.request import url2pathname
                            decoded_path = url2pathname(loc_url[8:])
                            decoded_path = decoded_path.replace('/', '\\').lower()
                            
                            # Check against anchor parent or anchor
                            # Decode might return c:\foo even if input was C:\Foo
                            if decoded_path == anchor_parent_str or decoded_path == anchor_str:
                                is_match = True
                    except: pass
                    
                if is_match:
                    # Found the window! Get selection.
                    items = doc.SelectedItems()
                    if items.Count > 0:
                        for i in range(items.Count):
                            item_path = items.Item(i).Path
                            selected_paths.append(Path(item_path))
                        return selected_paths
                    else:
                        # No selection? Maybe background click.
                        pass
            except Exception:
                continue
                
    except Exception:
        pass
        
    # Fallback: just return the anchor
    return [anchor]



def select_and_rename(path):
    """
    Selects the file in the *existing* Explorer window and triggers Rename (F2).
    Avoids opening a new window if possible.
    Special handling for Desktop to prevent new window opening.
    """
    try:
        path = Path(path).resolve()
        if not path.exists(): return

        # Check if we're on Desktop (user or public)
        user_desktop = Path(os.path.expanduser("~/Desktop")).resolve()
        public_desktop = Path(os.environ.get("PUBLIC", "C:\\Users\\Public")) / "Desktop"
        try:
            public_desktop = public_desktop.resolve()
        except:
            pass
        is_desktop = path.parent == user_desktop or path.parent == public_desktop
        
        # Fallback for systems without pywin32
        if not win32com:
            import subprocess
            subprocess.Popen(f'explorer /select,"{str(path)}"')
            return

        # Initialize COM (Critical for scripts running in separate processes)
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except: pass

        shell = win32com.client.Dispatch("Shell.Application")
        parent_path = str(path.parent).lower().replace('/', '\\')
        
        target_window = None
        
        # 1. Find the window displaying the folder
        try:
            windows = shell.Windows()
            for i in range(windows.Count):
                try:
                    window = windows.Item(i)
                    if not window: continue
                    
                    doc = window.Document
                    if not doc: continue
                    folder = doc.Folder
                    if not folder: continue
                    
                    win_path = folder.Self.Path
                    if not win_path: continue
                    
                    win_path_str = str(win_path).lower().replace('/', '\\')
                    
                    matched = False
                    if win_path_str == parent_path:
                        matched = True
                    else:
                        try:
                            loc_url = window.LocationURL
                            if loc_url and loc_url.lower().startswith("file:///"):
                                from urllib.request import url2pathname
                                decoded_path = url2pathname(loc_url[8:])
                                decoded_path = decoded_path.replace('/', '\\').lower()
                                if decoded_path == parent_path:
                                    matched = True
                        except: pass
                        
                    if matched:
                        target_window = window
                        break
                except Exception:
                    continue
        except Exception:
            pass
            
        def _send_f2_safe():
            """Send F2 key using ctypes to avoid NumLock toggle bug in SendKeys."""
            import ctypes
            user32 = ctypes.windll.user32
            VK_F2 = 0x71
            # Key Down
            user32.keybd_event(VK_F2, 0, 0, 0)
            # Key Up
            user32.keybd_event(VK_F2, 0, 2, 0)

        # 2. If found, select and F2
        if target_window:
            # Retry loop for locating the item (Explorer update lag)
            MAX_RETRIES = 5
            for attempt in range(MAX_RETRIES):
                try:
                    folder_item = target_window.Document.Folder.ParseName(path.name)
                except:
                    folder_item = None
                    
                if folder_item:
                    # Found it!
                    try:
                        # Select(item, flags): 1=Select, 4=Deselect others, 8=Ensure visible, 16=Focus
                        target_window.Document.SelectItem(folder_item, 1 | 4 | 8 | 16)
                        
                        # Wait for selection to apply
                        time.sleep(0.1)
                        
                        # Activate window
                        try:
                            import ctypes
                            hwnd = target_window.HWND
                            if hwnd:
                                ctypes.windll.user32.SetForegroundWindow(hwnd)
                                ctypes.windll.user32.SetFocus(hwnd)
                        except: pass
                        
                        time.sleep(0.1)
                        _send_f2_safe()
                        return # Success
                    except Exception as e:
                        print(f"Selection/Rename COM error: {e}")
                        
                # Not found yet, maybe refresh?
                if attempt < MAX_RETRIES - 1:
                    time.sleep(0.3)
                    try:
                        if attempt == 1: # On second failure, force refresh
                            target_window.Refresh()
                            time.sleep(0.5)
                    except: pass
            
            print(f"Failed to find item '{path.name}' after retries.")
            
        elif is_desktop:
            # Desktop special handling - use shell namespace approach
            try:
                # Get the desktop shell folder
                CSIDL_DESKTOP = 0
                shell_folder = shell.NameSpace(CSIDL_DESKTOP)
                if shell_folder:
                    folder_item = shell_folder.ParseName(path.name)
                    if folder_item:
                        # Try to select via desktop window (Progman)
                        time.sleep(0.2)
                        
                        # Focus desktop and send F2
                        try:
                            import ctypes
                            # Find and focus the desktop window
                            user32 = ctypes.windll.user32
                            progman = user32.FindWindowW("Progman", None)
                            if progman:
                                user32.SetForegroundWindow(progman)
                                time.sleep(0.1)
                                _send_f2_safe()
                        except:
                            pass
            except Exception as e:
                print(f"Desktop rename failed: {e}")
        else:
            # Window not found - don't open new window, just skip rename
            # User can manually rename if needed
            print(f"No Explorer window found for {path.parent}, skipping rename trigger")
            pass
    except Exception as e:
        print(f"select_and_rename failed: {e}")



