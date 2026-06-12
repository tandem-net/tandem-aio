import requests


def deploy_demo(url='http://localhost:5000/deploy', name='demo-app', verify=True):
    toml_text = f'[app]\nname = "{name}"\n'
    files = {'toml_file': ('config.toml', toml_text, 'text/plain')}
    resp = requests.post(url, files=files, timeout=5, verify=verify)
    print('Status:', resp.status_code)
    print(resp.text)
    return resp.status_code, resp.text


if __name__ == '__main__':
    deploy_demo()
