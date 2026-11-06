"""Authorize the midterm Gmail account once and save local, Git-ignored settings."""
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


ROOT = Path(__file__).resolve().parent
DESTINATION = ROOT / '.env.gmail'
SCOPE = 'https://www.googleapis.com/auth/gmail.send'


def main():
    files = list(ROOT.glob('client_secret_*.json'))
    if len(files) != 1:
        raise SystemExit('Cần đúng một file client_secret_*.json trong thư mục dự án.')
    if DESTINATION.exists():
        raise SystemExit('Đã có .env.gmail. Không ghi đè; hãy kiểm tra file này trước.')
    data = json.loads(files[0].read_text(encoding='utf-8'))['installed']
    flow = InstalledAppFlow.from_client_secrets_file(str(files[0]), [SCOPE])
    credentials = flow.run_local_server(host='localhost', port=0, open_browser=True,
                                        authorization_prompt_message='Mở link này nếu trình duyệt không tự mở: {url}',
                                        success_message='Đã cấp quyền. Quay lại terminal.')
    if not credentials.refresh_token:
        raise SystemExit('Google không cấp refresh token. Chưa lưu cấu hình; cần cấp quyền lại với offline access.')
    values = {
        'GOOGLE_CLIENT_ID': data['client_id'],
        'GOOGLE_CLIENT_SECRET': data['client_secret'],
        'GOOGLE_REFRESH_TOKEN': credentials.refresh_token,
        'GMAIL_SENDER': input('Nhập địa chỉ Gmail vừa cấp quyền: ').strip(),
    }
    if not values['GMAIL_SENDER'] or '@' not in values['GMAIL_SENDER']:
        raise SystemExit('Địa chỉ Gmail chưa hợp lệ; chưa lưu cấu hình.')
    # JSON quoted strings are accepted by python-dotenv and protect special characters.
    DESTINATION.write_text(''.join(f'{key}={json.dumps(value)}\n' for key, value in values.items()), encoding='utf-8')
    print('Đã lưu cấu hình vào .env.gmail (Git bỏ qua file này).')


if __name__ == '__main__':
    main()
