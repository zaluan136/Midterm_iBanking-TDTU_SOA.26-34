"""Two independent demo modes: Docker local OR native Python with ngrok."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import signal
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent


def compose_command():
    return ['docker', 'compose', '-f', 'compose.yaml']


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


def docker_mode():
    env = os.environ.copy()
    env['DEMO_ADMIN'] = '1'
    command = compose_command()
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
        prepare_keys()
        run(command + ['config', '--quiet'], env)
        print('Dang build va khoi dong Docker; lan dau can tai image va thu vien...', flush=True)
        attempted = True
        run(command + ['up', '--build', '-d', '--wait', '--wait-timeout', '180'], env)
        print('\nLOCAL: http://127.0.0.1:8000/', flush=True)
        print('Docker local, khong chay ngrok. Cong cu demo da bat.', flush=True)
        print('Nhan Ctrl+C de dung Docker. Khong can go lenh down.', flush=True)
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


def ngrok_executable():
    found = shutil.which('ngrok')
    if found:
        return found
    if os.name == 'nt':
        alias = Path(os.getenv('LOCALAPPDATA', '')) / 'Microsoft/WindowsApps/ngrok.exe'
        if alias.is_file():
            return str(alias)
    raise RuntimeError('Chua co ngrok CLI. Cai tu https://ngrok.com/download/windows, mo lai terminal roi chay lai. Khong can Docker.')


def start_process(command, env):
    kwargs = {'cwd': ROOT, 'env': env}
    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(command, **kwargs)


def wait_app(processes, port, timeout=60):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for name, process in processes:
            if process.poll() is not None:
                raise RuntimeError(name + ' da dung; xem log phia tren.')
        try:
            with opener.open(f'http://127.0.0.1:{port}/health', timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.25)
    raise RuntimeError(f'Service cong {port} chua san sang sau {timeout}s.')


def stop_processes(processes):
    for _, process in reversed(processes):
        if process.poll() is None:
            try:
                if os.name == 'nt':
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    process.terminate()
            except OSError:
                pass
    for _, process in reversed(processes):
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            if os.name == 'nt':
                # This PID is a process launched by this script, never an arbitrary listener.
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            else:
                process.kill()
            process.wait()


def native_environment():
    env = os.environ.copy()
    env['DEMO_ADMIN'] = '0'
    for name in ('JWT_SECRET', 'SERVICE_TOKEN', 'OTP_SECRET'):
        if not env.get(name):
            env[name] = secrets.token_urlsafe(48)
    for name, port in [('auth_account',8001),('payment',8002),('tuition',8003),('otp',8004)]:
        env[name.upper() + '_SERVICE_URL'] = f'http://127.0.0.1:{port}'
    # Supply the saved token without modifying ngrok's global configuration.
    for line in (ROOT / '.env.ngrok').read_text(encoding='utf-8-sig').splitlines():
        if line.startswith('NGROK_AUTHTOKEN='):
            env['NGROK_AUTHTOKEN'] = line.split('=', 1)[1].strip().strip('\"\x27')
    return env


def ngrok_mode():
    processes = []
    try:
        executable = ngrok_executable()
        for relative in ('DB/connection string.txt', '.env.gmail'):
            if not (ROOT / relative).is_file():
                raise RuntimeError('Thieu file: ' + relative)
        for port in (8000,8001,8002,8003,8004,4040):
            ensure_port_free(port)
        prepare_ngrok()
        env = native_environment()
        for name, port in [('auth_account',8001),('tuition',8003),('otp',8004),('payment',8002),('gateway',8000)]:
            process = start_process([sys.executable,'-m','uvicorn',f'services.{name}:app','--host','127.0.0.1','--port',str(port)], env)
            processes.append((name, process))
            wait_app(processes, port)
        # A dedicated config fixes the inspection API port regardless of global ngrok settings.
        processes.append(('ngrok', start_process([executable,'http','http://127.0.0.1:8000','--config',str(ROOT/'ngrok-native.yml'),'--log','stdout'], env)))
        print('\nLOCAL: http://127.0.0.1:8000/', flush=True)
        print('PUBLIC: ' + tunnel_url(), flush=True)
        print('Python local + ngrok, KHONG dung Docker. Cong cu demo public da tat.', flush=True)
        print('Nhan Ctrl+C de dung ngrok va app Python.', flush=True)
        while True:
            for name, process in processes:
                if process.poll() is not None:
                    raise RuntimeError(name + ' da dung; xem log phia tren.')
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nDang dung ngrok va app...', flush=True)
        return 0
    except (OSError, RuntimeError) as exc:
        print('\nKhong khoi dong duoc: ' + str(exc), file=sys.stderr, flush=True)
        return 1
    finally:
        stop_processes(processes)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--ngrok', action='store_true', help='Native Python + ngrok, no Docker')
    modes.add_argument('--local', action='store_true', help='Alias for Docker local, the default')
    modes.add_argument('--docker', action='store_true', help='Docker local, no ngrok')
    args = parser.parse_args(argv)
    return ngrok_mode() if args.ngrok else docker_mode()


if __name__ == '__main__':
    sys.exit(main())
