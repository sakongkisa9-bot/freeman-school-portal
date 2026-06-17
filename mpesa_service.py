"""
M-Pesa Daraja API Integration Service
Handles STK Push payments for student fees
"""
import base64
import requests
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MpesaService:
    """M-Pesa Daraja API Service for STK Push payments"""
    
    def __init__(self, consumer_key: str, consumer_secret: str, 
                 passkey: str, shortcode: str, 
                 environment: str = "sandbox"):
        """
        Initialize M-Pesa Service
        
        Args:
            consumer_key: M-Pesa consumer key from Daraja portal
            consumer_secret: M-Pesa consumer secret from Daraja portal
            passkey: M-Pesa passkey for STK Push
            shortcode: M-Pesa shortcode (paybill/till number)
            environment: 'sandbox' or 'production'
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.passkey = passkey
        self.shortcode = shortcode
        self.environment = environment
        
        # API URLs based on environment
        if environment == "sandbox":
            self.auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
            self.stk_push_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        else:
            self.auth_url = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
            self.stk_push_url = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        
        self.access_token = None
        self.token_expiry = None
    
    def get_access_token(self) -> Optional[str]:
        """
        Get OAuth access token from M-Pesa
        
        Returns:
            Access token string or None if failed
        """
        # Check if token is still valid (expires in 1 hour)
        if self.access_token and self.token_expiry:
            if datetime.now() < self.token_expiry:
                return self.access_token
        
        try:
            # Create basic auth header
            auth_string = f"{self.consumer_key}:{self.consumer_secret}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {encoded_auth}"
            }
            
            response = requests.get(self.auth_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                # Token expires in 1 hour, set expiry to 55 minutes to be safe
                self.token_expiry = datetime.now().replace(minute=55, second=0, microsecond=0)
                logger.info("Successfully obtained M-Pesa access token")
                return self.access_token
            else:
                logger.error(f"Failed to get access token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None
    
    def initiate_stk_push(self, phone_number: str, amount: int, 
                         callback_url: str, account_reference: str,
                         transaction_desc: str) -> Tuple[bool, Optional[Dict]]:
        """
        Initiate STK Push payment request
        
        Args:
            phone_number: Customer phone number (format: 254XXXXXXXXX)
            amount: Amount to charge (in KES)
            callback_url: URL to receive payment callback
            account_reference: Reference for the transaction (e.g., student adm_no)
            transaction_desc: Description of the transaction
            
        Returns:
            Tuple of (success, response_data)
        """
        # Get access token
        token = self.get_access_token()
        if not token:
            return False, {"error": "Failed to get access token"}
        
        # Format phone number (ensure it starts with 254)
        if phone_number.startswith("0"):
            phone_number = "254" + phone_number[1:]
        elif phone_number.startswith("+"):
            phone_number = phone_number[1:]
        
        # Generate timestamp and password
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        
        # Prepare STK Push request
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc
        }
        
        try:
            response = requests.post(self.stk_push_url, json=payload, 
                                    headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"STK Push initiated successfully: {data}")
                return True, data
            else:
                logger.error(f"STK Push failed: {response.status_code} - {response.text}")
                return False, {"error": response.text}
                
        except Exception as e:
            logger.error(f"Error initiating STK Push: {e}")
            return False, {"error": str(e)}
    
    def parse_callback(self, callback_data: Dict) -> Dict:
        """
        Parse M-Pesa callback data
        
        Args:
            callback_data: Raw callback data from M-Pesa
            
        Returns:
            Parsed callback information
        """
        try:
            # Extract callback metadata
            stk_callback = callback_data.get("Body", {}).get("stkCallback", {})
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc")
            merchant_request_id = stk_callback.get("MerchantRequestID")
            checkout_request_id = stk_callback.get("CheckoutRequestID")
            
            # Extract callback metadata
            callback_metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            
            # Parse metadata items
            metadata = {}
            for item in callback_metadata:
                name = item.get("Name")
                value = item.get("Value")
                metadata[name] = value
            
            # Extract payment details
            amount = metadata.get("Amount")
            mpesa_receipt = metadata.get("MpesaReceiptNumber")
            transaction_date = metadata.get("TransactionDate")
            phone_number = metadata.get("PhoneNumber")
            
            return {
                "success": result_code == 0,
                "result_code": result_code,
                "result_desc": result_desc,
                "merchant_request_id": merchant_request_id,
                "checkout_request_id": checkout_request_id,
                "amount": amount,
                "mpesa_receipt": mpesa_receipt,
                "transaction_date": transaction_date,
                "phone_number": phone_number,
                "raw_metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error parsing callback: {e}")
            return {"error": str(e)}


def format_phone_number(phone: str) -> str:
    """
    Format phone number to M-Pesa format (254XXXXXXXXX)
    
    Args:
        phone: Phone number in various formats
        
    Returns:
        Formatted phone number
    """
    phone = phone.strip()
    
    # Remove any non-digit characters
    phone = ''.join(c for c in phone if c.isdigit())
    
    # If starts with 0, replace with 254
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    # If starts with 7, add 254
    elif phone.startswith("7"):
        phone = "254" + phone
    # If already starts with 254, keep as is
    
    return phone
