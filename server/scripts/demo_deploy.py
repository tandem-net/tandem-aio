import json
import urllib.request
import urllib.error


def deploy_demo(url='http://localhost:5000/deploy', name='demo-app'):
    payload = {'name': name}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode('utf-8')
            print(f'Status: {resp.status}')
            print(body)
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else ''
        print(f'HTTP Error: {e.code}')
        print(body)
        return e.code, body
    except Exception as e:
        print('Error:', e)
        return None, str(e)


if __name__ == '__main__':
    deploy_demo()
