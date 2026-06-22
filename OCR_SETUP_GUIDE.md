# OCR Student Registration Setup Guide

This guide explains how to set up and use the OCR (Optical Character Recognition) feature to register students from images.

## What is OCR Student Registration?

OCR Student Registration allows you to:
- Take a picture or upload an image containing a list of students
- Automatically extract student information (names, admission numbers, grades, etc.)
- Review and edit the extracted data
- Register multiple students at once to the database

## Prerequisites

### 1. Install Tesseract OCR Engine

The OCR feature requires Tesseract OCR engine to be installed on your system.

#### For Windows:
1. Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
2. Download the latest Windows installer (e.g., `tesseract-ocr-w64-setup-5.3.0.20221222.exe`)
3. Run the installer and follow the setup wizard
4. **Important:** Note the installation path (default: `C:\Program Files\Tesseract-OCR`)
5. If you install to a different location, update the path in `ocr_service.py` line 15

#### For macOS:
```bash
brew install tesseract
```

#### For Linux:
```bash
sudo apt-get install tesseract-ocr
```

### 2. Install Python Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

The OCR-related dependencies are:
- `pytesseract==0.3.10` - Python wrapper for Tesseract
- `Pillow==10.0.0` - Image processing library
- `opencv-python==4.8.0.76` - Advanced image processing

## How to Use OCR Student Registration

### Step 1: Navigate to Student Registration
1. Open the Freeman School Portal application
2. Click on "Register Students" in the main menu
3. Select the class/grade you want to register students for

### Step 2: Open OCR Dialog
1. In the student registry view, click the **"📷 OCR Register"** button on the right control panel
2. This will open the OCR Student Registration dialog

### Step 3: Select Image
1. Click **"📷 Select Image"** button
2. Choose an image file containing a student list (supports: JPG, JPEG, PNG, BMP, TIFF)
3. The image preview will appear in the dialog

### Step 4: Extract Student Data
1. Click **"🔍 Extract Students"** button
2. The system will process the image using OCR
3. Extracted student data will appear in a table format

### Step 5: Review and Edit
1. Review the extracted student information
2. Edit any fields directly in the table:
   - **ADM No** - Admission number (required)
   - **Name** - Student name (required)
   - **Grade** - Class/grade
   - **Gender** - M/F (dropdown selection)
   - **Phone** - Contact number (optional)
3. Remove incorrect entries by clicking the **"✕"** button
4. Clear all data using **"🗑️ Clear All"** if needed

### Step 6: Register Students
1. Click **"✅ Register All Students"** button
2. Confirm the registration
3. Students will be added to the database
4. The student registry will automatically refresh to show the new students

## Best Practices for OCR Accuracy

### Image Quality:
- Use high-resolution images (300 DPI or higher)
- Ensure good lighting when taking photos
- Avoid blurry or distorted images
- Use a flat surface for documents

### Text Format:
- Use clear, legible fonts
- Ensure text has good contrast (black text on white background)
- Avoid handwritten text if possible (OCR works best with printed text)
- Use tabular or list format for student data

### Document Layout:
- Organize student data in columns or rows
- Include clear headers (ADM No, Name, Grade, etc.)
- Maintain consistent formatting throughout
- Avoid complex backgrounds or watermarks

## Supported Data Formats

The OCR system can extract student data from various formats:

### Tabular Format:
```
ADM No    Name            Grade    Gender    Phone
12345     John Doe        Grade 1  M         0712345678
12346     Jane Smith      Grade 1  F         0723456789
```

### List Format:
```
ADM: 12345
Name: John Doe
Grade: Grade 1
Gender: M
Phone: 0712345678

ADM: 12346
Name: Jane Smith
Grade: Grade 1
Gender: F
Phone: 0723456789
```

### Comma-Separated:
```
12345, John Doe, Grade 1, M, 0712345678
12346, Jane Smith, Grade 1, F, 0723456789
```

## Troubleshooting

### Tesseract Not Found Error:
**Problem:** "Warning: Tesseract not found at default path"

**Solution:**
1. Verify Tesseract is installed
2. Check the installation path
3. Update the path in `ocr_service.py` line 15:
   ```python
   tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

### No Text Extracted:
**Problem:** "No text could be extracted from the image"

**Solution:**
1. Check image quality and resolution
2. Ensure text is clearly visible
3. Try converting image to black and white
4. Use a different image format (PNG recommended)

### Poor OCR Accuracy:
**Problem:** Extracted text has many errors

**Solution:**
1. Use higher resolution images
2. Improve lighting conditions
3. Ensure text is horizontal (not rotated)
4. Pre-process image using photo editing software
5. Try using printed text instead of handwritten

### Import Errors:
**Problem:** "ModuleNotFoundError: No module named 'pytesseract'"

**Solution:**
```bash
pip install pytesseract Pillow opencv-python
```

## Advanced Configuration

### Custom Tesseract Path:
If Tesseract is installed in a non-standard location, update `ocr_service.py`:

```python
# Line 15 in ocr_service.py
tesseract_path = r'YOUR_CUSTOM_PATH\tesseract.exe'
```

### OCR Language Support:
To add support for additional languages, modify the Tesseract configuration in `ocr_service.py`:

```python
# Line 47 in ocr_service.py
text = pytesseract.image_to_string(
    pil_img,
    config='--psm 6 -l eng+swa'  # Add language codes (eng=English, swa=Swahili)
)
```

## Security Considerations

- The OCR feature processes images locally on your machine
- No data is sent to external servers
- All student data remains in your local database
- Images are not stored after processing

## Performance Tips

- For large student lists (50+ students), consider splitting into multiple images
- Use images with good contrast for faster processing
- Close other applications to improve processing speed
- Processing time depends on image size and system resources

## Support

For issues or questions:
1. Check this guide first
2. Verify Tesseract installation
3. Test with a simple image first
4. Check console output for error messages

## Example Workflow

1. **Prepare Document**: Print or write student list in clear format
2. **Capture Image**: Take photo or scan the document
3. **Open OCR Dialog**: Click "📷 OCR Register" in student registry
4. **Select Image**: Choose the captured image file
5. **Extract Data**: Click "🔍 Extract Students"
6. **Review**: Check extracted data for accuracy
7. **Edit**: Correct any errors in the table
8. **Register**: Click "✅ Register All Students"
9. **Verify**: Check student registry for new entries

## Integration with Existing Features

The OCR feature integrates seamlessly with:
- **Student Registry**: Automatically refreshes after registration
- **Database**: Uses existing student database structure
- **Validation**: Applies same validation rules as manual entry
- **Anti-cheating**: Records student footprint for deleted students
- **Cloud Sync**: OCR-registered students sync with cloud portal

## Future Enhancements

Potential improvements for future versions:
- Support for handwritten text recognition
- Batch processing of multiple images
- Custom data template configuration
- Direct camera integration (no file selection needed)
- Real-time OCR preview
- Export extracted data to Excel/CSV
