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


def apply_cloud_records_to_table(table_frame, records, subjects, columns_per_subject=3):
    """
    Synchronizes cloud data into the local Tkinter table.
    - Junior School: columns_per_subject=3 (Score, Rating, Points)
    - Primary/Lower: columns_per_subject=2 (Score, Rating)
    """
    # 1. Map cloud data using a 'Normalized' name (no spaces, all lowercase)
    # This prevents mismatches due to accidental double spaces or casing.
    record_map = {
        "".join(r.get("student_name", "").split()).lower(): r for r in records
    }
    filled_count = 0

    # Header/System labels to ignore if found in the first column
    ignore_list = [
        "studentname",
        "math",
        "eng",
        "kisw",
        "s",
        "r",
        "p",
        "tot",
        "avg",
        "rank",
    ]

    for row_frame in table_frame.winfo_children():
        if not hasattr(row_frame, "winfo_children"):
            continue

        # Get all widgets in the row and sort them strictly by column index
        widgets = row_frame.winfo_children()
        if not widgets:
            continue

        widgets.sort(key=lambda w: w.grid_info().get("column", 0))
        num_widgets = len(widgets)

        try:
            # 1. Find the first widget in the row that actually has a 'text' attribute
            # This skips over frames, canvases, or spacers that were causing the crash.
            name_widget = None
            raw_text = ""

            for w in widgets:
                # Check if the widget supports the 'text' option
                # Most CustomTkinter text widgets (Labels, Buttons) have this.
                try:
                    raw_text = w.cget("text")
                    name_widget = w
                    break  # Found it! Stop looking at other widgets in this row.
                except:
                    continue  # Not a text widget, try the next one

            if not name_widget:
                continue

            # 2. Normalize the text for matching
            clean_local_name = "".join(str(raw_text).split()).lower()

            # Skip header rows, empty rows, or system keywords
            if not clean_local_name or clean_local_name in ignore_list:
                continue

            # 3. Match against the Cloud Map
            record = record_map.get(clean_local_name)
            if not record:
                # Use this to see what the app is seeing vs what you expect
                # print(f"DEBUG: No Cloud match for: '{clean_local_name}'")
                continue

            # SUCCESS: Match found!
            # Turn the name green so we know the UI is active.
            name_widget.configure(text_color="#2ecc71")
            filled_count += 1

        except Exception as e:
            # Catch-all for unexpected UI structure issues
            print(f"DEBUG: Row Error: {e}")
            continue

        # 4. Helper function to handle writing to Entry widgets safely
        def safe_write(idx, val):
            if idx < num_widgets:
                w = widgets[idx]
                # Check if widget is a text-entry type (Entry or CTkEntry)
                if hasattr(w, "delete") and hasattr(w, "insert"):
                    if "label" not in str(w).lower():
                        try:
                            # Force state to normal to ensure we can write
                            current_state = w.cget("state")
                            w.configure(state="normal")

                            w.delete(0, "end")
                            w.insert(0, str(val) if val is not None else "")

                            # Restore original state (readonly/disabled/normal)
                            w.configure(state=current_state)
                        except:
                            pass

        # 5. Fill subject scores
        scores = record.get("scores", {})
        for i, subject in enumerate(subjects):
            sub_data = scores.get(subject, {})

            # Extract data regardless of whether cloud format is nested or flat
            if isinstance(sub_data, dict):
                score_val = sub_data.get("score", "")
                rating_val = sub_data.get("rating", "")
                point_val = sub_data.get("points", "")
            else:
                score_val = sub_data
                rating_val = ""
                point_val = ""

            # Standard positioning logic: Name is index 0, so subjects start at index 1
            base_idx = 1 + (i * columns_per_subject)

            safe_write(base_idx, score_val)
            safe_write(base_idx + 1, rating_val)
            if columns_per_subject == 3:
                safe_write(base_idx + 2, point_val)

        # 6. Update Totals and Averages (usually at the end of the row)
        # Using negative indexing to count back from the right side
        safe_write(num_widgets - 3, record.get("total_points", ""))
        safe_write(num_widgets - 2, record.get("average_level", ""))

    print(f"TERMINAL: Successfully updated {filled_count} students.")
    return True
