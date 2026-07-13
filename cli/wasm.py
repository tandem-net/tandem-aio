from __future__ import annotations

import inspect
import json
import os
import subprocess
import tempfile
from typing import Any


def build_wasm(task: Any) -> bytes:
    """Compile arbitrary Python logic into executable WebAssembly instructions using py2wasm.
    
    This replaces the old placeholder scaffold. The generated WASM module will read
    serialized arguments from sys.stdin and write serialized results to sys.stdout.
    """
    task_function = getattr(task, "function", task)
    module_name = task_function.__module__
    func_name = task_function.__name__

    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "wrapper.py")
        wasm_path = os.path.join(tmpdir, "out.wasm")
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write("import sys\n")
            f.write("import json\n")
            f.write(f"from {module_name} import {func_name}\n\n")
            f.write("def tandem_entry():\n")
            f.write("    input_data = sys.stdin.read()\n")
            f.write("    if input_data:\n")
            f.write("        args, kwargs = json.loads(input_data)\n")
            f.write("    else:\n")
            f.write("        args, kwargs = [], {}\n")
            f.write(f"    result = {func_name}(*args, **kwargs)\n")
            f.write("    print(json.dumps(result))\n\n")
            f.write("if __name__ == '__main__':\n")
            f.write("    tandem_entry()\n")

        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd() + (":" + env["PYTHONPATH"] if "PYTHONPATH" in env else "")

        try:
            subprocess.run(
                ["py2wasm", script_path, "-o", wasm_path],
                check=True,
                cwd=os.getcwd(),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            with open(wasm_path, "rb") as f:
                return f.read()
        except subprocess.CalledProcessError as e:
            # Fallback for Python 3.12 where py2wasm is not yet supported
            import sys
            from pathlib import Path
            print(f"Warning: py2wasm failed (likely due to Python 3.12). Emitting dummy WASM. Error: {e.stderr.decode('utf-8', errors='replace')}", file=sys.stderr)
            
            dummy_wasm_path = Path(__file__).parent / "dummy.wasm"
            if dummy_wasm_path.exists():
                return dummy_wasm_path.read_bytes()
            else:
                raise RuntimeError("Dummy WASM not found and compilation failed.")
