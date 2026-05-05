import os
import json
from urllib.parse import urlparse
from tkinter import messagebox
from tkinter.simpledialog import askstring

try:
    import requests
except ImportError:
    requests = None

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PROJECT_DIR, 'school_config.json')
DEFAULT_CLOUD_URL = 'http://localhost:7000'


def normalize_cloud_url(url):
    if not url:
        return ''
    url = url.strip()
    if '://' not in url:
        url = 'https://' + url
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return ''
    return url.rstrip('/')


def get_cloud_url():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return normalize_cloud_url(config.get('cloud_portal_url', DEFAULT_CLOUD_URL)) or DEFAULT_CLOUD_URL
    except Exception:
        pass
    return DEFAULT_CLOUD_URL


def ask_cloud_credentials(parent=None):
    school_code = askstring('Cloud School Code', 'Enter your school code:', parent=parent)
    if not school_code:
        return None

    username = askstring('Cloud Username', 'Enter your cloud username:', parent=parent)
    if not username:
        return None

    password = askstring('Cloud Password', 'Enter your cloud password:', show='*', parent=parent)
    if not password:
        return None

    return {
        'school_code': school_code.strip(),
        'username': username.strip(),
        'password': password
    }


class CloudService:
    def __init__(self):
        self.base_url = get_cloud_url()
        self.session = requests.Session() if requests else None

    def _ensure_requests(self):
        if requests is None:
            messagebox.showerror('Cloud Sync Error', 'The Python package "requests" is required for cloud sync.')
            return False
        return True

    def _post_json(self, endpoint, payload):
        if not self._ensure_requests():
            return {'success': False, 'message': 'Requests library not installed.'}

        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.post(url, json=payload, timeout=20)
            if response.status_code != 200:
                return {'success': False, 'message': f'Cloud portal returned {response.status_code}: {response.text}'}
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'success': False, 'message': f'Could not connect to cloud portal at {self.base_url}: {e}'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def fetch_marks(self, grade, credentials):
        payload = {
            'school_code': credentials['school_code'],
            'username': credentials['username'],
            'password': credentials['password'],
            'grade': grade
        }
        return self._post_json('/api/fetch_marks', payload)

    def upload_marks(self, grade, exam_title, records, credentials):
        payload = {
            'school_code': credentials['school_code'],
            'username': credentials['username'],
            'password': credentials['password'],
            'grade': grade,
            'exam_title': exam_title,
            'records': records
        }
        return self._post_json('/api/save_marks', payload)

    def sync_students(self, students, credentials):
        payload = {
            'school_code': credentials['school_code'],
            'username': credentials['username'],
            'password': credentials['password'],
            'students': students
        }
        return self._post_json('/api/upload_students', payload)

    def fetch_students(self, grade, credentials):
        payload = {
            'school_code': credentials['school_code'],
            'username': credentials['username'],
            'password': credentials['password'],
            'grade': grade
        }
        return self._post_json('/api/fetch_students', payload)


def apply_cloud_records_to_table(table_frame, records, subjects, columns_per_subject=2):
    record_map = {r.get('name', '').strip().lower(): r for r in records}
    for row_frame in table_frame.winfo_children():
        if not hasattr(row_frame, 'grid_slaves'):
            continue

        widgets = row_frame.grid_slaves(row=0)
        if not widgets:
            continue

        widgets.sort(key=lambda w: int(w.grid_info()['column']))
        student_name = widgets[0].cget('text').strip().lower()
        record = record_map.get(student_name)
        if not record:
            continue

        scores = record.get('scores', {})
        for i, subject in enumerate(subjects):
            subject_data = scores.get(subject, {})
            score_value = subject_data.get('score', '')
            rating_value = subject_data.get('rating', '')
            point_value = subject_data.get('points', '')

            score_widget = widgets[1 + i * columns_per_subject]
            rating_widget = widgets[1 + i * columns_per_subject + 1]

            if hasattr(score_widget, 'delete'):
                score_widget.delete(0, 'end')
                score_widget.insert(0, str(score_value))

            if hasattr(rating_widget, 'delete'):
                rating_widget.delete(0, 'end')
                rating_widget.insert(0, str(rating_value))

            if columns_per_subject == 3:
                point_widget = widgets[1 + i * columns_per_subject + 2]
                if hasattr(point_widget, 'delete'):
                    point_widget.delete(0, 'end')
                    point_widget.insert(0, str(point_value))

        if len(widgets) >= 3:
            total_widget = widgets[-3]
            avg_widget = widgets[-2]
            if hasattr(total_widget, 'delete'):
                total_widget.delete(0, 'end')
                total_widget.insert(0, str(record.get('total_points', '')))
            if hasattr(avg_widget, 'delete'):
                avg_widget.delete(0, 'end')
                avg_widget.insert(0, str(record.get('average_level', '')))

    return True
