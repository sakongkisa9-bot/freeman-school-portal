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

    def consume_marks(self, grade, credentials):
        """Delete marks from cloud after they've been fetched (consume operation)"""
        payload = {
            "school_code": credentials["school_code"],
            "username": credentials["username"],
            "password": credentials["password"],
            "grade": grade,
        }
        return self._post_json("/api/consume_marks", payload)

    def toggle_portal(self, credentials):
        """Toggle the cloud portal open/closed state"""
        if not self._ensure_requests():
            return {"success": False, "message": "Requests library not installed."}

        try:
            url = f"{self.base_url}/api/toggle_portal"
            # Need to authenticate with session first
            login_url = f"{self.base_url}/teacher/login"
            login_data = {
                "school_code": credentials["school_code"],
                "username": credentials["username"],
                "password": credentials["password"],
            }

            # Login to get session (use form data, not JSON)
            login_response = self.session.post(login_url, data=login_data, timeout=20, allow_redirects=False)
            if login_response.status_code not in (302, 200):
                return {"success": False, "message": f"Authentication failed: Status {login_response.status_code}"}

            # Now toggle portal
            response = self.session.post(url, timeout=20)
            if response.status_code != 200:
                return {"success": False, "message": f"Status: {response.status_code}, Response: {response.text}"}

            return response.json()
        except Exception as e:
            return {"success": False, "message": f"Connection Failed: {e}"}


def apply_cloud_records_to_table(
    table_inner_frame, records, subjects, columns_per_subject=3
):
    # DEBUG: Print incoming data
    print(f"DEBUG: apply_cloud_records_to_table called")
    print(f"DEBUG: Number of records from cloud: {len(records)}")
    print(f"DEBUG: Subjects: {subjects}")
    print(f"DEBUG: Columns per subject: {columns_per_subject}")
    
    # 1. Map cloud data for easy lookup
    record_map = {
        "".join(r.get("student_name", "").split()).lower(): r for r in records
    }
    print(f"DEBUG: Record map keys: {list(record_map.keys())}")

    # 2. Get all widgets and group them by row
    # For junior marksheet with row_frames, we need to handle nested structure
    rows = {}
    
    # First, get direct children of table_inner_frame
    direct_children = table_inner_frame.winfo_children()
    print(f"DEBUG: Direct children found: {len(direct_children)}")
    
    # Check if widgets are packed (PP2 style) or gridded (Junior style)
    has_grid_info = False
    for child in direct_children:
        info = child.grid_info()
        if info.get("row") is not None:
            has_grid_info = True
            break
    
    if has_grid_info:
        # Grid-based layout (Junior marksheet)
        for child in direct_children:
            info = child.grid_info()
            r_idx = info.get("row")
            
            # Skip header rows (0 and 1)
            if r_idx is None or r_idx < 2:
                continue
                
            if r_idx not in rows:
                rows[r_idx] = []
            
            # If this is a row_frame (has children), add its internal widgets
            if hasattr(child, "winfo_children") and child.winfo_children():
                # Add the row_frame itself (for name extraction)
                rows[r_idx].append(child)
                # Add all internal widgets
                for internal_widget in child.winfo_children():
                    rows[r_idx].append(internal_widget)
            else:
                # Direct widget (for PP1 style)
                rows[r_idx].append(child)
    else:
        # Pack-based layout (PP2 marksheet) - assign row indices based on order
        row_idx = 2  # Start after header rows
        for child in direct_children:
            # Skip header frames
            if hasattr(child, "winfo_children"):
                widgets_in_child = child.winfo_children()
                if widgets_in_child:
                    # Check if this looks like a header (has "STUDENT NAME" label)
                    is_header = False
                    for w in widgets_in_child:
                        try:
                            if w.cget("text") == "STUDENT NAME":
                                is_header = True
                                break
                        except:
                            continue
                    if is_header:
                        continue
                    
                    # This is a data row
                    if row_idx not in rows:
                        rows[row_idx] = []
                    rows[row_idx].append(child)
                    # Add all internal widgets
                    for internal_widget in widgets_in_child:
                        rows[row_idx].append(internal_widget)
                    row_idx += 1
    
    print(f"DEBUG: Rows detected: {list(rows.keys())}")
    print(f"DEBUG: Total widgets in rows: {sum(len(w) for w in rows.values())}")

    filled_count = 0

    # 3. Process each row
    for r_idx in sorted(rows.keys()):
        widgets = sorted(rows[r_idx], key=lambda w: w.grid_info().get("column", 0))
        print(f"DEBUG: Processing row {r_idx}, widgets: {len(widgets)}")
        
        # Print column numbers of all widgets for debugging
        col_numbers = []
        for w in widgets:
            col = w.grid_info().get("column")
            col_numbers.append(col)
        print(f"DEBUG: Row {r_idx} widget columns: {col_numbers}")

        # In your Junior UI, Column 0 is the Name Label
        name_widget = widgets[0]

        # If it's a CTkFrame (from the 'Fixed Row Alignment' fix), get the label inside it
        if hasattr(name_widget, "winfo_children") and name_widget.winfo_children():
            # For junior marksheet, find the label widget inside the row_frame
            name_label = None
            for child in name_widget.winfo_children():
                # Try to get text from any widget that supports it
                try:
                    raw_name = child.cget("text")
                    name_label = child
                    break
                except:
                    continue
            if name_label:
                try:
                    raw_name = name_label.cget("text")
                except:
                    print(f"DEBUG: Row {r_idx} - Could not get text from label")
                    continue
            else:
                print(f"DEBUG: Row {r_idx} - No name label found in row_frame")
                continue
        else:
            try:
                raw_name = name_widget.cget("text")
            except:
                print(f"DEBUG: Row {r_idx} - Could not get text from name_widget")
                continue

        clean_local_name = "".join(str(raw_name).split()).lower()
        print(f"DEBUG: Row {r_idx} - Local name: '{raw_name}' -> Cleaned: '{clean_local_name}'")
        record = record_map.get(clean_local_name)
        print(f"DEBUG: Row {r_idx} - Match found: {record is not None}")

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
                        col = w.grid_info().get("column")
                        if col is not None and int(col) == target_col:
                            if hasattr(w, "delete"):
                                curr_state = w.cget("state")
                                w.configure(state="normal")
                                w.delete(0, "end")
                                w.insert(0, str(vals[offset]))
                                w.configure(state=curr_state)
                            break

            # Fill in total_points and average_level in the summary columns
            total_points = record.get("total_points", "0")
            average_level = record.get("average_level", "")
            
            # Summary columns start after all subject columns
            total_start_col = 1 + (len(subjects) * columns_per_subject)
            print(f"DEBUG: Filling totals for {raw_name}, total_start_col={total_start_col}, total_points={total_points}, avg_level={average_level}")
            
            # Fill total_points column
            tot_found = False
            for w in widgets:
                col = w.grid_info().get("column")
                if col is not None and int(col) == total_start_col:
                    if hasattr(w, "delete"):
                        curr_state = w.cget("state")
                        w.configure(state="normal")
                        w.delete(0, "end")
                        w.insert(0, str(total_points))
                        w.configure(state=curr_state)
                        tot_found = True
                        print(f"DEBUG: Filled total_points at column {col}")
                    break
            if not tot_found:
                print(f"DEBUG: Could not find widget at column {total_start_col} for total_points")
            
            # Fill average_level column
            avg_found = False
            for w in widgets:
                col = w.grid_info().get("column")
                if col is not None and int(col) == total_start_col + 1:
                    # Handle both Entry and Label widgets
                    if hasattr(w, "delete"):
                        # Entry widget
                        curr_state = w.cget("state")
                        w.configure(state="normal")
                        w.delete(0, "end")
                        w.insert(0, str(average_level))
                        w.configure(state=curr_state)
                        avg_found = True
                        print(f"DEBUG: Filled average_level (Entry) at column {col}")
                    elif hasattr(w, "configure"):
                        # Label widget
                        w.configure(text=str(average_level))
                        avg_found = True
                        print(f"DEBUG: Filled average_level (Label) at column {col}")
                    break
            if not avg_found:
                print(f"DEBUG: Could not find widget at column {total_start_col + 1} for average_level")

            filled_count += 1
            print(f"✅ Sync Successful: {raw_name}")

    return True
