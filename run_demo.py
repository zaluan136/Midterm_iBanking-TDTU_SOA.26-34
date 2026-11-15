"""One command: Docker iBanking + ngrok; Ctrl+C stops this Compose stack."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent


def compose_command(public=True):
    command = ['docker', 'compose', '-f', 'compose.yaml']
    if public:
        command += ['-f', 'compose.ngrok.yaml']
    return command


def run(command, env, **kwargs):
    return subprocess.run(command, cwd=ROOT, env=env, check=True, **kwargs)


def prepare_keys():
    target = ROOT / '.env.docker'
    if not target.exists():
        with target.open('x', encoding='utf-8') as f:
            for name in ('JWT_SECRET', 'SERVICE_TOKEN', 'OTP_SECRET'):
                f.write(f'{name}={secrets.token_urlsafe(48)}\n')
            f.write('DB_SCHEMA=public\n')


def find_ngrok_token():
    token = os.getenv('NGROK_AUTHTOKEN', '').strip()
    if token:
        return token
    candidates = []
    if os.getenv('LOCALAPPDATA'):
        candidates.append(Path(os.environ['LOCALAPPDATA']) / 'ngrok/ngrok.yml')
    candidates += [Path.home()/'.config/ngrok/ngrok.yml', Path.home()/'.ngrok2/ngrok.yml']
    for file in candidates:
        if file.is_file():
            match = re.search(r'^\s*authtoken:\s*[\"\x27]?([^\s\"\x27#]+)', file.read_text(encoding='utf-8-sig'), re.M)
            if match:
                return match.group(1)
    return ''


def prepare_ngrok():
    target = ROOT / '.env.ngrok'
    if target.exists():
        content = target.read_text(encoding='utf-8-sig')
        if re.search(r'^NGROK_AUTHTOKEN=\S+', content, re.M):
            return
        raise RuntimeError('.env.ngrok chua co NGROK_AUTHTOKEN hop le.')
    token = find_ngrok_token()
    if not token:
        print('Lan dau: lay Authtoken tai https://dashboard.ngrok.com/get-started/your-authtoken', flush=True)
        if not sys.stdin.isatty():
            raise RuntimeError('Can nhap ngrok token trong terminal, hoac dat NGROK_AUTHTOKEN truoc khi chay.')
        token = getpass.getpass('Dan ngrok Authtoken (khong hien ky tu): ').strip()
    if not token or any(c.isspace() for c in token):
        raise RuntimeError('Authtoken rong hoac sai dinh dang; chua luu.')
    with target.open('x', encoding='utf-8') as f:
        f.write('NGROK_AUTHTOKEN=' + token + '\n')
    print('Da luu .env.ngrok cho nhung lan chay sau.', flush=True)


def ensure_port_free(port):
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError(f'Cong {port} dang duoc dung. Dung app local/ngrok hoac phien demo cu truoc khi chay.')


def tunnel_url(timeout=60):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with opener.open('http://127.0.0.1:4040/api/tunnels', timeout=2) as response:
                tunnels = json.load(response).get('tunnels', [])
            for tunnel in tunnels:
                url = tunnel.get('public_url', '')
                if url.startswith('https://'):
                    return url
        except (OSError, ValueError, urllib.error.URLError):
            pass
        time.sleep(1)
    raise RuntimeError('Ngrok chua tao duoc link. Kiem tra token, mang va log ngrok ben duoi.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', action='store_true', help='Docker local only; enable demo tools, no ngrok')
    args = parser.parse_args(argv)
    public = not args.local
    env = os.environ.copy()
    # Explicit override for every app container, including those with their own environment map.
    env['DEMO_ADMIN'] = '0' if public else '1'
    command = compose_command(public)
    attempted = False
    try:
        if not shutil.which('docker'):
            raise RuntimeError('Chua co Docker Desktop. Cai Docker Desktop, mo ung dung (Linux containers), roi chay lai lenh nay.')
        run(['docker', 'compose', 'version'], env, stdout=subprocess.DEVNULL)
        run(['docker', 'info'], env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for relative in ('DB/connection string.txt', '.env.gmail'):
            if not (ROOT / relative).is_file():
                raise RuntimeError('Thieu file: ' + relative)
        ensure_port_free(8000)
        if public:
            ensure_port_free(4040)
        prepare_keys()
        if public:
            prepare_ngrok()
        run(command + ['config', '--quiet'], env)
        print('Dang build va khoi dong Docker; lan dau can tai image va thu vien...', flush=True)
        attempted = True
        run(command + ['up', '--build', '-d', '--wait', '--wait-timeout', '180'], env)
        print('\nLOCAL: http://127.0.0.1:8000/', flush=True)
        if public:
            print('PUBLIC: ' + tunnel_url(), flush=True)
            print('Link public: Cong cu demo da tat. May va Docker phai tiep tuc chay.', flush=True)
        print('Nhan Ctrl+C de dung Docker va ngrok. Khong can go lenh down.', flush=True)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nDang dung demo...', flush=True)
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('\nKhong khoi dong duoc: ' + str(exc), file=sys.stderr, flush=True)
        if attempted:
            subprocess.run(command + ['logs', '--tail', '25'], cwd=ROOT, env=env, check=False)
        return 1
    finally:
        if attempted:
            try:
                subprocess.run(command + ['stop', '--timeout', '15'], cwd=ROOT, env=env, check=False)
            except OSError:
                print('Khong goi duoc Docker de dung. Mo Docker Desktop va dung project ibanking.', file=sys.stderr)


if __name__ == '__main__':
    sys.exit(main())
