import json

import requests
from demo_deploy import auth_headers, deploy_demo

DEFAULT_BASE_URL = "http://localhost:6767"


def start_demo(base_url=DEFAULT_BASE_URL, name="demo-start", verify=True):
    deploy_status, deploy_text = deploy_demo(
        base_url=base_url, name=name, verify=verify
    )
    if deploy_status != 201:
        raise RuntimeError(f"Deploy failed before start demo: {deploy_text}")

    deploy_payload = json.loads(deploy_text)
    pid = deploy_payload["pid"]
    url = f"{base_url.rstrip('/')}/start/"
    toml_text = f'[app]\nname = "{name}"\nlanguage = "python"\n'

    # This demo only exercises the queueing API. These are placeholder payloads,
    # so a real node will mark them as failed if it tries to execute them.
    p1 = b"fake-pickle-1"
    p2 = b"fake-pickle-2"

    files = [
        ("pickle_files", ("p1.pkl", p1, "application/octet-stream")),
        ("pickle_files", ("p2.pkl", p2, "application/octet-stream")),
        ("toml_file", ("config.toml", toml_text.encode("utf-8"), "text/plain")),
    ]

    resp = requests.post(
        url,
        data={"pid": pid},
        files=files,
        headers=auth_headers(),
        timeout=10,
        verify=verify,
    )
    print("Status:", resp.status_code)
    print(resp.text)
    return resp.status_code, resp.text


if __name__ == "__main__":
    start_demo()
