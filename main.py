# main.py
import os
import sys
import logging
from datetime import datetime

# Setup logging to file BEFORE any other imports
def setup_logging():
    """Setup logging to file for debugging executable behavior"""
    try:
        # Determine log file location
        if getattr(sys, 'frozen', False):
            # Running as executable
            log_dir = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
        else:
            # Running as script
            log_dir = os.path.dirname(os.path.realpath(__file__))

        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "freeman_portal_log.txt")

        # Clear previous log file on new run
        if os.path.exists(log_file):
            try:
                os.remove(log_file)
            except:
                pass

        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, mode='w'),
                logging.StreamHandler(sys.stdout)
            ]
        )

        logging.info("=" * 80)
        logging.info("FREEMAN SCHOOL PORTAL - STARTING")
        logging.info("=" * 80)
        logging.info(f"Python Version: {sys.version}")
        logging.info(f"Executable Mode: {getattr(sys, 'frozen', False)}")
        logging.info(f"Working Directory: {os.getcwd()}")

        if getattr(sys, 'frozen', False):
            logging.info(f"sys._MEIPASS: {sys._MEIPASS}")
            logging.info(f"Executable Path: {sys.executable}")

        logging.info(f"Log File: {log_file}")
        logging.info("=" * 80)

        return log_file
    except Exception as e:
        print(f"Error setting up logging: {e}")
        return None

# Setup logging immediately
log_file = setup_logging()
logging.info("Logging initialized successfully")

# Import file_loader FIRST to set up user data directory and sys.path
try:
    from file_loader import get_app_directories, initialize_user_data_files, sync_updated_files
    logging.info("file_loader imported successfully")
except Exception as e:
    logging.error(f"Error importing file_loader: {e}")
    import traceback
    logging.error(traceback.format_exc())
    sys.exit(1)

# Initialize user data files and sync updated files BEFORE any other imports
try:
    logging.info("Initializing user data files...")
    initialize_user_data_files()
    logging.info("User data files initialized")

    logging.info("Syncing updated files...")
    sync_updated_files()
    logging.info("Updated files synced")
except Exception as e:
    logging.error(f"Error initializing file_loader functions: {e}")
    import traceback
    logging.error(traceback.format_exc())

# Add user data directory to Python path for updated modules
# This MUST happen before importing any application modules
if getattr(sys, 'frozen', False):
    logging.info("Running in executable mode - setting up sys.path")
    _, user_data_dir = get_app_directories()
    logging.info(f"User data directory: {user_data_dir}")

    if user_data_dir not in sys.path:
        sys.path.insert(0, user_data_dir)
        logging.info(f"Added {user_data_dir} to sys.path at position 0")

    # Check for update pending flag
    backup_dir = os.path.join(user_data_dir, "backup")
    flag_file = os.path.join(backup_dir, "update_pending.flag")
    update_pending = os.path.exists(flag_file)

    if update_pending:
        logging.info("Update pending detected - will prioritize user data modules")
        # Clean up the flag file
        try:
            os.remove(flag_file)
            logging.info("Removed update_pending.flag")
        except Exception as e:
            logging.error(f"Error removing flag file: {e}")

    # Log which updated modules will be prioritized
    critical_modules = [
        'update_manager',
        'ui_dashboard',
        'security',
        'license_manager',
        'database',
        'grading_logic',
        'cloud_service',
        'notification_service',
        'fcm_service',
        'mpesa_service',
        'reportforms',
        'wizard'
    ]

    logging.info("Checking for updated modules in user data directory:")
    for module_name in critical_modules:
        module_file = f"{module_name}.py"
        user_module_path = os.path.join(user_data_dir, module_file)
        if os.path.exists(user_module_path):
            status = "UPDATE PENDING" if update_pending else "UPDATED"
            logging.info(f"  Found {status} {module_name} in user data, will load from there")
        else:
            logging.info(f"  {module_name} not in user data, will load from bundled")
else:
    logging.info("Running in development mode")

# Now import other modules after path is set up
try:
    logging.info("Importing customtkinter...")
    import customtkinter as ctk
    logging.info("customtkinter imported successfully")
except Exception as e:
    logging.error(f"Error importing customtkinter: {e}")
    import traceback
    logging.error(traceback.format_exc())

try:
    logging.info("Importing PIL...")
    from PIL import Image
    logging.info("PIL imported successfully")
except Exception as e:
    logging.error(f"Error importing PIL: {e}")

import random
import json

try:
    logging.info("Importing license_manager...")
    from license_manager import check_and_activate_license
    logging.info("license_manager imported successfully")
except Exception as e:
    logging.error(f"Error importing license_manager: {e}")

try:
    logging.info("Importing security...")
    import security
    logging.info("security imported successfully")
except Exception as e:
    logging.error(f"Error importing security: {e}")

# LICENSE CHECK - Must pass before application can start
def check_license_before_start():
    """Check license validity before allowing application to start"""
    is_allowed, message = check_and_activate_license()
    
    if not is_allowed:
        # Show error dialog and exit
        root = ctk.CTk()
        root.title("License Error")
        root.geometry("600x400")
        
        # Center the window
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (600 // 2)
        y = (screen_height // 2) - (400 // 2)
        root.geometry(f"600x400+{x}+{y}")
        root.resizable(False, False)
        
        # Error message frame
        frame = ctk.CTkFrame(root)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Error icon/text
        ctk.CTkLabel(frame, text="⚠️ LICENSE ERROR", font=("Arial Bold", 24), 
                   text_color="#e74c3c").pack(pady=(20, 10))
        
        # Error message
        msg_label = ctk.CTkLabel(frame, text=message, font=("Arial", 12), 
                                wraplength=500, justify="center")
        msg_label.pack(pady=20)
        
        # Exit button
        ctk.CTkButton(frame, text="Exit", command=root.destroy, 
                     width=150, height=40, fg_color="#e74c3c").pack(pady=20)
        
        root.mainloop()
        sys.exit(1)
    
    # Check if system is locked due to payment
    if check_system_payment_lock():
        return show_payment_dialog()

    return True


def check_system_payment_lock():
    """Check if system is locked due to payment requirements"""
    try:
        # Handle both development and executable environments
        if getattr(sys, 'frozen', False):
            USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
        else:
            USER_DATA_DIR = os.path.dirname(os.path.realpath(__file__))
        
        db_path = os.path.join(USER_DATA_DIR, "freeman_school.db")
        
        if not os.path.exists(db_path):
            return False
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if payment_settings table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='payment_settings'
        """)
        if not cursor.fetchone():
            conn.close()
            return False
        
        # Check if system is locked
        cursor.execute("SELECT system_locked FROM payment_settings ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] == 1:
            return True
        
    except Exception as e:
        print(f"Error checking payment lock: {e}")
    
    return False


def show_payment_dialog():
    """Show payment dialog with two options when system is locked"""
    try:
        # Handle both development and executable environments
        if getattr(sys, 'frozen', False):
            USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
        else:
            USER_DATA_DIR = os.path.dirname(os.path.realpath(__file__))
        
        db_path = os.path.join(USER_DATA_DIR, "freeman_school.db")
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get payment settings
        cursor.execute("SELECT * FROM payment_settings ORDER BY id DESC LIMIT 1")
        payment_settings = cursor.fetchone()
        
        # Get student count
        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0]
        
        # Get paid students count
        cursor.execute("SELECT COUNT(DISTINCT adm_no) FROM student_payments WHERE payment_status = 'paid'")
        paid_students = cursor.fetchone()[0]
        
        conn.close()
        
        if not payment_settings:
            return True  # No payment settings, allow access
        
        full_amount = payment_settings[1]  # full_payment_amount
        payment_percentage = payment_settings[2]  # payment_percentage
        partial_amount = full_amount * (payment_percentage / 100)
        
        # Create payment dialog
        root = ctk.CTk()
        root.title("Payment Required")
        root.geometry("700x600")
        
        # Center the window
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (700 // 2)
        y = (screen_height // 2) - (600 // 2)
        root.geometry(f"700x600+{x}+{y}")
        root.resizable(False, False)
        
        # Main frame
        main_frame = ctk.CTkFrame(root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        ctk.CTkLabel(main_frame, text="💳 PAYMENT REQUIRED", font=("Arial Bold", 28), 
                   text_color="#2c3e50").pack(pady=(20, 10))
        
        # Status info
        status_frame = ctk.CTkFrame(main_frame, fg_color="#ecf0f1")
        status_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(status_frame, text=f"Total Students: {total_students}", 
                   font=("Arial", 12)).pack(pady=5)
        ctk.CTkLabel(status_frame, text=f"Paid Students: {paid_students}", 
                   font=("Arial", 12), text_color="#27ae60").pack(pady=5)
        ctk.CTkLabel(status_frame, text=f"Unpaid Students: {total_students - paid_students}", 
                   font=("Arial", 12), text_color="#e74c3c").pack(pady=5)
        
        # Payment options frame
        options_frame = ctk.CTkFrame(main_frame)
        options_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Full payment option frame
        full_frame = ctk.CTkFrame(options_frame, fg_color="#3498db", border_width=2)
        full_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(full_frame, text="FULL PAYMENT (100%)", font=("Arial Bold", 18), 
                   text_color="white").pack(pady=(15, 5))
        ctk.CTkLabel(full_frame, text=f"KES {full_amount:.2f}", font=("Arial Bold", 24), 
                   text_color="white").pack(pady=5)
        ctk.CTkLabel(full_frame, text="Pay full amount to unlock system for all students", 
                   font=("Arial", 11), text_color="#ecf0f1").pack(pady=(5, 15))
        
        ctk.CTkButton(full_frame, text="PAY NOW", command=lambda: show_phone_entry('full', full_amount),
                     fg_color="white", hover_color="#ecf0f1", text_color="#3498db", 
                     width=150, height=40, font=("Arial Bold", 14)).pack(pady=(5, 15))
        
        # 70% payment option frame
        partial_frame = ctk.CTkFrame(options_frame, fg_color="#9b59b6", border_width=2)
        partial_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(partial_frame, text=f"70% PAYMENT OPTION", font=("Arial Bold", 18), 
                   text_color="white").pack(pady=(15, 5))
        ctk.CTkLabel(partial_frame, text=f"KES {partial_amount:.2f}", font=("Arial Bold", 24), 
                   text_color="white").pack(pady=5)
        ctk.CTkLabel(partial_frame, text="Pay 70% now, select students for partial access", 
                   font=("Arial", 11), text_color="#ecf0f1").pack(pady=(5, 15))
        
        ctk.CTkButton(partial_frame, text="PAY NOW", command=lambda: show_phone_entry('partial', partial_amount),
                     fg_color="white", hover_color="#ecf0f1", text_color="#9b59b6", 
                     width=150, height=40, font=("Arial Bold", 14)).pack(pady=(5, 15))
        
        def show_phone_entry(payment_type, amount):
            """Show phone number entry dialog"""
            phone_dialog = ctk.CTkToplevel(root)
            phone_dialog.title("Enter Phone Number")
            phone_dialog.geometry("500x400")
            
            # Center the window
            screen_width = phone_dialog.winfo_screenwidth()
            screen_height = phone_dialog.winfo_screenheight()
            x = (screen_width // 2) - (500 // 2)
            y = (screen_height // 2) - (400 // 2)
            phone_dialog.geometry(f"500x400+{x}+{y}")
            phone_dialog.resizable(False, False)
            phone_dialog.attributes("-topmost", True)
            phone_dialog.grab_set()
            
            # Main frame
            phone_main_frame = ctk.CTkFrame(phone_dialog)
            phone_main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            ctk.CTkLabel(phone_main_frame, text="Enter Phone Number", 
                       font=("Arial Bold", 20), text_color="#2c3e50").pack(pady=(20, 10))
            
            ctk.CTkLabel(phone_main_frame, text=f"Payment Amount: KES {amount:.2f}", 
                       font=("Arial", 14), text_color="#7f8c8d").pack(pady=5)
            
            ctk.CTkLabel(phone_main_frame, text="Payment Type: " + payment_type.upper(), 
                       font=("Arial", 14), text_color="#7f8c8d").pack(pady=5)
            
            ctk.CTkLabel(phone_main_frame, text="Phone Number:", 
                       font=("Arial", 12, "bold")).pack(pady=(20, 5))
            
            phone_entry = ctk.CTkEntry(phone_main_frame, width=300, placeholder_text="e.g., 0712345678")
            phone_entry.pack(pady=5)
            
            def process_payment_with_phone():
                phone_number = phone_entry.get().strip()
                
                if not phone_number:
                    messagebox.showerror("Error", "Please enter a phone number")
                    return
                
                if len(phone_number) < 10:
                    messagebox.showerror("Error", "Please enter a valid phone number (at least 10 digits)")
                    return
                
                # Save phone number with payment settings
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Update payment settings with phone number
                cursor.execute("""
                    UPDATE payment_settings 
                    SET phone_number = ?
                    WHERE id = (SELECT id FROM payment_settings ORDER BY id DESC LIMIT 1)
                """, (phone_number,))
                
                conn.commit()
                conn.close()
                
                phone_dialog.destroy()
                
                # Process the payment based on type
                if payment_type == 'full':
                    process_full_payment()
                else:
                    process_partial_payment()
            
            def process_full_payment():
                # Mark all students as paid with full payment
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT adm_no, name FROM students")
                students = cursor.fetchall()
                
                for adm_no, name in students:
                    cursor.execute("""
                        INSERT OR REPLACE INTO student_payments 
                        (adm_no, student_name, payment_type, amount_paid, payment_status)
                        VALUES (?, ?, ?, ?, 'paid')
                    """, (adm_no, name, 'full', full_amount))
                
                # Unlock system
                cursor.execute("UPDATE payment_settings SET system_locked = 0")
                conn.commit()
                conn.close()
                
                root.destroy()
            
            def process_partial_payment():
                # Calculate how many students get 70% payment
                unpaid_students = total_students - paid_students
                partial_payment_count = int(unpaid_students * (payment_percentage / 100))
                
                root.destroy()
                # Show student selection dialog
                show_student_selection_dialog(db_path, partial_payment_count, full_amount, payment_percentage)
            
            # Buttons
            phone_buttons_frame = ctk.CTkFrame(phone_main_frame, fg_color="transparent")
            phone_buttons_frame.pack(pady=20)
            
            ctk.CTkButton(phone_buttons_frame, text="Confirm Payment", command=process_payment_with_phone,
                         fg_color="#27ae60", hover_color="#219a52", width=150, height=50,
                         font=("Arial Bold", 14)).pack(side="left", padx=5)
            
            ctk.CTkButton(phone_buttons_frame, text="Cancel", command=phone_dialog.destroy,
                         fg_color="#e74c3c", hover_color="#c0392b", width=100, height=50,
                         font=("Arial Bold", 14)).pack(side="left", padx=5)
        
        root.mainloop()
        
        # After dialog closes, check if system is still locked
        return not check_system_payment_lock()
        
    except Exception as e:
        print(f"Error showing payment dialog: {e}")
        return True  # Allow access on error


def show_student_selection_dialog(db_path, required_count, full_amount, payment_percentage):
    """Show dialog to select students for 70% payment option"""
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get unpaid students
    cursor.execute("""
        SELECT adm_no, name, grade FROM students 
        WHERE adm_no NOT IN (SELECT DISTINCT adm_no FROM student_payments WHERE payment_status = 'paid')
    """)
    unpaid_students = cursor.fetchall()
    
    conn.close()
    
    # Create selection dialog
    root = ctk.CTk()
    root.title("Select Students for 70% Payment")
    root.geometry("800x600")
    
    # Center the window
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (800 // 2)
    y = (screen_height // 2) - (600 // 2)
    root.geometry(f"800x600+{x}+{y}")
    root.resizable(False, False)
    
    # Main frame
    main_frame = ctk.CTkFrame(root)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Title
    ctk.CTkLabel(main_frame, text="SELECT STUDENTS FOR 70% PAYMENT", 
               font=("Arial Bold", 20), text_color="#2c3e50").pack(pady=(20, 10))
    
    ctk.CTkLabel(main_frame, text=f"Select exactly {required_count} students for 70% payment", 
               font=("Arial", 12), text_color="#e67e22").pack(pady=5)
    
    ctk.CTkLabel(main_frame, text=f"Remaining {len(unpaid_students) - required_count} students will pay via 'Pay for Remaining Students' button",
               font=("Arial", 12), text_color="#27ae60").pack(pady=5)
    
    # Scrollable frame for student list
    from customtkinter import CTkScrollableFrame
    scroll_frame = CTkScrollableFrame(main_frame, height=400)
    scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
    
    student_checkboxes = {}
    
    # Create checkboxes for each student
    for adm_no, name, grade in unpaid_students:
        checkbox_var = ctk.BooleanVar()
        checkbox = ctk.CTkCheckBox(
            scroll_frame,
            text=f"{name} (ADM: {adm_no}) - {grade}",
            variable=checkbox_var
        )
        checkbox.pack(pady=5, anchor="w")
        student_checkboxes[adm_no] = checkbox_var
    
    # Selection counter
    counter_label = ctk.CTkLabel(main_frame, text=f"Selected: 0 / {required_count}", 
                                font=("Arial Bold", 14))
    counter_label.pack(pady=10)
    
    def update_counter():
        selected_count = sum(1 for var in student_checkboxes.values() if var.get())
        counter_label.configure(text=f"Selected: {selected_count} / {required_count}")
    
    # Bind checkbox changes to counter
    for var in student_checkboxes.values():
        var.trace_add("write", lambda *args: update_counter())
    
    # Buttons frame
    buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    buttons_frame.pack(pady=20)
    
    def confirm_selection():
        selected_count = sum(1 for var in student_checkboxes.values() if var.get())
        
        if selected_count != required_count:
            messagebox.showerror(
                "Error",
                f"Please select exactly {required_count} students for 70% payment.\n"
                f"Currently selected: {selected_count}"
            )
            return
        
        # Get selected students
        selected_adm_nos = [
            adm_no for adm_no, var in student_checkboxes.items() if var.get()
        ]
        
        # Save payment records
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        partial_amount = full_amount * (payment_percentage / 100)
        
        # Save 70% payment for selected students (status = pending - they can't view reports)
        for adm_no in selected_adm_nos:
            student_info = next((s for s in unpaid_students if s[0] == adm_no), None)
            if student_info:
                cursor.execute("""
                    INSERT OR REPLACE INTO student_payments
                    (adm_no, student_name, payment_type, amount_paid, payment_status)
                    VALUES (?, ?, ?, ?, 'pending')
                """, (adm_no, student_info[1], 'partial', partial_amount))

        # NOTE: Remaining students do NOT get payment records yet
        # They will need to pay via "Pay for Remaining Students" button
        
        # Unlock system
        cursor.execute("UPDATE payment_settings SET system_locked = 0")
        conn.commit()
        conn.close()
        
        # Send FCM notifications
        send_payment_notifications(selected_adm_nos, partial_amount, full_amount, db_path)
        
        messagebox.showinfo(
            "Success",
            f"Payment configuration saved!\n\n"
            f"{required_count} students assigned to 70% payment (pending)\n"
            f"{len(unpaid_students) - required_count} students will need to pay via 'Pay for Remaining Students' button\n\n"
            f"System is now unlocked. Selected students cannot view reports until payment is completed."
        )
        
        root.destroy()
    
    def cancel():
        root.destroy()
        sys.exit(1)
    
    ctk.CTkButton(buttons_frame, text="Confirm Selection", command=confirm_selection,
                 fg_color="#27ae60", hover_color="#219a52", width=150, height=50,
                 font=("Arial Bold", 14)).pack(side="left", padx=5)
    
    ctk.CTkButton(buttons_frame, text="Cancel", command=cancel,
                 fg_color="#e74c3c", hover_color="#c0392b", width=100, height=50,
                 font=("Arial Bold", 14)).pack(side="left", padx=5)
    
    root.mainloop()


def send_payment_notifications(partial_students, partial_amount, full_amount, db_path):
    """Send FCM notifications to parents"""
    try:
        from fcm_service import get_fcm_service
        
        fcm_service = get_fcm_service()
        
        if not fcm_service.is_available():
            return
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Send notifications to partial payment students
        for adm_no in partial_students:
            cursor.execute("""
                SELECT token FROM fcm_tokens 
                WHERE student_id = (SELECT id FROM students WHERE adm_no = ?)
            """, (adm_no,))
            tokens = cursor.fetchall()
            
            for (token,) in tokens:
                fcm_service.send_notification(
                    token=token,
                    title="Payment Required - 70% Option",
                    body=f"Your child is eligible for 70% payment option. Amount: KES {partial_amount:.2f}",
                    data={"payment_type": "partial", "amount": str(partial_amount)}
                )
        
        # Send notifications to full payment students
        cursor.execute("""
            SELECT adm_no FROM students 
            WHERE adm_no NOT IN ({})
        """.format(','.join(['?'] * len(partial_students))), partial_students)
        
        full_payment_students_list = cursor.fetchall()
        
        for (adm_no,) in full_payment_students_list:
            cursor.execute("""
                SELECT token FROM fcm_tokens 
                WHERE student_id = (SELECT id FROM students WHERE adm_no = ?)
            """, (adm_no,))
            tokens = cursor.fetchall()
            
            for (token,) in tokens:
                fcm_service.send_notification(
                    token=token,
                    title="Payment Required - Full Payment",
                    body=f"Full payment required: KES {full_amount:.2f}",
                    data={"payment_type": "full", "amount": str(full_amount)}
                )
        
        conn.close()
        
    except Exception as e:
        print(f"Error sending notifications: {e}")


def check_terms_agreement():
    """Check if user has agreed to Terms of Use"""
    try:
        # Handle both development and executable environments
        if getattr(sys, 'frozen', False):
            USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
        else:
            USER_DATA_DIR = os.path.dirname(os.path.realpath(__file__))
        
        config_path = os.path.join(USER_DATA_DIR, "school_config.json")
        
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                # Check if terms have been accepted and version matches
                current_terms_version = "1.0"
                accepted_version = config.get("terms_accepted_version", "")
                if accepted_version == current_terms_version:
                    return True
    except:
        pass
    
    return False


def show_terms_dialog():
    """Show Terms of Use agreement dialog"""
    dialog = ctk.CTk()
    dialog.title("Terms of Use Agreement")
    dialog.geometry("800x600")
    
    # Center the window
    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()
    x = (screen_width // 2) - (800 // 2)
    y = (screen_height // 2) - (600 // 2)
    dialog.geometry(f"800x600+{x}+{y}")
    dialog.resizable(False, False)
    
    # Main frame
    main_frame = ctk.CTkFrame(dialog)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Title
    ctk.CTkLabel(main_frame, text="TERMS OF USE", font=("Arial Bold", 24), 
                text_color="#2c3e50").pack(pady=(10, 20))
    
    # Scrollable text area for terms
    from customtkinter import CTkScrollableFrame
    scroll_frame = CTkScrollableFrame(main_frame, width=700, height=350)
    scroll_frame.pack(fill="both", expand=True, pady=(0, 20))
    
    terms_text = """
1. OWNERSHIP AND INTELLECTUAL PROPERTY
This software (the "School management system") is the sole and exclusive property of Freeman-Tech Solutions. The School acknowledges that it is being granted a limited, non-exclusive, non-transferable, and revocable license to use the System for its internal academic management purposes. The School does not acquire any ownership interest, title, or rights in the System.

2. RESTRICTIONS AND PROHIBITED USE
The School shall not, and shall not permit any third party to:
• Decompile, disassemble, reverse-engineer, or attempt to derive the source code or underlying logic of the System.
• Modify, adapt, or create derivative works based on the System.
• Rent, lease, sublicense, or distribute the System to any other school or entity. Any attempt to bypass security features, license keys, or update mechanisms will result in the immediate termination of this license.

3. TRIAL PERIOD AND LICENSING
• Trial Period: A School may be granted a Free Trial period. If the System is installed during an academic term, the Free Trial shall remain active until the conclusion of that current academic term.
• Transition to Premium: Upon the conclusion of the Trial Period, the School must pay the agreed-upon Premium License Fee to maintain access to the System.
• Renewal: Failure to remit payment within 14 days of the start of the following term will result in the suspension of all system features, including cloud synchronization, report generation, and data export capabilities.

4. UPDATES, MAINTENANCE, AND SUPPORT
• Automatic Updates: The System may periodically connect to Freeman-Tech Solutions' servers to check for and apply updates, security patches, or feature enhancements. The School consents to these automatic updates to ensure continued functionality.
• Support Services: Basic support for system errors is included during the active license period. Major feature requests or personalized customizations outside the standard scope of the System are subject to separate negotiation and additional fees.
• Disclaimer: Freeman-Tech Solutions provides the System on an "as-is" basis and does not guarantee that access will be 100% uninterrupted.

5. LIMITATION OF LIABILITY
Freeman-Tech Solutions shall not be held liable for any data loss, administrative errors, or hardware issues resulting from the use of the System. The School is responsible for maintaining its own periodic backups of all academic data.

6. TERMINATION
This license remains in effect until terminated. Freeman-Tech Solutions reserves the right to terminate this license if the School fails to comply with any terms herein, specifically regarding payment or unauthorized redistribution. Upon termination, the School must cease all use of the System immediately.
"""
    
    terms_label = ctk.CTkLabel(scroll_frame, text=terms_text, font=("Arial", 11), 
                               justify="left", wraplength=650)
    terms_label.pack(pady=10, padx=10, anchor="w")
    
    # Checkbox for agreement
    agree_var = ctk.BooleanVar(value=False)
    checkbox = ctk.CTkCheckBox(main_frame, text="I have read and agree to the Terms of Use", 
                             variable=agree_var, font=("Arial", 12))
    checkbox.pack(pady=(0, 20))
    
    # Buttons
    button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    button_frame.pack(fill="x")
    
    def on_agree():
        if agree_var.get():
            # Save agreement to config
            try:
                if getattr(sys, 'frozen', False):
                    USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
                else:
                    USER_DATA_DIR = os.path.dirname(os.path.realpath(__file__))
                
                config_path = os.path.join(USER_DATA_DIR, "school_config.json")
                
                config = {}
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        config = json.load(f)
                
                config["terms_accepted_version"] = "1.0"
                config["terms_accepted_date"] = "2026-06-17"
                
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=4)
            except:
                pass
            
            dialog.destroy()
        else:
            ctk.CTkMessageBox.show_warning("Agreement Required", 
                                         "You must agree to the Terms of Use to continue.")
    
    def on_decline():
        ctk.CTkMessageBox.showinfo("Exit", "You must agree to the Terms of Use to use this software.")
        sys.exit(1)
    
    agree_btn = ctk.CTkButton(button_frame, text="I Agree", command=on_agree, 
                              width=150, height=40, fg_color="#27ae60", hover_color="#219150")
    agree_btn.pack(side="right", padx=5)
    
    decline_btn = ctk.CTkButton(button_frame, text="Decline", command=on_decline, 
                                width=150, height=40, fg_color="#e74c3c", hover_color="#c0392b")
    decline_btn.pack(side="right", padx=5)
    
    dialog.mainloop()

class SplashScreen(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. Window Setup
        self.overrideredirect(True)
        width, height = 600, 450 # Increased height slightly for the bar
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.geometry(f"{width}x{height}+{(screen_w-width)//2}+{(screen_h-height)//2}")
# --- NEW: Bottom Frame for Text and Bar ---
        # Change 'fg_color' to any color you want (e.g., "#2b2b2b", "gray10", or "blue")
        self.bottom_frame = ctk.CTkFrame(self, fg_color="#a232a8", corner_radius=0)
        self.bottom_frame.pack(fill="x", side="bottom")


        # 2. Assets & Status Messages
        self.assets_path = os.path.join(os.path.dirname(__file__), "assets")
        self.images = ["splash1.jpg", "splash2.jpg", "splash3.jpg"]
        self.status_messages = [
            "Initializing Freeman Engine...",
            "Loading Database...",
            "Checking Security Protocols...",
            "Syncing Grade Rubrics...",
            "Optimizing Dashboard...",
            "Finalizing Startup..."
        ]
        self.current_img_idx = 0
        self.progress_val = 0

        # 3. UI Elements
        # Image Display (Top Part)
        self.img_label = ctk.CTkLabel(self, text="")
        self.img_label.pack(expand=True, fill="both")

        # Status Text (Now inside bottom_frame)
        self.status_label = ctk.CTkLabel(self.bottom_frame, text="Starting...", font=("Arial", 14))
        self.status_label.pack(pady=(15, 5))

        # Loading Bar (Now inside bottom_frame)
        self.progress_bar = ctk.CTkProgressBar(self.bottom_frame, width=400, progress_color="#1f6aa5")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 10))

        # Percentage Label (Now inside bottom_frame)
        self.percentage_label = ctk.CTkLabel(self.bottom_frame, text="0%", font=("Arial Bold", 12))
        self.percentage_label.pack(pady=(0, 15))
        
        # 4. Start the logic
        self.after(100, apply_rounded_corners, self)
        self.update_slideshow()
        self.update_progress()

    def update_slideshow(self):
        """Switches images every 3 seconds"""
        if self.current_img_idx < len(self.images):
            img_path = os.path.join(self.assets_path, self.images[self.current_img_idx])
            try:
                raw_img = Image.open(img_path)
                ctk_img = ctk.CTkImage(raw_img, size=(600, 350))
                self.img_label.configure(image=ctk_img)
                self.current_img_idx += 1
                self.after(3000, self.update_slideshow)
            except:
                self.current_img_idx += 1
                self.after(3000, self.update_slideshow)

    def update_progress(self):
        """Handles the 1% to 100% logic and status text"""
        if self.progress_val <= 1.0:
            # Update the bar and percentage text
            self.progress_bar.set(self.progress_val)
            self.percentage_label.configure(text=f"{int(self.progress_val * 100)}%")
            
            # Change status text randomly to look like it's "thinking"
            if int(self.progress_val * 100) % 20 == 0:
                self.status_label.configure(text=random.choice(self.status_messages))
            
            # Increment progress (0.01 = 1%)
            # It will take about 9 seconds total (matches 3 images x 3 seconds)
            self.progress_val += 0.01
            self.after(90, self.update_progress) 
        else:
            self.finish_splash()

    def finish_splash(self):
        self.destroy()
        # Note: security.show_login() doesn't exist, this splash screen is not used in the main flow

import customtkinter as ctk
from security import LoginPage   # Assuming you saved the login class here
from splash import SplashScreen2, apply_rounded_corners # Assuming you saved the splash class here
from ui_dashboard import Dashboard     # Your beautiful registry GUI

def run_freeman_os():
    # Check license before starting application
    check_license_before_start()
    
    # Check Terms of Use agreement
    if not check_terms_agreement():
        show_terms_dialog()

    # STEP 1: OPEN LOGIN
    login = LoginPage()
    login.mainloop() 
    
    if login.success:
    # The code PAUSES here until login.destroy() is called inside the Login class
    
    # STEP 2: IF LOGIN SUCCESSFUL, SHOW ANIMATED SPLASH
    # (In your Login class, ensure you only call self.destroy() if credentials are correct)
       splash = SplashScreen2()
       splash.mainloop()

    # STEP 3: LAUNCH THE HOMEPAGE
       app = Dashboard()
       app.mainloop()
    else:
        # If they hit "X" or failed, the script just ends here
        print("Login cancelled or failed. System shutting down.")

if __name__ == "__main__":
    # Show initial splash screen
    app = SplashScreen()
    app.mainloop()
    
    # Then run the main application (login → splashscreen2 → dashboard)
    run_freeman_os()




