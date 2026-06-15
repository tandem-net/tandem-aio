import cmd
import json
import os
import socket
from pathlib import Path
import random
import shutil
import requests

base_path = os.path.dirname(os.path.abspath(__file__))
toml_folder = os.path.join(base_path, "toml")
pickles_root = os.path.join(base_path, "pickles")
temp_folder = os.path.join(base_path, "temp_pid")
path = Path(temp_folder)

class App():
    def __init__(self, name, language):
        self.name = name
        self.language = language
        base_path_local = os.path.dirname(os.path.abspath(__file__))
        self.toml_path = os.path.join(base_path_local, "toml", f"{name}.toml")

        # per-app pickles folder
        self.pickles_dir = os.path.join(base_path_local, "pickles", name)

    def is_valid(self):
        toml_dir = os.path.dirname(self.toml_path)
        os.makedirs(toml_dir, exist_ok=True)
        os.makedirs(self.pickles_dir, exist_ok=True)
        
        if os.path.exists(self.toml_path):
            print(f"Error: App '{self.name}' already exists")
            return False
        
        with open(self.toml_path, 'w') as f:
            f.write(f"[app]\nname = \"{self.name}\"\nlanguage = \"{self.language}\"\n")
        
        return True

    def list_app(self):
        """List all TOML files in the toml folder."""
        list_names = []
        toml_folder_local = os.path.dirname(self.toml_path)
        
        if not os.path.exists(toml_folder_local):
            return list_names
        
        folder = Path(toml_folder_local)
        for item in folder.iterdir():
            if item.name.endswith('.toml'):
                list_names.append(item.name)
        
        return list_names


class MyInteractiveCLI(cmd.Cmd):
    prompt = 'Tandem $ '
    intro = "Welcome to Tandem! type help for commands."

    apps = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_all_apps()

    def load_all_apps(self):
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)
        
        for item in path.iterdir():
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()       # Deletes files and links inside
                elif item.is_dir():
                    shutil.rmtree(item)  # Deletes subfolders inside
            except Exception as e:
                print(f'Could not delete {item}. Error: {e}')
        if not os.path.exists(toml_folder):
            return
        
        for filename in os.listdir(toml_folder):
            if filename.endswith('.toml'):
                toml_path = os.path.join(toml_folder, filename)
                name = None
                language = None
                
                with open(toml_path, 'r') as f:
                    for line in f:
                        if line.startswith('name = '):
                            name = line.split('"')[1]
                        elif line.startswith('language = '):
                            language = line.split('"')[1]
                
                if name and language:
                    app = App(name, language)
                    try:
                        os.makedirs(app.pickles_dir, exist_ok=True)
                    except Exception:
                        pass
                    self.apps.append(app)

    def do_clear(self, line):
        """Clears the screen."""
        print("\033[H\033[2J", end="")

    def do_exit(self, line):
        """Exits the application."""
        print("au revoir")
        return True  
    
    def do_add_app(self, line):
        """Add an app. Usage: add_app <app_name> <app_language>"""
        if not line:
            print("Error: Please provide an app name and language")
            return
        
        parts = line.split()
        if len(parts) < 2:
            print("Error: Usage: add_app <app_name> <app_language>")
            return
        
        app_name = parts[0]
        app_language = parts[1]
        
        app = App(app_name, app_language)
        if app.is_valid():
            self.apps.append(app)
            print(f"App '{app_name}' added with language '{app_language}'")
            print(f"Pickle folder created: {app.pickles_dir}")

    def do_list(self, line):
        """List all added apps."""
        if not self.apps:
            print("No apps added yet.")
            return
        
        print("Apps:")
        for app in self.apps:
            print(f"  - {app.name} ({app.language})")
    
    def do_remove_app(self,line):
        """Removes an app Usage: remove_app <app_name>"""
        app_name = line.strip()
        if not app_name:
            print("Error: Usage: remove_app <app_name>")
            return

        for i, app in enumerate(self.apps):
            if app.name == app_name:
                try:
                    if os.path.exists(app.toml_path):
                        os.remove(app.toml_path)
                except Exception as e:
                    print(f"Warning: could not remove toml file: {e}")

                del self.apps[i]
                print(f"App '{app_name}' removed")
                return

        print(f"Error: App '{app_name}' not found")
    
    def do_deploy_app(self, line): #port 6767
        """Deploys an app to port 6767 Usage: deploy_app <app_name>"""
        
        app_name = line.strip()

        if not app_name:
            print("Error: Usage: deploy_app <app_name>")
            return

        for i, app in enumerate(self.apps):
            if app.name == app_name:
                try:
                    file_name = f'{app_name}.toml'
                    if not os.path.exists(app.toml_path):
                        print(f"Error: toml file not found at {app.toml_path}")
                        return

                    url = "http://127.0.0.1:6767/deploy/"

                    with open(app.toml_path, 'rb') as file:
                        files = {'toml_file': (file_name, file, 'text/plain')}
                        resp = requests.post(url, files=files, timeout=5)

                    print("Status:", resp.status_code)
                    print(resp.text)
                except Exception as e:
                    print(f"Error: could not send toml file: {e}")

                
                return

        print(f"Error: App '{app_name}' not found")
    
    def do_start_app(self, line):
        """Start an app. Usage: start_app <app_name> [pickle_path1 ...]"""

        parts = line.split()
        if not parts:
            print("Error: Usage: start_app <app_name> [pickle_path1 ...]")
            return

        app_name = parts[0]
        pickle_paths = parts[1:]

        app = self.get_app(app_name)
        if not app:
            print(f"Error: App '{app_name}' not found")
            return

        if not os.path.exists(app.toml_path):
            print(f"Error: toml file not found at {app.toml_path}")
            return

        url = "http://127.0.0.1:6767/start/"

        file_objs = []
        files = []
        try:
            # attach toml file
            toml_f = open(app.toml_path, 'rb')
            file_objs.append(toml_f)
            files.append(('toml_file', (os.path.basename(app.toml_path), toml_f, 'text/plain')))

            # If no explicit pickles given, use the app pickles folder
            if not pickle_paths:
                default_dir = getattr(app, 'pickles', None)
                if default_dir and os.path.isdir(default_dir):
                    entries = [os.path.join(default_dir, x) for x in os.listdir(default_dir)]
                    pickle_paths = [p for p in entries if os.path.isfile(p)]

            # Allow directories passed explicitly: expand them
            expanded = []
            for p in pickle_paths:
                if os.path.isdir(p):
                    for fname in os.listdir(p):
                        fp = os.path.join(p, fname)
                        if os.path.isfile(fp):
                            expanded.append(fp)
                else:
                    expanded.append(p)

            for p in expanded:
                if not os.path.exists(p):
                    print(f"Warning: pickle file not found: {p}")
                    continue

                f = open(p, 'rb')
                file_objs.append(f)
                files.append(('pickle_files', (os.path.basename(p), f, 'application/octet-stream')))

            if len(files) <= 1:
                print("Error: No valid pickle files to send")
                return

            resp = requests.post(url, files=files, timeout=10)

            print("Status:", resp.status_code)
            try:
                print(resp.text)
            except Exception:
                print('<no text response>')

        except Exception as e:
            print(f"Error: could not send start request: {e}")
        finally:
            for f in file_objs:
                try:
                    f.close()
                except Exception:
                    pass
    def _update_toml_field(self, toml_path: str, table: str, key: str, value: str):
        """
        Update or add a key under a TOML table.
        If the table doesn't exist it will be appended. If the key exists it's
        replaced.
        """
        if not os.path.exists(toml_path):
            print(f"Error: TOML file not found: {toml_path}")
            return False

        with open(toml_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        table_line = f'[{table}]\n'
        in_table = False
        table_start = None
        table_end = None

        for i, ln in enumerate(lines):
            if ln.strip().startswith('[') and ln.strip().endswith(']'):
                if in_table:
                    table_end = i
                    break
                if ln == table_line:
                    in_table = True
                    table_start = i

        if in_table and table_start is not None:
            if table_end is None:
                table_end = len(lines)

            # search for key
            key_prefix = key + ' = '
            replaced = False
            for i in range(table_start + 1, table_end):
                if lines[i].strip().startswith(key_prefix):
                    lines[i] = f'{key} = "{value}"\n'
                    replaced = True
                    break

            if not replaced:
                # insert before table_end
                lines.insert(table_end, f'{key} = "{value}"\n')
        else:
            # append new table
            if not lines or not lines[-1].endswith('\n'):
                lines.append('\n')
            lines.append(table_line)
            lines.append(f'{key} = "{value}"\n')

        with open(toml_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return True

    def do_set_run(self, line):
        """Set the run command for an app. Usage: set_run <app_name> <run command>"""
        parts = line.split(maxsplit=1)
        if len(parts) < 2:
            print('Usage: set_run <app_name> <run command>')
            return

        app_name, cmd = parts[0], parts[1]
        app = self.get_app(app_name)
        if not app:
            print(f"Error: App '{app_name}' not found")
            return

        ok = self._update_toml_field(app.toml_path, 'tandem', 'run', cmd)
        if ok:
            print(f"Set run command for '{app_name}': {cmd}")

    def do_set_install(self, line):
        """Set the install command for an app. Usage: set_install <app_name> <install command>"""
        parts = line.split(maxsplit=1)
        if len(parts) < 2:
            print('Usage: set_install <app_name> <install command>')
            return

        app_name, cmd = parts[0], parts[1]
        app = self.get_app(app_name)
        if not app:
            print(f"Error: App '{app_name}' not found")
            return

        ok = self._update_toml_field(app.toml_path, 'tandem', 'install', cmd)
        if ok:
            print(f"Set install command for '{app_name}': {cmd}")

    def do_set_script(self, line):
        """Reference an install/run script. Usage: set_script <app_name> <run|install> <script_path>"""
        parts = line.split(maxsplit=2)
        if len(parts) < 3:
            print('Usage: set_script <app_name> <run|install> <script_path>')
            return

        app_name, which, path_arg = parts[0], parts[1], parts[2]
        if which not in ('run', 'install'):
            print("Second arg must be 'run' or 'install'")
            return

        key = f'{which}_script'
        app = self.get_app(app_name)
        if not app:
            print(f"Error: App '{app_name}' not found")
            return

        ok = self._update_toml_field(app.toml_path, 'tandem', key, path_arg)
        if ok:
            print(f"Set {key} for '{app_name}': {path_arg}")

    def do_show_config(self, line):
        """Show parsed TOML fields for an app. Usage: show_config <app_name>"""
        app_name = line.strip()
        if not app_name:
            print('Usage: show_config <app_name>')
            return

        app = self.get_app(app_name)
        if not app:
            print(f"Error: App '{app_name}' not found")
            return

        if not os.path.exists(app.toml_path):
            print('TOML file missing')
            return

        with open(app.toml_path, 'r', encoding='utf-8') as f:
            print(f.read())

    def do_help(self, line):
        """Show minimal help listing: $ command ..."""
        commands = [
            'add_app <app_name> <app_language>',
            'remove_app <app_name>',
            'list',
            'deploy_app <app_name>',
            'start_app <app_name> [pickle_path1 ...]',
            'set_run <app_name> <run command>',
            'set_install <app_name> <install command>',
            'set_script <app_name> <run|install> <script_path>',
            'show_config <app_name>',
            'clear',
            'exit'
        ]
        for c in commands:
            print(f"$ {c}")
        
            
    def validate(self,app_name):
        for app in self.apps:
            if app.name == app_name:
                return True
            
        return False

    def get_app(self, app_name):
        for app in self.apps:
            if app.name == app_name:
                return app

        return None
if __name__ == '__main__':
    MyInteractiveCLI().cmdloop()
