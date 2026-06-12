import requests


def start_demo(url='http://localhost:5000/start', verify=True):
    toml_text = '[app]\nname = "demo-start"\n'

    p1 = b'fake-pickle-1'
    p2 = b'fake-pickle-2'

    files = [
        ('pickle_files', ('p1.pkl', p1, 'application/octet-stream')),
        ('pickle_files', ('p2.pkl', p2, 'application/octet-stream')),
        ('toml_file', ('config.toml', toml_text.encode('utf-8'), 'text/plain')),
    ]

    # requests will encode multipart/form-data correctly
    resp = requests.post(url, files=files, timeout=10, verify=verify)
    print('Status:', resp.status_code)
    print(resp.text)
    return resp.status_code, resp.text


if __name__ == '__main__':
    start_demo()
