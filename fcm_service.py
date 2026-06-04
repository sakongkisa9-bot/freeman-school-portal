import os
import json
import logging
from typing import List, Dict, Optional

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FCM_AVAILABLE = True
except ImportError:
    FCM_AVAILABLE = False
    logging.warning("firebase-admin not installed. FCM notifications will not work.")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_PATH = os.path.join(PROJECT_DIR, "firebase-service-account.json")


class FCMService:
    """Firebase Cloud Messaging service for push notifications"""
    
    def __init__(self):
        self.initialized = False
        if FCM_AVAILABLE:
            self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if already initialized
            if firebase_admin._apps:
                self.initialized = True
                logging.info("Firebase already initialized")
                return
            
            # Try to get credentials from environment variable (for cloud deployment)
            service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
            if service_account_json:
                try:
                    cred_dict = json.loads(service_account_json)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                    self.initialized = True
                    logging.info("Firebase initialized from environment variable")
                    return
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse FIREBASE_SERVICE_ACCOUNT JSON: {e}")
            
            # Fallback to file (for local development)
            if not os.path.exists(SERVICE_ACCOUNT_PATH):
                logging.warning(f"Firebase service account file not found at {SERVICE_ACCOUNT_PATH}")
                logging.warning("Set FIREBASE_SERVICE_ACCOUNT environment variable or place firebase-service-account.json in project root")
                return
            
            # Initialize Firebase with service account file
            cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred)
            self.initialized = True
            logging.info("Firebase initialized from file")
            
        except Exception as e:
            logging.error(f"Failed to initialize Firebase: {e}")
    
    def is_available(self) -> bool:
        """Check if FCM service is available"""
        return FCM_AVAILABLE and self.initialized
    
    def send_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict] = None
    ) -> bool:
        """Send a notification to a specific device"""
        if not self.is_available():
            logging.warning("FCM not available, cannot send notification")
            return False
        
        try:
            # Create message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                token=token
            )
            
            # Send message
            response = messaging.send(message)
            logging.info(f"Notification sent successfully: {response}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send notification: {e}")
            return False
    
    def send_multicast_notification(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict] = None
    ) -> Dict:
        """Send a notification to multiple devices"""
        if not self.is_available():
            logging.warning("FCM not available, cannot send multicast notification")
            return {"success": 0, "failure": len(tokens)}
        
        try:
            # Create multicast message
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                tokens=tokens
            )
            
            # Send message
            response = messaging.send_multicast(message)
            logging.info(f"Multicast notification sent: {response.success_count} success, {response.failure_count} failure")
            
            return {
                "success": response.success_count,
                "failure": response.failure_count,
                "invalid_tokens": []
            }
            
        except messaging.InvalidArgumentError as e:
            # Handle invalid tokens
            logging.error(f"Invalid tokens in multicast: {e}")
            return {"success": 0, "failure": len(tokens), "invalid_tokens": tokens}
        except Exception as e:
            logging.error(f"Failed to send multicast notification: {e}")
            return {"success": 0, "failure": len(tokens)}
    
    def send_topic_notification(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict] = None
    ) -> bool:
        """Send a notification to all devices subscribed to a topic"""
        if not self.is_available():
            logging.warning("FCM not available, cannot send topic notification")
            return False
        
        try:
            # Create topic message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                topic=topic
            )
            
            # Send message
            response = messaging.send(message)
            logging.info(f"Topic notification sent successfully: {response}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send topic notification: {e}")
            return False


# Global FCM service instance
_fcm_service = None

def get_fcm_service() -> FCMService:
    """Get or create the global FCM service instance"""
    global _fcm_service
    if _fcm_service is None:
        _fcm_service = FCMService()
    return _fcm_service
