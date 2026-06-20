import requests

DEFAULT_BASE_URL = "http://localhost:6767"


def deploy_demo(base_url=DEFAULT_BASE_URL, name="demo-app", verify=True):
    url = f"{base_url.rstrip('/')}/deploy/"
    toml_text = f'[app]\nname = "{name}"\nlanguage = "python"\n'
    files = {"toml_file": ("config.toml", toml_text, "text/plain")}

    resp = requests.post(url, files=files, timeout=5, verify=verify)
    print("Status:", resp.status_code)
    print(resp.text)
    return resp.status_code, resp.text


if __name__ == "__main__":
    deploy_demo()
