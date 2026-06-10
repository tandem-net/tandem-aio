import cmd
import json
import os
import socket
from pathlib import Path

class MyInteractiveCLI(cmd.Cmd):
    prompt = 'Tandem> '
    intro = "Welcome to Tandem! type help for commands."

    apps = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_all_apps()

    def load_all_apps(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        toml_folder = os.path.join(base_path, "toml")
        
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
    
    def do_deploy_app(self,line): #port 6767
        """Deploys an app to port 6767 Usage: deploy_app <app_name>"""
        app_name = line.strip()
        if not app_name:
            print("Error: Usage: deploy_app <app_name>")
            return

        app = self.get_app(app_name)
        if not app:
            print(f"Error: App '{app_name}' not found")
            return

        payload = json.dumps({
            "name": app.name,
            "language": app.language,
            "toml_path": app.toml_path,
        }).encode("utf-8")

        try:
            with socket.create_connection(("127.0.0.1", 6767), timeout=5) as connection:
                connection.sendall(payload + b"\n")
                response_body = connection.recv(4096).decode("utf-8")
        except OSError as exc:
            print(f"Error: Could not reach test server on port 6767: {exc}")
            return

        try:
            response = json.loads(response_body)
        except json.JSONDecodeError:
            print(f"Error: Test server returned an invalid response: {response_body}")
            return

        if response.get("status") != "ok":
            print(f"Error: Test server rejected deploy: {response.get('message', 'unknown error')}")
            return

        print(f"Deployed '{app.name}' to test server")
        
            
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
