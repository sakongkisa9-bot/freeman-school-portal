import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
import sys


class NotificationService:
    """Service for sending alerts via Telegram or Email"""
    
    def __init__(self):
        self.config = self.load_config()
    
    def load_config(self):
        """Load notification configuration from file"""
        try:
            # Handle both development and executable environments
            if getattr(sys, 'frozen', False):
                # Running as executable - use user data directory for config
                USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
                os.makedirs(USER_DATA_DIR, exist_ok=True)
                config_path = os.path.join(USER_DATA_DIR, "notification_config.json")
                
                # If config doesn't exist in user data, copy from the bundled config
                if not os.path.exists(config_path):
                    bundled_config_path = os.path.join(sys._MEIPASS, "notification_config.json")
                    if os.path.exists(bundled_config_path):
                        import shutil
                        shutil.copy(bundled_config_path, config_path)
            else:
                # Running as script - use project directory
                config_path = os.path.join(
                    os.path.dirname(os.path.realpath(__file__)), "notification_config.json"
                )
            
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading notification config: {e}")
        return {}
    
    def send_telegram_alert(self, message):
        """Send alert via Telegram bot"""
        try:
            bot_token = self.config.get("telegram_bot_token", "")
            chat_id = self.config.get("telegram_chat_id", "")
            
            if not bot_token or not chat_id:
                return False, "Telegram credentials not configured"
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=data, timeout=30)
            result = response.json()
            
            if result.get("ok"):
                return True, "Telegram alert sent successfully"
            else:
                return False, result.get("description", "Unknown error")
                
        except Exception as e:
            return False, f"Telegram error: {str(e)}"
    
    def send_email_alert(self, subject, message):
        """Send alert via Email"""
        try:
            smtp_server = self.config.get("smtp_server", "")
            smtp_port = self.config.get("smtp_port", 587)
            smtp_username = self.config.get("smtp_username", "")
            smtp_password = self.config.get("smtp_password", "")
            from_email = self.config.get("from_email", "")
            to_email = self.config.get("to_email", "")
            
            if not all([smtp_server, smtp_username, smtp_password, from_email, to_email]):
                return False, "Email credentials not configured"
            
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True, "Email alert sent successfully"
            
        except Exception as e:
            return False, f"Email error: {str(e)}"
    
    def send_alert(self, message, subject="Freeman School Portal Alert"):
        """Send alert via configured channels (Telegram or Email)"""
        results = []
        
        # Try Telegram first
        telegram_success, telegram_msg = self.send_telegram_alert(message)
        results.append(("Telegram", telegram_success, telegram_msg))
        
        # If Telegram fails, try Email
        if not telegram_success:
            email_success, email_msg = self.send_email_alert(subject, message)
            results.append(("Email", email_success, email_msg))
        
        return results
