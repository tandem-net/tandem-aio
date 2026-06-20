import tomllib as _toml
from typing import Any


def parse_toml_string(s: Any) -> dict:
    # file-like object (Flask's FileStorage, open file, etc.)
    if hasattr(s, 'read'):
        raw = s.read()
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        return _toml.loads(raw)

    # bytes
    if isinstance(s, (bytes, bytearray)):
        s = s.decode('utf-8')

    # assume string now
    return _toml.loads(s)


def extract_name(parsed: dict) -> str | None:
    if not isinstance(parsed, dict):
        return None

    # top-level
    if 'name' in parsed and isinstance(parsed['name'], str):
        return parsed['name']

    # common tables
    for table in ('app', 'project', 'package'):
        t = parsed.get(table)
        if isinstance(t, dict) and isinstance(t.get('name'), str):
            return t.get('name')

    # poetry / tool layout
    tool = parsed.get('tool')
    if isinstance(tool, dict):
        poetry = tool.get('poetry')
        if isinstance(poetry, dict) and isinstance(poetry.get('name'), str):
            return poetry.get('name')

    return None


def extract_language(parsed: dict) -> str | None:
    """Find a language value commonly stored under `[app].language` or top-level."""
    if not isinstance(parsed, dict):
        return None

    if 'language' in parsed and isinstance(parsed['language'], str):
        return parsed['language']

    app = parsed.get('app')
    if isinstance(app, dict) and isinstance(app.get('language'), str):
        return app.get('language')

    # other possible locations
    for table in ('project', 'package'):
        t = parsed.get(table)
        if isinstance(t, dict) and isinstance(t.get('language'), str):
            return t.get('language')

    return None


def get_relevant(parsed: dict) -> dict:
    """Return a small dict of commonly useful fields from parsed TOML."""
    out = {}
    if not isinstance(parsed, dict):
        return out

    out['name'] = extract_name(parsed)
    # version
    if isinstance(parsed.get('version'), str):
        out['version'] = parsed.get('version')
    else:
        for table in ('project', 'tool'):
            t = parsed.get(table)
            if isinstance(t, dict) and isinstance(t.get('version'), str):
                out['version'] = t.get('version')
                break

    # authors (common locations)
    authors = None
    project = parsed.get('project')
    if isinstance(project, dict):
        authors = project.get('authors') or project.get('author')

    if not authors:
        tool = parsed.get('tool')
        if isinstance(tool, dict):
            poetry = tool.get('poetry')
            if isinstance(poetry, dict):
                authors = poetry.get('authors') or poetry.get('author')

    if authors:
        out['authors'] = authors

    lang = extract_language(parsed)
    if lang:
        out['language'] = lang

    tandem = parsed.get('tandem') if isinstance(parsed.get('tandem'), dict) else None

    def _find_key(k: str):
        if tandem and isinstance(tandem.get(k), str):
            return tandem.get(k)

        # check app table
        app = parsed.get('app')
        if isinstance(app, dict) and isinstance(app.get(k), str):
            return app.get(k)

        if isinstance(parsed.get(k), str):
            return parsed.get(k)

        return None

    run_cmd = _find_key('run')
    install_cmd = _find_key('install')
    run_script = _find_key('run_script')
    install_script = _find_key('install_script')

    if run_cmd:
        out['run'] = run_cmd
    if install_cmd:
        out['install'] = install_cmd
    if run_script:
        out['run_script'] = run_script
    if install_script:
        out['install_script'] = install_script

    return out
