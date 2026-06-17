import subprocess
import threading
import os
import sys
import json
import socket
from tkinter import messagebox

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, "freeman_data.db")
JSON_PATH = os.path.join(PROJECT_DIR, 'school_config.json')

if not os.path.exists(DB_PATH):
    print(f"WARNING: Database not found at {DB_PATH}. Check that the database exists in the project folder.")

def load_school_name():
    try:
        if os.path.exists(JSON_PATH):
            with open(JSON_PATH, 'r') as f:
                config = json.load(f)
                name = config.get('school_name', '')
                return name.strip() if isinstance(name, str) and name.strip() else 'Freeman'
    except Exception:
        pass
    return 'Freeman'


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def check_hosted_network_support():
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'drivers'], capture_output=True, text=True)
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            return False, output.strip() or "Could not query WLAN driver support."

        for line in output.splitlines():
            normalized = line.strip().lower()
            if 'hosted network supported' in normalized:
                supported = normalized.split(':', 1)[1].strip()
                if supported == 'yes':
                    return True, ''
                if supported == 'no':
                    return False, 'Hosted network not supported by this adapter.'
                return False, f'Hosted network support value: {supported}'

        return False, 'Unable to determine hosted network support from driver info.'
    except Exception as e:
        return False, str(e)


def start_hosted_network(ssid, password):
    set_cmd = ['netsh', 'wlan', 'set', 'hostednetwork', 'mode=allow', f'ssid={ssid}', f'key={password}']
    start_cmd = ['netsh', 'wlan', 'start', 'hostednetwork']

    set_result = subprocess.run(set_cmd, capture_output=True, text=True)
    if set_result.returncode != 0:
        return False, set_result.stderr.strip() or set_result.stdout.strip()

    start_result = subprocess.run(start_cmd, capture_output=True, text=True)
    if start_result.returncode != 0:
        return False, start_result.stderr.strip() or start_result.stdout.strip()

    return True, ''


def launch_sync_portal(school_name="Freeman"):
    try:
        if not school_name:
            school_name = load_school_name()

        ssid_base = str(school_name).strip() or 'Freeman'
        ssid = f"{ssid_base.replace(' ', '_')}_Sync"
        password = "freeman26"

        supported, support_message = check_hosted_network_support()
        hotspot_started = False
        hotspot_message = ''

        if supported:
            hotspot_started, hotspot_message = start_hosted_network(ssid, password)
        else:
            hotspot_message = support_message
            if support_message.startswith('Unable to determine'):
                hotspot_started, fallback_message = start_hosted_network(ssid, password)
                if hotspot_started:
                    hotspot_message = ''
                else:
                    hotspot_message = f"{support_message}\n{fallback_message}"

        def run_flask():
            server_script = os.path.join(PROJECT_DIR, "hotspot_server.py")
            os.system(f'"{sys.executable}" "{server_script}"')

        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

        server_url = f"http://{get_local_ip()}:5000"
        if hotspot_started:
            return True, f"HOTSPOT|{ssid}|{password}|{server_url}"

        return True, f"SERVER_ONLY|{server_url}|{hotspot_message}"
    except Exception as e:
        return False, str(e)