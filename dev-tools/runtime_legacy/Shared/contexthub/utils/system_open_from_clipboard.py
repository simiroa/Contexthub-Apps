import os
import win32clipboard
from pathlib import Path

def open_path_from_clipboard():
    """
    Get path from clipboard and open it in Windows Explorer.
    Supports both file/folder copied from Explorer (CF_HDROP) 
    and path strings (CF_TEXT/CF_UNICODETEXT).
    """
    try:
        win32clipboard.OpenClipboard()
        try:
            target_path = None
            
            # 1. Try CF_HDROP (Files copied in Explorer)
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
                if data:
                    target_path = data[0] # Open first item
            
            # 2. Try Text (Path or URL string)
            elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                if text:
                    clean_text = text.strip().replace('"', '')
                    # Check for URL (Extended detection)
                    url_prefixes = ('http://', 'https://', 'www.', 'ftp://', 'file://')
                    if clean_text.lower().startswith(url_prefixes) or ('.' in clean_text and not os.path.sep in clean_text and not ' ' in clean_text):
                        import webbrowser
                        url = clean_text
                        if clean_text.lower().startswith('www.'):
                            url = 'http://' + clean_text
                        elif not any(clean_text.lower().startswith(p) for p in url_prefixes):
                            # Guessing it's a domain if it has a dot and no spaces/slashes
                            url = 'http://' + clean_text
                        
                        try:
                            webbrowser.open(url)
                            return f"Opened URL: {url}"
                        except Exception as web_e:
                            return f"Detected URL but failed to open: {web_e}"
                    
                    if os.path.exists(clean_text):
                        target_path = clean_text
            
            elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_TEXT):
                text = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
                if text:
                    try:
                        text_str = text.decode('utf-8').strip().replace('"', '')
                        # Check for URL (Extended detection)
                        url_prefixes = ('http://', 'https://', 'www.', 'ftp://', 'file://')
                        if text_str.lower().startswith(url_prefixes):
                            import webbrowser
                            url = text_str
                            if text_str.lower().startswith('www.'):
                                url = 'http://' + text_str
                            webbrowser.open(url)
                            return f"Opened URL: {url}"

                        if os.path.exists(text_str):
                            target_path = text_str
                    except:
                        pass
            
            if target_path:
                path = Path(target_path)
                # If it's a file, open its parent and select it
                if path.is_file():
                    os.system(f'explorer /select,"{path}"')
                    return f"Selected: {path.name}"
                elif path.is_dir():
                    os.startfile(str(path))
                    return f"Opened: {path.name}"
                else:
                     return "Path exists but is not a file or directory."
            else:
                return "Clipboard does not contain a valid file or path."
                    
        finally:
            win32clipboard.CloseClipboard()
            
    except Exception as e:
        return f"Failed to open path: {e}"

if __name__ == "__main__":
    result = open_path_from_clipboard()
    if result:
        print(result)
        # Optional: simpler error visibility for context menu users (if console stays open briefly)
        if "Failed" in result or "not contain" in result:
             import time
             # time.sleep(2) # Uncomment if debugging context menu

