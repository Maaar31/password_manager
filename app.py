from flask import Flask, request, jsonify
from cryptography.fernet import Fernet
import os
import threading
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
import json
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)
key = Fernet.generate_key()
cipher_suite = Fernet(key)

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# Google Authentication
def authenticate_user():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as token_file:
            creds = Credentials.from_authorized_user_info(json.load(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'w') as token_file:
            token_file.write(creds.to_json())

    return creds

credentials = authenticate_user()
drive_service = build('drive', 'v3', credentials=credentials)

# Google Drive Integration
def upload_password_to_drive(password):
    file_metadata = {'name': 'password.txt'}
    media = MediaFileUpload('password.txt', mimetype='text/plain')
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def download_password_from_drive(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh.read().decode()

@app.route('/store_password', methods=['POST'])
def store_password():
    data = request.json
    password = data.get('password')
    encrypted_password = cipher_suite.encrypt(password.encode())

    with open('password.txt', 'wb') as f:
        f.write(encrypted_password)

    file_id = upload_password_to_drive(encrypted_password)

    return jsonify({"status": "success", "file_id": file_id})

@app.route('/retrieve_password', methods=['POST'])
def retrieve_password():
    data = request.json
    file_id = data.get('file_id')

    encrypted_password = download_password_from_drive(file_id)
    decrypted_password = cipher_suite.decrypt(encrypted_password.encode()).decode()

    return jsonify({"password": decrypted_password})

@app.route('/get_passwords', methods=['GET'])
def get_passwords():
    # Placeholder: Retrieve stored passwords (to be implemented)
    passwords = ["site1:password1", "site2:password2"]
    return jsonify({"passwords": passwords})

def run_app():
    app.run()

# System Tray Integration
def create_image():
    width = 64
    height = 64
    color1 = (0, 0, 0)
    color2 = (255, 255, 255)

    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)

    return image

def show_passwords(icon, item):
    # Placeholder: Show stored passwords (to be implemented)
    print("Showing passwords")

def search_password(icon, item):
    # Placeholder: Search passwords (to be implemented)
    print("Searching password")

def import_passwords(icon, item):
    # Placeholder: Import passwords (to be implemented)
    print("Importing passwords")

def start_monitor(icon, item):
    threading.Thread(target=monitor_browser).start()

def on_quit(icon, item):
    icon.stop()

menu = (
    item('Show Passwords', show_passwords),
    item('Search Password', search_password),
    item('Import Firefox Passwords', import_passwords),
    item('Start Monitor', start_monitor),
    item('Quit', on_quit)
)
icon = pystray.Icon("password_manager", create_image(), "Password Manager", menu)

def run_systray():
    icon.run()

# Browser Monitoring
def monitor_browser():
    driver = webdriver.Chrome(executable_path='path/to/chromedriver')
    driver.get("http://example.com")

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "form")))
    except:
        driver.quit()

    forms = driver.find_elements(By.TAG_NAME, "form")
    for form in forms:
        form_id = form.get_attribute("id")
        if form_id:
            driver.execute_script(f'''
                document.getElementById('{form_id}').onsubmit = function() {{
                    var username = document.querySelector("input[type='text']").value;
                    var password = document.querySelector("input[type='password']").value;
                    fetch('http://127.0.0.1:5000/check_and_save', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            'username': username,
                            'password': password,
                            'url': window.location.href
                        }})
                    }}).then(response => response.json()).then(data => {{
                        if (data.status === 'prompt') {{
                            var save = confirm('Do you want to save this password?');
                            if (save) {{
                                fetch('http://127.0.0.1:5000/save_password', {{
                                    method: 'POST',
                                    headers: {{
                                        'Content-Type': 'application/json'
                                    }},
                                    body: JSON.stringify({{
                                        'username': username,
                                        'password': password,
                                        'url': window.location.href
                                    }})
                                }});
                            }}
                        }}
                    }});
                }};
            ''')

    driver.quit()

if __name__ == '__main__':
    authenticate_user()
    threading.Thread(target=run_app).start()
    run_systray()
