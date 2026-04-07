import os
import sys
import winreg
import subprocess
from pathlib import Path

from .logger import setup_logger
from .manifest_index import scan_manifests

logger = setup_logger("registry")


class RegistryManager:
    def __init__(self, config_or_root):
        if isinstance(config_or_root, Path):
            self.root_dir = config_or_root
        else:
            self.root_dir = getattr(config_or_root, "root_dir", Path.cwd())
        self.root_key = "Software\\Classes"
        self.app_key = "ContextHub"

        embedded = Path(__file__).parent.parent.parent / "tools" / "python" / "pythonw.exe"
        if embedded.exists():
            self.embedded_python = embedded
        else:
            self.embedded_python = Path(sys.executable)
            if self.embedded_python.name.lower() == "python.exe":
                possible_w = self.embedded_python.parent / "pythonw.exe"
                if possible_w.exists():
                    self.embedded_python = possible_w

        try:
            from .settings import load_settings
            settings = load_settings()
            custom = settings.get("PYTHON_PATH")

            candidate = None
            if custom and Path(custom).exists():
                candidate = Path(custom)
            else:
                candidate = Path(sys.executable)

            if candidate and candidate.name.lower() == "python.exe":
                possible_w = candidate.parent / "pythonw.exe"
                if possible_w.exists():
                    candidate = possible_w

            self.system_python = candidate
        except Exception:
            self.system_python = Path(sys.executable)

        self.menu_script = Path(__file__).parent / "menu.py"

    def _is_win11(self) -> bool:
        try:
            return sys.platform.startswith("win") and sys.getwindowsversion().build >= 22000
        except Exception:
            return False

    def _register_win11_main_menu(self, entries: list) -> None:
        """
        Register the Win11 main context menu via COM shell extension.
        """
        try:
            index_path = self.root_dir / "Runtimes" / "Shared" / "contexthub" / "context_menu_index.tsv"
            index_path.parent.mkdir(parents=True, exist_ok=True)

            lines = []
            for entry in entries:
                extensions = entry.context_extensions or []
                normalized = []
                for ext in extensions:
                    if ext == "*":
                        normalized.append(ext)
                    elif ext.startswith("."):
                        normalized.append(ext)
                    else:
                        normalized.append("." + ext)
                line = "\t".join(
                    [
                        entry.app_id,
                        entry.name.replace("\t", " ").replace("\n", " "),
                        "",
                        ",".join(sorted(set(normalized), key=str.lower)),
                    ]
                )
                lines.append(line)

            index_path.write_text("\n".join(lines), encoding="utf-8")

            script = self.root_dir / "tools" / "shell_extension" / "register_win11.ps1"
            if not script.exists():
                logger.warning("Win11 shell extension script not found.")
                return

            cmd = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-RootPath",
                str(self.root_dir),
                "-PythonPath",
                str(self.system_python or ""),
                "-IndexPath",
                str(index_path),
            ]
            subprocess.run(cmd, check=False, capture_output=True, text=True)
        except Exception as e:
            logger.warning(f"Win11 main menu registration failed: {e}")

    def _get_command(self, item_id: str, placeholder: str = "%1", env: str = "embedded") -> str:
        python_bin = self.embedded_python if env != "system" else self.system_python

        if isinstance(python_bin, Path):
            cmd = f'"{python_bin}" "{self.menu_script}" "{item_id}" "{placeholder}"'
        else:
            cmd = f'{python_bin} "{self.menu_script}" "{item_id}" "{placeholder}"'

        return cmd

    def register_all(self):
        """
        Registers items based on manifests under Apps_installed.
        """
        logger.info(f"Starting registration using {self.embedded_python} (System: {self.system_python})...")

        try:
            from .settings import load_settings
            settings = load_settings()
            if settings.get("WIN11_MAIN_MENU_ENABLED") and self._is_win11():
                win11_entries = [entry for entry in manifests.values() if entry.context_enabled]
                self._register_win11_main_menu(win11_entries)

            registry_map = {}
            item_applies_to = {}
            submenu = "ContextHub"

            manifests = scan_manifests(self.root_dir)
            for entry in manifests.values():
                if not entry.context_enabled:
                    continue

                targets = []
                extensions = entry.context_extensions
                if not extensions:
                    targets.append("*")
                else:
                    if "directory" in extensions or "folder" in extensions:
                        targets.append("Directory")
                        targets.append("Directory\\Background")
                    if "background" in extensions:
                        targets.append("Directory\\Background")

                    file_exts = [
                        ext
                        for ext in extensions
                        if ext not in {"directory", "folder", "background", "*"}
                    ]
                    if file_exts:
                        targets.append("*")
                        conditions = []
                        for ext in file_exts:
                            if not ext.startswith("."):
                                ext = "." + ext
                            conditions.append(f"System.FileExtension:={ext}")
                        if conditions:
                            item_applies_to[entry.app_id] = "(" + " OR ".join(conditions) + ")"

                for target in targets:
                    if target not in registry_map:
                        registry_map[target] = {}
                    if submenu not in registry_map[target]:
                        registry_map[target][submenu] = []
                    registry_map[target][submenu].append(entry)

            for target, submenus in registry_map.items():
                placeholder = "%V" if target == "Directory\\Background" else "%1"

                for submenu_name, items in submenus.items():
                    items = sorted(items, key=lambda it: (it.name, it.app_id))
                    self._register_submenu_group(target, submenu_name, items, placeholder, item_applies_to)

            self._bypass_selection_limit()
            logger.info("Registration complete.")

        except Exception as e:
            logger.error(f"Registration failed: {e}")
            raise

    def _register_submenu_group(self, reg_class: str, submenu_name: str, items: list, placeholder: str, item_applies_to: dict):
        display_submenu_name = submenu_name

        base_key_path = f"{self.root_key}\\{reg_class}\\shell"

        safe_key_name = "".join(c for c in submenu_name if c.isalnum() or c in ("_", "-"))

        from .settings import load_settings
        settings = load_settings()
        show_at_top = settings.get("MENU_POSITION_TOP", True)

        if not safe_key_name:
            safe_key_name = "ContextHub"

        parent_key_path = f"{base_key_path}\\{safe_key_name}"

        try:
            context_icon = Path(__file__).parent.parent.parent / "assets" / "icons" / "ContextHub.ico"
            if not context_icon.exists():
                context_icon = Path(__file__).parent.parent.parent / "assets" / "icons" / "ContextUp.ico"

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, parent_key_path) as key:
                winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, display_submenu_name)
                if context_icon.exists():
                    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, str(context_icon))
                winreg.SetValueEx(key, "SubCommands", 0, winreg.REG_SZ, "")
                winreg.SetValueEx(key, "ContextHubManaged", 0, winreg.REG_SZ, "true")
                try:
                    winreg.DeleteValue(key, "ExplorerCommandHandler")
                except FileNotFoundError:
                    pass
                except OSError:
                    pass

                if show_at_top:
                    winreg.SetValueEx(key, "Position", 0, winreg.REG_SZ, "Top")
                else:
                    try:
                        winreg.DeleteValue(key, "Position")
                    except Exception:
                        pass
        except Exception:
            pass

        parent_key_path = f"{parent_key_path}\\shell"
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, parent_key_path) as key:
                pass
        except Exception:
            pass

        for item in items:
            item_id = item.app_id
            item_name = item.name
            item_icon = ""

            order_prefix = "9999" if item_id == "copy_my_info" else "0000"
            item_key_path = f"{parent_key_path}\\{order_prefix}_{item_id}"

            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, item_key_path) as key:
                    winreg.SetValue(key, "", winreg.REG_SZ, item_name)
                    winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, item_name)
                    if item_icon:
                        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, item_icon)

                    if item_applies_to and item_id in item_applies_to and reg_class != "Directory\\Background":
                        winreg.SetValueEx(key, "AppliesTo", 0, winreg.REG_SZ, item_applies_to[item_id])

                    winreg.SetValueEx(key, "ContextHubManaged", 0, winreg.REG_SZ, "true")

                command_key_path = f"{item_key_path}\\command"
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, command_key_path) as key:
                    cmd = self._get_command(item_id, placeholder, "embedded")
                    winreg.SetValue(key, "", winreg.REG_SZ, cmd)

            except Exception as e:
                logger.warning(f"Failed to register item {item_id}: {e}")

    def unregister_all(self):
        """
        Removes the registry keys.
        Scans for keys with 'ContextHubManaged' marker, known legacy names,
        OR keys where the command executes our menu.py script.
        """
        logger.info("Unregistering...")

        self._unregister_win11_main_menu()

        targets = ["*", "Directory", "Directory\\Background"]
        legacy_keys = ["CreatorTools_v2", "ContextHub", " ContextHub"]

        menu_script_name = "menu.py"

        for target in targets:
            base_path = f"{self.root_key}\\{target}\\shell"
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base_path, 0, winreg.KEY_ALL_ACCESS) as key:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            full_subkey_path = f"{base_path}\\{subkey_name}"

                            should_delete = False

                            if subkey_name in legacy_keys:
                                should_delete = True

                            if not should_delete:
                                try:
                                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, full_subkey_path) as subkey:
                                        try:
                                            val, _ = winreg.QueryValueEx(subkey, "ContextHubManaged")
                                            if val == "true":
                                                should_delete = True
                                        except FileNotFoundError:
                                            pass
                                except Exception:
                                    pass

                            if not should_delete:
                                try:
                                    cmd_key_path = f"{full_subkey_path}\\command"
                                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cmd_key_path) as cmd_key:
                                        val, _ = winreg.QueryValueEx(cmd_key, "")
                                        if menu_script_name in val:
                                            should_delete = True
                                except Exception:
                                    try:
                                        shell_path = f"{full_subkey_path}\\shell"
                                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, shell_path) as shell_key:
                                            j = 0
                                            while True:
                                                try:
                                                    item_name = winreg.EnumKey(shell_key, j)
                                                    item_cmd_path = f"{shell_path}\\{item_name}\\command"
                                                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, item_cmd_path) as item_cmd_key:
                                                        val, _ = winreg.QueryValueEx(item_cmd_key, "")
                                                        if menu_script_name in val:
                                                            should_delete = True
                                                            break
                                                    j += 1
                                                except OSError:
                                                    break
                                    except Exception:
                                        pass

                            if should_delete:
                                self._delete_key_recursive(winreg.HKEY_CURRENT_USER, full_subkey_path)
                                i = 0
                            else:
                                i += 1
                        except OSError:
                            break
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.warning(f"Error scanning {base_path}: {e}")

        try:
            self._delete_key_recursive(winreg.HKEY_CURRENT_USER, "Software\\Classes\\ContextHub.CopyInfoMenu")
        except Exception:
            pass

        logger.info("Unregistration complete.")

    def _unregister_win11_main_menu(self) -> None:
        script = self.root_dir / "tools" / "shell_extension" / "unregister_win11.ps1"
        if not script.exists():
            return
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-RootPath",
                str(self.root_dir),
            ]
            subprocess.run(cmd, check=False, capture_output=True, text=True)
        except Exception as e:
            logger.warning(f"Win11 main menu unregister failed: {e}")

    def _bypass_selection_limit(self):
        """
        Sets MultipleInvokePromptMinimum to avoid context menu disappearance
        when selecting >15 files.
        """
        try:
            key_path = "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "MultipleInvokePromptMinimum", 0, winreg.REG_DWORD, 500)
                logger.info("Set MultipleInvokePromptMinimum to 500")
        except Exception as e:
            logger.warning(f"Failed to set MultipleInvokePromptMinimum: {e}")

    def _delete_key_recursive(self, root, key_path):
        try:
            with winreg.OpenKey(root, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
                while True:
                    try:
                        subkey = winreg.EnumKey(key, 0)
                        self._delete_key_recursive(root, f"{key_path}\\{subkey}")
                    except OSError:
                        break
            winreg.DeleteKey(root, key_path)
            logger.debug(f"Deleted {key_path}")
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug(f"Failed to delete {key_path}: {e}")
