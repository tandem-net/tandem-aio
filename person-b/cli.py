import cmd
import os
from pathlib import Path
class MyInteractiveCLI(cmd.Cmd):
    prompt = 'Tandem> '
    intro = """
     _____ ____  _      ____  _____ _     
/__ __Y  _ \/ \  /|/  _ \/  __// \__/|
  / \ | / \|| |\ ||| | \||  \  | |\/||
  | | | |-||| | \||| |_/||  /_ | |  ||
  \_/ \_/ \|\_/  \|\____/\____\\_/  \|
                                      
    """

    apps = []

    def __init__(self, *args, **kwargs):
        """initializes cli"""
        super().__init__(*args, **kwargs)
        self.load_all_apps()

    def load_all_apps(self):
        """loads all apps in toml folder into apps list"""
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
            app.add_app()
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
    
        
    
class App():
    def __init__(self, name, language):
        """Initalizes app object with name language and toml path"""
        self.name = name
        self.language = language
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.toml_path = os.path.join(base_path, "toml", f"{name}.toml")

    def is_valid(self):
        """Checks if the app already exists in toml directory"""
        toml_dir = os.path.dirname(self.toml_path)
        os.makedirs(toml_dir, exist_ok=True)
        
        if os.path.exists(self.toml_path):
            print(f"Error: App '{self.name}' already exists")
            return False
        
        return True
    
    def add_app(self):
        """Adds app in toml directory"""
        with open(self.toml_path, 'w') as f:
            f.write(f"[app]\nname = \"{self.name}\"\nlanguage = \"{self.language}\"\n")
    
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


#slop
if __name__ == '__main__':
    MyInteractiveCLI().cmdloop()
