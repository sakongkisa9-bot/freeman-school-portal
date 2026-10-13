"""
M-Pesa Callback Server
Handles M-Pesa STK Push payment callbacks for the Freeman School Portal
This server receives payment confirmations from Safaricom and updates the database
"""
from flask import Flask, request, jsonify
import threading
import sqlite3
import os
import sys
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Handle both development and executable environments
if getattr(sys, 'frozen', False):
    # Running as executable
    USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
else:
    # Running as script
    USER_DATA_DIR = os.path.dirname(os.path.realpath(__file__))

DB_PATH = os.path.join(USER_DATA_DIR, "freeman_school.db")

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    """Handle M-Pesa STK Push callback"""
    try:
        callback_data = request.get_json()
        logger.info(f"Received M-Pesa callback: {callback_data}")
        
        # Parse callback data
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
        
        # Update payment status in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Find the pending payment record
            cursor.execute('''
                SELECT id, payment_type, amount FROM payment_tracking
                WHERE merchant_request_id = ? AND status = 'pending'
                ORDER BY id DESC LIMIT 1
            ''', (merchant_request_id,))
            
            payment_record = cursor.fetchone()
            
            if payment_record:
                payment_id = payment_record['id']
                payment_type = payment_record['payment_type']
                expected_amount = payment_record['amount']
                
                # Update payment status based on result code
                if result_code == 0:  # Success
                    # Format transaction date for database
                    if transaction_date:
                        try:
                            # M-Pesa format: YYYYMMDDHHMMSS
                            formatted_date = datetime.strptime(transaction_date, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            formatted_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        formatted_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    cursor.execute('''
                        UPDATE payment_tracking
                        SET status = 'completed',
                            mpesa_receipt = ?,
                            transaction_date = ?,
                            result_code = ?,
                            result_desc = ?
                        WHERE id = ?
                    ''', (mpesa_receipt, formatted_date, result_code, result_desc, payment_id))
                    
                    logger.info(f"Payment {payment_id} completed successfully. Receipt: {mpesa_receipt}")
                    
                    # Handle student payment status updates based on payment type
                    if payment_type in ['termly_full', 'installation_fee']:
                        # Mark all students as paid for full payments
                        cursor.execute("SELECT adm_no FROM students")
                        students = cursor.fetchall()
                        
                        for student in students:
                            adm_no = student['adm_no']
                            cursor.execute('''
                                INSERT OR REPLACE INTO student_payments
                                (adm_no, student_name, payment_type, amount_paid, payment_status, payment_date)
                                VALUES (?, (SELECT name FROM students WHERE adm_no = ?), ?, ?, ?, ?)
                            ''', (adm_no, adm_no, payment_type, amount if payment_type == 'termly_full' else 0, 'paid', formatted_date))
                    
                    elif payment_type in ['termly_70_percent', 'installation_fee_70']:
                        # For 70% payments, we need to handle student selection separately
                        # This will be handled by the UI when payment is confirmed
                        logger.info(f"70% payment {payment_id} completed. Student selection required.")
                    
                    elif payment_type == 'remaining_students':
                        # This is handled by the UI after payment confirmation
                        logger.info(f"Remaining students payment {payment_id} completed.")
                    
                else:  # Failed
                    cursor.execute('''
                        UPDATE payment_tracking
                        SET status = 'failed',
                            result_code = ?,
                            result_desc = ?
                        WHERE id = ?
                    ''', (result_code, result_desc, payment_id))
                    
                    logger.error(f"Payment {payment_id} failed: {result_desc}")
                
                conn.commit()
                return jsonify({"status": "success", "message": "Callback processed"}), 200
            else:
                logger.warning(f"No pending payment found for MerchantRequestID: {merchant_request_id}")
                return jsonify({"status": "error", "message": "Payment record not found"}), 404
                
        except Exception as e:
            logger.error(f"Database error processing callback: {e}")
            conn.rollback()
            return jsonify({"status": "error", "message": str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error processing M-Pesa callback: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "M-Pesa Callback Server"}), 200

def run_callback_server(port=5000):
    """Run the callback server in a separate thread"""
    logger.info(f"Starting M-Pesa callback server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

if __name__ == "__main__":
    # For standalone testing
    run_callback_server()