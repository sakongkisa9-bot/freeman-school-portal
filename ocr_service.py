import pytesseract
import cv2
import numpy as np
from PIL import Image
import re
import os
from typing import List, Dict, Optional, Tuple

class OCRService:
    """Service for OCR-based student registration from images"""
    
    def __init__(self):
        # Set Tesseract path for Windows (adjust if needed)
        if os.name == 'nt':  # Windows
            # Try multiple possible Tesseract locations
            possible_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tesseract', 'tesseract.exe'),
                os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tesseract.exe')
            ]
            
            tesseract_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    tesseract_path = path
                    break
            
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                print(f"Tesseract found at: {tesseract_path}")
            else:
                print("Warning: Tesseract not found. Please install Tesseract OCR or include it in the application folder.")
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for better OCR accuracy"""
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image from {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to get binary image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(binary, h=10)
        
        # Apply dilation to make text more prominent
        kernel = np.ones((2, 2), np.uint8)
        dilated = cv2.dilate(denoised, kernel, iterations=1)
        
        return dilated
    
    def extract_text(self, image_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            # Preprocess image
            processed_img = self.preprocess_image(image_path)
            
            # Convert to PIL Image for Tesseract
            pil_img = Image.fromarray(processed_img)
            
            # Extract text with multiple configurations for better accuracy
            text = pytesseract.image_to_string(
                pil_img,
                config='--psm 6 -c preserve_interword_spaces=1'
            )
            
            return text.strip()
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
    
    def parse_student_data(self, text: str) -> List[Dict[str, str]]:
        """Parse extracted text to identify student information"""
        students = []
        lines = text.split('\n')
        
        current_student = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                # Empty line might indicate end of student record
                if current_student:
                    students.append(current_student)
                    current_student = {}
                continue
            
            # Try to identify patterns for student data
            # Pattern: Admission Number (e.g., ADM: 12345 or just 12345)
            adm_match = re.search(r'(?:ADM|Admission|Adm\s*[:#]?\s*)(\d+)', line, re.IGNORECASE)
            if adm_match:
                current_student['adm_no'] = adm_match.group(1)
                continue
            
            # Pattern: Name (usually the first non-numeric field after ADM)
            # Look for lines that contain letters but not many numbers
            if re.search(r'[A-Za-z]{3,}', line) and not re.search(r'\d{4,}', line):
                # This might be a name
                name = re.sub(r'[^A-Za-z\s\-]', '', line).strip()
                if name and len(name) > 2:
                    current_student['name'] = name
                    continue
            
            # Pattern: Grade/Class (e.g., Grade 1, Class 2A, PP1, PP2)
            grade_match = re.search(r'(?:Grade|Class|Std)\s*(\d+[A-Za-z]?)|PP[12]|Playgroup', line, re.IGNORECASE)
            if grade_match:
                current_student['grade'] = grade_match.group(0).strip()
                continue
            
            # Pattern: Gender (M/F, Male/Female)
            gender_match = re.search(r'(?:Gender|Gen|Sex)\s*[:#]?\s*(M|F|Male|Female)', line, re.IGNORECASE)
            if gender_match:
                gender = gender_match.group(1).upper()
                if gender in ['MALE', 'FEMALE']:
                    current_student['gender'] = gender[0]  # M or F
                else:
                    current_student['gender'] = gender.upper()
                continue
            
            # Pattern: Phone number
            phone_match = re.search(r'(?:Phone|Tel|Contact)\s*[:#]?\s*(\d{10,})', line, re.IGNORECASE)
            if phone_match:
                current_student['phone'] = phone_match.group(1)
                continue
            
            # If line looks like a complete student record (has name and numbers)
            # Try to parse tab-separated or comma-separated values
            if '\t' in line or ',' in line:
                parts = re.split(r'[\t,]', line)
                if len(parts) >= 2:
                    # Try to identify which part is which
                    for part in parts:
                        part = part.strip()
                        if re.match(r'^\d+$', part) and len(part) >= 4:
                            current_student['adm_no'] = part
                        elif re.search(r'[A-Za-z]{3,}', part) and not re.search(r'\d{4,}', part):
                            current_student['name'] = part
        
        # Don't forget the last student
        if current_student:
            students.append(current_student)
        
        return students
    
    def process_student_list_image(self, image_path: str) -> Tuple[List[Dict[str, str]], str]:
        """Process an image containing a list of students"""
        try:
            # Extract text from image
            extracted_text = self.extract_text(image_path)
            
            if not extracted_text:
                return [], "No text could be extracted from the image"
            
            # Parse student data
            students = self.parse_student_data(extracted_text)
            
            if not students:
                return [], "No student data could be parsed from the extracted text"
            
            return students, f"Successfully extracted {len(students)} student records"
            
        except Exception as e:
            return [], f"Error processing image: {str(e)}"
    
    def validate_student_data(self, student: Dict[str, str]) -> Dict[str, str]:
        """Validate and clean student data"""
        cleaned = {}
        
        # Clean admission number
        if 'adm_no' in student:
            cleaned['adm_no'] = re.sub(r'[^\d]', '', str(student['adm_no']))
        
        # Clean name
        if 'name' in student:
            cleaned['name'] = re.sub(r'[^A-Za-z\s\-]', '', str(student['name'])).strip()
        
        # Clean grade
        if 'grade' in student:
            cleaned['grade'] = str(student['grade']).strip()
        
        # Clean gender
        if 'gender' in student:
            gender = str(student['gender']).upper()
            if gender.startswith('M'):
                cleaned['gender'] = 'M'
            elif gender.startswith('F'):
                cleaned['gender'] = 'F'
            else:
                cleaned['gender'] = gender
        
        # Clean phone
        if 'phone' in student:
            cleaned['phone'] = re.sub(r'[^\d]', '', str(student['phone']))
        
        return cleaned

# Test function
def test_ocr_service():
    """Test the OCR service with a sample image"""
    ocr = OCRService()
    
    # Test with a sample image path
    test_image = "sample_student_list.jpg"
    
    if os.path.exists(test_image):
        students, message = ocr.process_student_list_image(test_image)
        print(f"Message: {message}")
        print(f"Students found: {len(students)}")
        for i, student in enumerate(students, 1):
            print(f"\nStudent {i}:")
            print(f"  ADM: {student.get('adm_no', 'N/A')}")
            print(f"  Name: {student.get('name', 'N/A')}")
            print(f"  Grade: {student.get('grade', 'N/A')}")
            print(f"  Gender: {student.get('gender', 'N/A')}")
            print(f"  Phone: {student.get('phone', 'N/A')}")
    else:
        print(f"Test image not found: {test_image}")
        print("Please provide a sample image to test OCR functionality.")

if __name__ == "__main__":
    test_ocr_service()
