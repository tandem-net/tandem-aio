""" """

import base64
import cmd
import os
import shutil
import time
from pathlib import Path

import cloudpickle
import requests

SERVER_URL = os.environ.get("TANDEM_SERVER_URL", "http://127.0.0.1:6767").rstrip("/")
API_KEY_ENV_VAR = "TANDEM_API_KEY"
base_path = os.path.dirname(os.path.abspath(__file__))
pickles_root = os.path.join(base_path, "pickles")
temp_folder = os.path.join(base_path, "temp_pid")
path = Path(temp_folder)


def auth_headers(extra_headers: dict | None = None) -> dict[str, str]:
    api_key = (os.environ.get(API_KEY_ENV_VAR) or "").strip()
    if not api_key:
        raise RuntimeError(f"Missing {API_KEY_ENV_VAR} environment variable")

    headers = dict(extra_headers or {})
    headers["X-API-Key"] = api_key
    return headers


class App:
    def __init__(self, name, language):
        self.name = name
        self.language = language
        base_path_local = os.path.dirname(os.path.abspath(__file__))
        self.toml_path = os.path.join(base_path_local, f"{name}.toml")

        # per-app pickles folder
        self.pickles_dir = os.path.join(base_path_local, "pickles", name)

    def is_valid(self):
        os.makedirs(self.pickles_dir, exist_ok=True)

        if os.path.exists(self.toml_path):
            print(f"Error: App '{self.name}' already exists")
            return False

        with open(self.toml_path, "w") as f:
            f.write(f'[app]\nname = "{self.name}"\nlanguage = "{self.language}"\n')

        return True

    def list_app(self):
        """List all TOML files in the toml folder."""
        list_names = []
        root_folder_local = os.path.dirname(self.toml_path)
        if not os.path.exists(root_folder_local):
            return list_names

        folder = Path(root_folder_local)
        for item in folder.iterdir():
            if item.name.endswith(".toml"):
                list_names.append(item.name)

        return list_names


class MyInteractiveCLI(cmd.Cmd):
    prompt = "Tandem $ "
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
                    item.unlink()  # Deletes files and links inside
                elif item.is_dir():
                    shutil.rmtree(item)  # Deletes subfolders inside
            except Exception as e:
                print(f"Could not delete {item}. Error: {e}")

        if not os.path.exists(base_path):
            return

        for filename in os.listdir(base_path):
            if filename.endswith(".toml"):
                toml_path = os.path.join(base_path, filename)
                name = None
                language = None

                with open(toml_path, "r") as f:
                    for line in f:
                        if line.startswith("name = "):
                            name = line.split('"')[1]
                        elif line.startswith("language = "):
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

    def do_new(self, line):
        """Add an app. Usage: new <app_name> <app_language>"""
        if not line:
            print("Error: Please provide an app name and language")
            return

        parts = line.split()
        if len(parts) < 2:
            print("Error: Usage: new <app_name> <app_language>")
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

    def do_remove(self, line):
        """Removes an app Usage: remove <app_name>"""
        app_name = line.strip()
        if not app_name:
            print("Error: Usage: remove <app_name>")
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

    def _pid_file_path(self, app_name: str) -> str:
        return os.path.join(temp_folder, f"{app_name}.pid")

    def _load_pid(self, app_name: str):
        pid_file_path = self._pid_file_path(app_name)
        if not os.path.exists(pid_file_path):
            return None

        with open(pid_file_path, "r", encoding="utf-8") as pid_file:
            pid = pid_file.read().strip()

        return pid or None

    def _wait_for_job_results(
        self, job_id: str, job_token: str, timeout_seconds: int = 300
    ):
        results_url = f"{SERVER_URL}/start/{job_id}/results"
        headers = auth_headers({"X-Job-Token": job_token})
        started_at = time.time()
        last_snapshot = None

        while time.time() - started_at <= timeout_seconds:
            resp = requests.get(results_url, headers=headers, timeout=10)

            try:
                payload = resp.json()
            except Exception:
                payload = {}

            if resp.status_code == 200:
                return payload

            if resp.status_code != 202:
                print(f"Error while waiting for job {job_id}: {resp.status_code}")
                try:
                    print(resp.text)
                except Exception:
                    pass
                return None

            snapshot = (payload.get("status"), str(payload.get("counts")))
            if snapshot != last_snapshot:
                print(
                    f"Job {job_id}: status={payload.get('status')} counts={payload.get('counts')}"
                )
                last_snapshot = snapshot

            time.sleep(0.5)

        print(f"Timed out waiting for job {job_id} after {timeout_seconds} seconds")
        return None

    def _print_job_results(self, payload):
        print(
            f"Job complete: status={payload.get('status')} counts={payload.get('counts')}"
        )

        for item in payload.get("results", []):
            tid = item.get("tid")
            status = item.get("status")

            if status == "completed":
                raw = base64.b64decode(item.get("result_b64", ""))
                value = cloudpickle.loads(raw)
                print(f"  - {tid}: {value}")
            else:
                print(f"  - {tid}: FAILED - {item.get('error')}")

    def do_deploy(self, line):  # port 6767
        """Deploys an app to port 6767 Usage: deploy <app_name>"""

        app_name = line.strip()

        if not app_name:
            print("Error: Usage: deploy <app_name>")
            return

        for i, app in enumerate(self.apps):
            if app.name == app_name:
                try:
                    file_name = f"{app_name}.toml"
                    if not os.path.exists(app.toml_path):
                        print(f"Error: toml file not found at {app.toml_path}")
                        return

                    url = f"{SERVER_URL}/deploy/"

                    with open(app.toml_path, "rb") as file:
                        files = {"toml_file": (file_name, file, "text/plain")}
                        resp = requests.post(
                            url,
                            files=files,
                            headers=auth_headers(),
                            timeout=5,
                        )

                    print(resp.text)

                    if resp.status_code == 201:
                        try:
                            response_data = resp.json()
                            pid = response_data.get("pid")
                            if pid:
                                pid_file_path = self._pid_file_path(app_name)
                                with open(pid_file_path, "w") as pid_file:
                                    pid_file.write(str(pid))
                                print(f"Saved PID {pid} to {pid_file_path}")
                            else:
                                print(
                                    "Warning: No pid key found in server response JSON"
                                )
                        except Exception as json_err:
                            print(
                                f"Warning: Could not parse JSON response or save PID file: {json_err}"
                            )

                except Exception as e:
                    print(f"Error: could not send toml file: {e}")

                return

        print(f"Error: App '{app_name}' not found")

    def do_start(self, line):
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

        pid = self._load_pid(app_name)
        if not pid:
            print("Error: app has not been deployed yet. Run `deploy <app_name>` first")
            return

        url = f"{SERVER_URL}/start/"

        file_objs = []
        files = []
        try:
            toml_f = open(app.toml_path, "rb")
            file_objs.append(toml_f)
            files.append(
                ("toml_file", (os.path.basename(app.toml_path), toml_f, "text/plain"))
            )

            if not pickle_paths:
                default_dir = app.pickles_dir
                if os.path.isdir(default_dir):
                    entries = [
                        os.path.join(default_dir, x) for x in os.listdir(default_dir)
                    ]
                    pickle_paths = [p for p in entries if os.path.isfile(p)]

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

                f = open(p, "rb")
                file_objs.append(f)
                files.append(
                    (
                        "pickle_files",
                        (os.path.basename(p), f, "application/octet-stream"),
                    )
                )

            if len(files) <= 1:
                print("Error: No valid pickle files to send")
                return

            resp = requests.post(
                url,
                data={"pid": pid},
                files=files,
                headers=auth_headers(),
                timeout=30,
            )

            print("Status:", resp.status_code)
            try:
                print(resp.text)
            except Exception:
                print("<no text response>")

            if resp.status_code == 202:
                try:
                    payload = resp.json()
                except Exception as json_err:
                    print(f"Error: could not parse start response JSON: {json_err}")
                    return

                job_id = payload.get("job_id")
                job_token = payload.get("job_token")
                if not job_id or not job_token:
                    print("Error: server did not return job_id/job_token")
                    return

                print(f"Queued job {job_id}")
                result_payload = self._wait_for_job_results(job_id, job_token)
                if result_payload:
                    self._print_job_results(result_payload)

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

        with open(toml_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        table_line = f"[{table}]\n"
        in_table = False
        table_start = None
        table_end = None

        for i, ln in enumerate(lines):
            if ln.strip().startswith("[") and ln.strip().endswith("]"):
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
            key_prefix = key + " = "
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
            if not lines or not lines[-1].endswith("\n"):
                lines.append("\n")
            lines.append(table_line)
            lines.append(f'{key} = "{value}"\n')

        with open(toml_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        return True

    def do_set_run(self, line):
        """Set the run command for an app. Usage: set_run <app_name> <run command>"""
        parts = line.split(maxsplit=1)
        if len(parts) < 2:
            print("Usage: set_run <app_name> <run command>")
            return

        app_name, cmd = parts[0], parts[1]
        app = self.get_app(app_name)
        if not app:
            print(f"Error: App '{app_name}' not found")
            return

        ok = self._update_toml_field(app.toml_path, "tandem", "run", cmd)
        if ok:
            print(f"Set run command for '{app_name}': {cmd}")

    def do_set_install(self, line):
        """Set the install command for an app. Usage: set_install <app_name> <install command>"""
        parts = line.split(maxsplit=1)
        if len(parts) < 2:
            print("Usage: set_install <app_name> <install command>")
            return

        app_name, cmd = parts[0], parts[1]
        app = self.get_app(app_name)
        if not app:
            print(f"Error: App '{app_name}' not found")
            return

        ok = self._update_toml_field(app.toml_path, "tandem", "install", cmd)
        if ok:
            print(f"Set install command for '{app_name}': {cmd}")

    def do_set_script(self, line):
        """Reference an install/run script. Usage: set_script <app_name> <run|install> <script_path>"""
        parts = line.split(maxsplit=2)
        if len(parts) < 3:
            print("Usage: set_script <app_name> <run|install> <script_path>")
            return

        app_name, which, path_arg = parts[0], parts[1], parts[2]
        if which not in ("run", "install"):
            print("Second arg must be 'run' or 'install'")
            return

        key = f"{which}_script"
        app = self.get_app(app_name)
        if not app:
            print(f"Error: App '{app_name}' not found")
            return

        ok = self._update_toml_field(app.toml_path, "tandem", key, path_arg)
        if ok:
            print(f"Set {key} for '{app_name}': {path_arg}")

    def do_show_config(self, line):
        """Show parsed TOML fields for an app. Usage: show_config <app_name>"""
        app_name = line.strip()
        if not app_name:
            print("Usage: show_config <app_name>")
            return

        app = self.get_app(app_name)
        if not app:
            print(f"Error: App '{app_name}' not found")
            return

        if not os.path.exists(app.toml_path):
            print("TOML file missing")
            return

        with open(app.toml_path, "r", encoding="utf-8") as f:
            print(f.read())

    def do_help(self, arg):
        """Show minimal help listing: $ command ..."""
        commands = [
            "new <app_name> <app_language>",
            "remove <app_name>",
            "list",
            "deploy <app_name>",
            "start <app_name> [pickle_path1 ...]",
            "set_run <app_name> <run command>",
            "set_install <app_name> <install command>",
            "set_script <app_name> <run|install> <script_path>",
            "show_config <app_name>",
            "clear",
            "exit",
        ]
        for c in commands:
            print(f"$ {c}")

    def validate(self, app_name):
        for app in self.apps:
            if app.name == app_name:
                return True

        return False

    def get_app(self, app_name):
        for app in self.apps:
            if app.name == app_name:
                return app

        return None


if __name__ == "__main__":
    MyInteractiveCLI().cmdloop()
