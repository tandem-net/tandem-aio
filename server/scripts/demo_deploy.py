import os

import requests

DEFAULT_BASE_URL = "http://localhost:6767"
API_KEY_ENV_VAR = "TANDEM_API_KEY"


def auth_headers(extra_headers=None):
    api_key = (os.environ.get(API_KEY_ENV_VAR) or "").strip()
    if not api_key:
        raise RuntimeError(f"Missing {API_KEY_ENV_VAR} environment variable")

    headers = dict(extra_headers or {})
    headers["X-API-Key"] = api_key
    return headers


def deploy_demo(base_url=DEFAULT_BASE_URL, name="demo-app", verify=True):
    url = f"{base_url.rstrip('/')}/deploy/"
    toml_text = f'[app]\nname = "{name}"\nlanguage = "python"\n'
    files = {"toml_file": ("config.toml", toml_text, "text/plain")}

    resp = requests.post(
        url,
        files=files,
        headers=auth_headers(),
        timeout=5,
        verify=verify,
    )
    print("Status:", resp.status_code)
    print(resp.text)
    return resp.status_code, resp.text


if __name__ == "__main__":
    deploy_demo()
