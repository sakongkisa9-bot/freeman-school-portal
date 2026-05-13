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
CONFIG_PATH = os.path.join(PROJECT_DIR, "school_config.json")
DEFAULT_CLOUD_URL = "http://localhost:7000"


def normalize_cloud_url(url):
    if not url:
        return ""
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return url.rstrip("/")


def get_cloud_url():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                return (
                    normalize_cloud_url(
                        config.get("cloud_portal_url", DEFAULT_CLOUD_URL)
                    )
                    or DEFAULT_CLOUD_URL
                )
    except Exception:
        pass
    return DEFAULT_CLOUD_URL


def ask_cloud_credentials(parent=None):
    school_code = askstring(
        "Cloud School Code", "Enter your school code:", parent=parent
    )
    if not school_code:
        return None

    username = askstring("Cloud Username", "Enter your cloud username:", parent=parent)
    if not username:
        return None

    password = askstring(
        "Cloud Password", "Enter your cloud password:", show="*", parent=parent
    )
    if not password:
        return None

    return {
        "school_code": school_code.strip(),
        "username": username.strip(),
        "password": password,
    }


class CloudService:
    def __init__(self):
        self.base_url = get_cloud_url()
        self.session = requests.Session() if requests else None

    def _ensure_requests(self):
        if requests is None:
            messagebox.showerror(
                "Cloud Sync Error",
                'The Python package "requests" is required for cloud sync.',
            )
            return False
        return True

    def _post_json(self, endpoint, payload):
        if not self._ensure_requests():
            return {"success": False, "message": "Requests library not installed."}

        try:
            url = f"{self.base_url}{endpoint}"
            # --- DEBUG PRINT ---
            print(f"SYNC ATTEMPT: Sending data to {url}")

            response = self.session.post(url, json=payload, timeout=20)

            if response.status_code != 200:
                # This will pop up a window telling us exactly what Railway said
                error_detail = f"Status: {response.status_code}\nURL: {url}\nResponse: {response.text}"
                print(f"SYNC ERROR:\n{error_detail}")
                return {"success": False, "message": error_detail}

            return response.json()
        except Exception as e:
            return {"success": False, "message": f"Connection Failed: {e}"}

    def fetch_marks(self, grade, credentials):
        payload = {
            "school_code": credentials["school_code"],
            "username": credentials["username"],
            "password": credentials["password"],
            "grade": grade,
        }
        return self._post_json("/api/get_marks", payload)

    def upload_marks(self, grade, exam_title, records, credentials):
        payload = {
            "school_code": credentials["school_code"],
            "username": credentials["username"],
            "password": credentials["password"],
            "grade": grade,
            "exam_title": exam_title,
            "records": records,
        }
        return self._post_json("/api/save_marks", payload)

    def sync_students(self, students, credentials):
        payload = {
            "school_code": credentials["school_code"],
            "username": credentials["username"],
            "password": credentials["password"],
            "students": students,
        }
        return self._post_json("/api/upload_students", payload)

    def fetch_students(self, grade, credentials):
        payload = {
            "school_code": credentials["school_code"],
            "username": credentials["username"],
            "password": credentials["password"],
            "grade": grade,
        }
        return self._post_json("/api/fetch_students", payload)


def apply_cloud_records_to_table(
    table_inner_frame, records, subjects, columns_per_subject=3
):
    # 1. Map cloud data for easy lookup
    record_map = {
        "".join(r.get("student_name", "").split()).lower(): r for r in records
    }

    # 2. Get all widgets and group them by row
    all_widgets = table_inner_frame.winfo_children()
    rows = {}

    for w in all_widgets:
        info = w.grid_info()
        r_idx = info.get("row")
        if r_idx is not None and r_idx >= 2:  # Skip the 2 header rows
            if r_idx not in rows:
                rows[r_idx] = []
            rows[r_idx].append(w)

    filled_count = 0

    # 3. Process each row
    for r_idx in sorted(rows.keys()):
        widgets = sorted(rows[r_idx], key=lambda w: w.grid_info().get("column", 0))

        # In your Junior UI, Column 0 is the Name Label
        name_widget = widgets[0]

        # If it's a CTkFrame (from the 'Fixed Row Alignment' fix), get the label inside it
        if hasattr(name_widget, "winfo_children") and name_widget.winfo_children():
            name_label = name_widget.winfo_children()[0]
            try:
                raw_name = name_label.cget("text")
            except:
                continue
        else:
            try:
                raw_name = name_widget.cget("text")
            except:
                continue

        clean_local_name = "".join(str(raw_name).split()).lower()
        record = record_map.get(clean_local_name)

        if record:
            scores = record.get("scores", {})

            # Highlight name to show sync worked
            try:
                name_widget.configure(fg_color="#1e3a24")  # Dark green background
            except:
                pass

            for i, subject in enumerate(subjects):
                # Match subject names flexibly
                val_data = None
                clean_sub = subject.strip().lower()
                for cloud_key in scores.keys():
                    if clean_sub in cloud_key.lower() or cloud_key.lower() in clean_sub:
                        val_data = scores[cloud_key]
                        break

                # Extract values
                if isinstance(val_data, dict):
                    vals = [
                        val_data.get("score", ""),
                        val_data.get("rating", ""),
                        val_data.get("points", ""),
                    ]
                else:
                    vals = [val_data if val_data is not None else "", "", ""]

                # Target the correct entry boxes
                # Column 0 = Name, 1-3 = Subj1, 4-6 = Subj2...
                base_col = 1 + (i * columns_per_subject)

                for offset in range(columns_per_subject):
                    target_col = base_col + offset
                    # Find the widget sitting in this specific column
                    for w in widgets:
                        if int(w.grid_info().get("column")) == target_col:
                            if hasattr(w, "delete"):
                                curr_state = w.cget("state")
                                w.configure(state="normal")
                                w.delete(0, "end")
                                w.insert(0, str(vals[offset]))
                                w.configure(state=curr_state)
                            break

            filled_count += 1
            print(f"✅ Sync Successful: {raw_name}")

    return True
