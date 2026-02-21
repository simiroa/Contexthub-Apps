import os
from .ui import FinderApp

def open_finder(target_path=None, *args, **kwargs):
    if not target_path:
        target_path = os.getcwd()
    app = FinderApp(target_path=target_path)
    app.mainloop()
