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
temp_folder = os.path.join(base_path, "temp_pid")
path = Path(temp_folder)

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

            if not pickle_paths:
                print("Error: Please provide at least one pickle file path")
                return

            for p in pickle_paths:
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

    
        
    
class App():
    def __init__(self, name, language):
        self.name = name
        self.language = language
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.toml_path = os.path.join(base_path, "toml", f"{name}.toml")

    def is_valid(self):
        toml_dir = os.path.dirname(self.toml_path)
        os.makedirs(toml_dir, exist_ok=True)
        
        if os.path.exists(self.toml_path):
            print(f"Error: App '{self.name}' already exists")
            return False
        
        config = {
            "app": {
                "name": self.name,
                "language": self.language
            }
        }
        
        with open(self.toml_path, 'w') as f:
            import json
            f.write(f"[app]\nname = \"{self.name}\"\nlanguage = \"{self.language}\"\n")
        
        return True
    
    def list_app(self):
        """List all TOML files in the toml folder."""
        list_names = []
        toml_folder = os.path.dirname(self.toml_path)
        
        if not os.path.exists(toml_folder):
            return list_names
        
        folder = Path(toml_folder)
        for item in folder.iterdir():
            if item.name.endswith('.toml'):
                list_names.append(item.name)
        
        return list_names



if __name__ == '__main__':
    MyInteractiveCLI().cmdloop()
