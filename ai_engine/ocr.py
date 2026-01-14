import pytesseract
from PIL import Image
import re
import os

# Set tesseract path if needed (e.g. Windows default)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# We will assume it's in PATH or user can configure it.

def extract_text(image_path):
    """Extracts text from an image file."""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""

def parse_receipt(text):
    """
    Analyzes OCR text to find the Amount and a Description.
    Strategy: 
    - Description: First few lines or the longest line.
    - Amount: The largest float found in the text (usually the Total).
    """
    if not text:
        return "Receipt", 0.0

    # Find all numbers (like 1200.00, 500, etc.)
    # Exclude dates if possible, but simplest is just find all floats.
    matches = re.findall(r'\b\d+\.\d{2}\b|\b\d+\b', text)
    
    amount = 0.0
    if matches:
        # Convert to floats and find max
        try:
            amounts = [float(m) for m in matches]
            amount = max(amounts)
        except:
            pass
            
    # Clean text for description
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    description = lines[0] if lines else "Scanned Receipt"
    
    # If description is just the amount, try next line
    if str(amount) in description and len(lines) > 1:
        description = lines[1]
        
    return description, amount

def parse_receipt_items(text):
    """
    Advanced OCR: Extracts multiple items from a receipt.
    Returns a list of {'desc': str, 'amount': float}
    """
    if not text:
        return []

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    items = []
    
    # regex for line item: "Item Name ... 120.00"
    # Matches: [Words] [Spaces] [Number with optional decimal]
    item_pattern = re.compile(r'([a-zA-Z\s]+).*?(\d+\.?\d{0,2})')
    
    ignore_keywords = ["total", "subtotal", "tax", "cash", "change", "due", "visa", "date", "time", "receipt", "thank"]

    for line in lines:
        line_lower = line.lower()
        
        # Skip total/footer lines
        if any(bad in line_lower for bad in ignore_keywords):
            continue
            
        match = item_pattern.search(line)
        if match:
            desc_raw = match.group(1).strip()
            amt_raw = match.group(2)
            
            # Filter unlikely descriptions (too short, too long)
            if len(desc_raw) < 3 or len(desc_raw) > 50: 
                continue
                
            try:
                amount = float(amt_raw)
                if amount > 0:
                    items.append({'desc': desc_raw, 'amount': amount})
            except:
                continue
                
    return items
