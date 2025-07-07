#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF to CSV Converter for Bank Leumi Statements
Converts Bank Leumi PDF statements to CSV format compatible with PNL Dashboard
"""

import argparse
import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

try:
    import pdfplumber
except ImportError:
    print("Error: pdfplumber is not installed. Install with: pip install pdfplumber")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("Error: pandas is not installed. Install with: pip install pandas")
    sys.exit(1)


class BankLeumiPDFParser:
    """Parser for Bank Leumi PDF statements"""
    
    def __init__(self, verbose=False, force=False):
        self.verbose = verbose
        self.force = force
        # Hebrew month names mapping
        self.hebrew_months = {
            'ינואר': 1, 'פברואר': 2, 'מרץ': 3, 'אפריל': 4,
            'מאי': 5, 'יוני': 6, 'יולי': 7, 'אוגוסט': 8,
            'ספטמבר': 9, 'אוקטובר': 10, 'נובמבר': 11, 'דצמבר': 12
        }
        
        # Transaction patterns for Bank Leumi statements
        # Based on actual format: balance amount reference description date date
        self.transaction_patterns = [
            # Main Bank Leumi pattern: balance amount reference description date date
            r'([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+(\d+)\s*([א-ת\-\*\s]+?)\s+(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})',
            
            # Alternative pattern with more flexible spacing
            r'([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+(\d+)\s+([א-ת\-\*\s]+?)\s+(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})',
            
            # Pattern for lines with currency symbols
            r'([\d,]+\.?\d*)\s*₪?\s+([\d,]+\.?\d*)\s*₪?\s+(\d+)\s+([א-ת\-\*\s]+?)\s+(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})',
            
            # Fallback: Original patterns for other formats (keeping for compatibility)
            r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\s+(.+?)\s+([\-\+\(]?\d{1,3}(?:,\d{3})*\.?\d{0,2}[\)\-]?)\s+([\-\+\(]?\d{1,3}(?:,\d{3})*\.?\d{0,2}[\)\-]?)',
        ]
        
        # Income keywords for transaction classification
        self.income_keywords = [
            'רבית זכות', 'הפקדת מזומן', 'משכורת', 'פרילנס', 'החזר', 'הכנסה', 'זיכוי', 'שכר',
            'העברת משכורת', 'ריבית לפקדון', 'פרעון פקדון', 'זיכוי עמ.הישיר', 'הפקדת שיק'
        ]
        
        # Category mappings
        self.category_map = {
            'לאומי ויזא': 'כרטיסי אשראי',
            'הע. אינטרנט': 'העברות',
            'מסלול בסיסי': 'עמלות בנק',
            'עיריית ירושל': 'מסים עירוניים',
            'קופת פנסיה': 'פנסיה וביטוח',
            'הראל חברה': 'ביטוח',
            'מנהלת הגמלאו': 'חסכונות',
            'ביטוח': 'ביטוח',
            'הוראת קבע': 'תשלומים קבועים',
            'שירותי בריאו': 'בריאות',
            'העברה עצמית': 'העברות פנימיות',
            'העברה דיגיטל': 'העברות דיגיטליות',
            'משיכת מזומן': 'משיכות מזומן',
            'הפקדת מזומן': 'הפקדות',
            'גביית עמלה': 'עמלות',
            'רבית זכות': 'רבית והכנסות',
            'מס הכנסה': 'מסים',
            'החזרי מס': 'החזרי מס',
            'כרטיסי אשראי': 'כרטיסי אשראי',
            'עמל.ערוץ יש': 'עמלות בנק',
            'הפקדת שיק': 'הפקדות',
            'מכבי': 'ביטוח בריאות',
            'לאומי למשכנת': 'משכנתא',
            'מיטב דש גמל': 'חסכונות וגמל',
            'מקס איט פיננ': 'הלוואות ואשראי',
            'בנק אוצר ה': 'העברות בנק',
            'בנק מזרחי': 'העברות בנק',
            'עמ.העברת מטח': 'העברות מטח',
            'העברת משכורת': 'הכנסות עבודה',
            'עמ.הקצאת אשראי': 'עמלות בנק',
            'ריבית לפקדון': 'רבית והכנסות',
            'פרעון פקדון': 'פקדונות',
            'פיקדון': 'פקדונות',
            'מסיטיבנק ס': 'העברות בנק',
            'זיכוי עמ.הישיר': 'החזרים',
            'תשלום עיקול פ': 'תשלומים משפטיים'
        }
        
        # Description translation mappings (from raw Hebrew to readable format)
        self.description_translations = {
            'י-יארשא יסיטרכ': 'כרטיסי אשראי-י',
            'י-יבכמ': 'מכבי-י',
            'תרוכשמ תרבעה': 'העברת משכורת',
            'לטיגיד הרבעה': 'העברה דיגיטל',
            'תימצע הרבעה': 'העברה עצמית',
            'יחרזמ קנב': 'בנק מזרחי',
            'י-ה רצוא קנב': 'בנק אוצר ה-י',
            'י-ראודה קנב': 'בנק אוצר ה-י',  # Alternative spelling
            'י-נניפ טיא סקמ': 'מקס איט פיננ-י',
            'י-למג שד בטימ': 'מיטב דש גמל-י',
            'י-תנכשמל ימואל': 'לאומי למשכנת-י',
            'טיב-םילעופה': 'הפועלים-ביט',
            'תוכז תיבר': 'רבית זכות',
            'הסנכה סמ': 'מס הכנסה',
            'קיש תדקפה': 'הפקדת שיק',
            'קיש': 'שיק',
            'י-זחה הסנכה-סמ': 'מס הכנסה-חזה-י',
            'ןודקפ ןוערפ': 'פרעון פקדון',
            'ןודקפל תיביר': 'ריבית לפקדון',
            '*ןודקיפ': 'פיקדון*',
            'פ לוקיע םולשת': 'תשלום עיקול פ',
            'יוכיז עמ.הישיר': 'זיכוי עמ.הישיר',
            'עמל.ערוץ יש': 'עמל.ערוץ יש'
        }
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            # Validate file exists and is readable
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            if not os.access(pdf_path, os.R_OK):
                raise PermissionError(f"Cannot read PDF file: {pdf_path}")
            
            # Check file size (avoid processing very large files)
            file_size = os.path.getsize(pdf_path)
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                raise ValueError(f"PDF file too large: {file_size / (1024*1024):.1f}MB (max 50MB)")
            
            if file_size == 0:
                raise ValueError("PDF file is empty")
            
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    raise ValueError("PDF file contains no pages")
                
                text = ""
                pages_processed = 0
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                            pages_processed += 1
                    except Exception as page_error:
                        # Log page error but continue with other pages
                        print(f"Warning: Could not process page {page_num + 1}: {page_error}")
                        continue
                
                if pages_processed == 0:
                    raise ValueError("No text could be extracted from any page in the PDF")
                
                # Debug output if verbose
                if self.verbose:
                    print(f"Successfully extracted text from {pages_processed} pages")
                    print("First 500 characters of extracted text:")
                    print("-" * 50)
                    print(text[:500])
                    print("-" * 50)
                
                return text
                
        except pdfplumber.PDFException as e:
            raise Exception(f"PDF parsing error: {str(e)}")
        except Exception as e:
            if isinstance(e, (FileNotFoundError, PermissionError, ValueError)):
                raise
            raise Exception(f"Unexpected error extracting text from PDF: {str(e)}")
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string in various formats"""
        # Remove extra whitespace
        date_str = date_str.strip()
        
        # Try different date formats
        date_formats = [
            "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y",
            "%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%Y/%m/%d",
            "%m/%d/%Y", "%m/%d/%y"  # American format (less common but possible)
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                
                # Fix year for 2-digit years
                if fmt.endswith('%y') and parsed_date.year < 2000:
                    # For 2-digit years, assume 20xx if year is 00-49, 19xx if 50-99
                    if parsed_date.year < 50:
                        parsed_date = parsed_date.replace(year=parsed_date.year + 2000)
                    else:
                        parsed_date = parsed_date.replace(year=parsed_date.year + 1900)
                
                # Validate that the date makes sense (not too far in future/past)
                current_year = datetime.now().year
                if parsed_date.year < 1990 or parsed_date.year > current_year + 1:
                    continue
                
                return parsed_date
            except ValueError:
                continue
        
        # Try to parse Hebrew date formats
        return self._parse_hebrew_date(date_str)
    
    def _parse_hebrew_date(self, date_str: str) -> Optional[datetime]:
        """Parse Hebrew date formats like '15 ינואר 2025' """
        try:
            # Pattern for Hebrew dates: "DD month_name YYYY"
            hebrew_date_pattern = r'(\d{1,2})\s+(\w+)\s+(\d{4})'
            match = re.match(hebrew_date_pattern, date_str)
            
            if match:
                day, month_name, year = match.groups()
                
                # Look up month number
                month_num = self.hebrew_months.get(month_name)
                if month_num:
                    return datetime(int(year), month_num, int(day))
            
            return None
        except (ValueError, TypeError):
            return None
    
    def parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string and return float"""
        if not amount_str:
            return None
        
        # Clean the amount string
        amount_str = amount_str.strip()
        
        # Remove currency symbols
        amount_str = amount_str.replace("₪", "").replace("$", "").strip()
        
        # Check for various negative formats
        is_negative = False
        
        # Format 1: Parentheses (1,234.56) or (1234.56)
        if amount_str.startswith("(") and amount_str.endswith(")"):
            is_negative = True
            amount_str = amount_str[1:-1]  # Remove parentheses
        
        # Format 2: Leading minus -1,234.56
        elif amount_str.startswith("-"):
            is_negative = True
            amount_str = amount_str[1:]  # Remove leading minus
        
        # Format 3: Trailing minus 1,234.56-
        elif amount_str.endswith("-"):
            is_negative = True
            amount_str = amount_str[:-1]  # Remove trailing minus
        
        # Format 4: Leading plus (explicit positive) +1,234.56
        elif amount_str.startswith("+"):
            amount_str = amount_str[1:]  # Remove leading plus
        
        # Remove commas from number
        amount_str = amount_str.replace(",", "").strip()
        
        # Handle empty string after cleaning
        if not amount_str:
            return None
        
        try:
            amount = float(amount_str)
            return -amount if is_negative else amount
        except ValueError:
            # Try to handle malformed numbers
            # Remove any remaining non-numeric characters except decimal point
            cleaned = re.sub(r'[^\d\.]', '', amount_str)
            if cleaned:
                try:
                    amount = float(cleaned)
                    return -amount if is_negative else amount
                except ValueError:
                    return None
            return None
    
    def classify_transaction(self, description: str, amount: float) -> str:
        """Classify transaction as Income or Expense"""
        # First check if it's based on amount sign
        if amount > 0:
            return "Income"
        
        # Check income keywords
        for keyword in self.income_keywords:
            if keyword in description:
                return "Income"
        
        return "Expense"
    
    def translate_description(self, description: str) -> str:
        """Translate raw Hebrew description to readable format"""
        # Clean the description
        cleaned_desc = description.strip()
        
        # Check direct translations first
        if cleaned_desc in self.description_translations:
            return self.description_translations[cleaned_desc]
        
        # Check for partial matches
        for raw_text, translated_text in self.description_translations.items():
            if raw_text in cleaned_desc:
                return translated_text
        
        # If no translation found, return original
        return cleaned_desc
    
    def extract_category(self, description: str) -> str:
        """Extract category from transaction description"""
        for keyword, category in self.category_map.items():
            if keyword in description:
                return category
        return "אחר"
    
    def parse_transactions(self, text: str) -> List[Dict]:
        """Parse transactions from PDF text"""
        transactions = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try each transaction pattern
            for pattern_idx, pattern in enumerate(self.transaction_patterns):
                match = re.search(pattern, line)
                if match:
                    groups = match.groups()
                    
                    # Handle different patterns based on number of groups
                    if len(groups) == 6:  # New Bank Leumi format: balance amount ref description date date
                        balance_str, amount_str, reference, description, date_str1, date_str2 = groups
                        date_str = date_str1  # Use first date
                        
                        # Calculate transaction amount from balance change if needed
                        # For now, use the amount directly but we might need to adjust the sign
                        
                    elif len(groups) == 4:  # Original format: date description amount balance
                        date_str, description, amount_str, balance_str = groups
                        
                    else:
                        continue  # Skip if unexpected number of groups
                    
                    # Parse date
                    date = self.parse_date(date_str)
                    if not date:
                        continue
                    
                    # Parse amount (raw from PDF)
                    raw_amount = self.parse_amount(amount_str)
                    if raw_amount is None:
                        continue
                    
                    # Parse balance
                    balance = self.parse_amount(balance_str)
                    if balance is None:
                        continue
                    
                    # Clean description
                    description = description.strip()
                    
                    # For new format, reverse Hebrew text if needed
                    if len(groups) == 6:
                        # The Hebrew text might be reversed, try to detect and fix
                        description = self._fix_hebrew_text(description)
                    
                    # Translate description to readable format
                    translated_description = self.translate_description(description)
                    
                    # Store both raw amount and balance for later processing
                    transaction = {
                        'date': date,
                        'description': translated_description,
                        'raw_amount': raw_amount,  # Store raw amount for calculation
                        'balance': balance,
                        'type': None,  # Will be set later
                        'category': None  # Will be set later
                    }
                    
                    if self.verbose and pattern_idx < 3:  # Debug for new patterns
                        print(f"Matched pattern {pattern_idx}: {line.strip()}")
                        print(f"  Parsed: date={date.strftime('%Y-%m-%d')}, desc='{translated_description}', raw_amount={raw_amount}, balance={balance}")
                    
                    transactions.append(transaction)
                    break
        
        # Post-process transactions to calculate actual amounts and set types
        return self._post_process_transactions(transactions)
    
    def _fix_hebrew_text(self, text: str) -> str:
        """Attempt to fix reversed Hebrew text"""
        # Simple heuristic: if text contains Hebrew and looks reversed, reverse it
        if text and any('\u0590' <= char <= '\u05FF' for char in text):
            # This is a simple approach - reverse the string
            # In a real implementation, you might want more sophisticated logic
            return text[::-1] if text.endswith('י-') or text.startswith('-') else text
        return text
    
    def save_to_csv(self, transactions: List[Dict], output_path: str) -> None:
        """Save transactions to CSV file"""
        if not transactions:
            raise ValueError("No transactions to save")
        
        # Sort transactions by date
        transactions.sort(key=lambda x: x['date'])
        
        # Create CSV data with proper rounding
        csv_data = []
        for transaction in transactions:
            csv_data.append({
                'Date': transaction['date'].strftime('%Y-%m-%d'),
                'Description': transaction['description'],
                'Amount': round(transaction['amount'], 2),
                'Balance': round(transaction['balance'], 2)
            })
        
        # Write to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Date', 'Description', 'Amount', 'Balance']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
    
    def convert_pdf_to_csv(self, pdf_path: str, csv_path: str) -> None:
        """Main conversion function"""
        try:
            # Validate input parameters
            if not pdf_path or not isinstance(pdf_path, str):
                raise ValueError("Invalid PDF path provided")
            
            if not csv_path or not isinstance(csv_path, str):
                raise ValueError("Invalid CSV path provided")
            
            # Extract text from PDF
            text = self.extract_text_from_pdf(pdf_path)
            
            if not text.strip():
                raise ValueError("No text could be extracted from the PDF")
            
            # Basic validation that this looks like a bank statement
            if not self.force and not self._validate_bank_statement_text(text):
                if self.verbose:
                    print("Validation failed. Extracted text sample:")
                    print(text[:1000])
                raise ValueError("PDF does not appear to be a Bank Leumi statement (use --force to bypass)")
            
            # Parse transactions
            if self.verbose:
                print("Attempting to parse transactions...")
            
            transactions = self.parse_transactions(text)
            
            if self.verbose:
                print(f"Found {len(transactions)} raw transactions")
            
            if not transactions:
                if self.verbose:
                    print("No transactions found. Text lines sample:")
                    lines = text.split('\n')[:20]  # First 20 lines
                    for i, line in enumerate(lines):
                        print(f"Line {i+1}: {line.strip()}")
                raise ValueError("No transactions found in the PDF. Please check the file format.")
            
            # Validate transactions
            valid_transactions = self._validate_transactions(transactions)
            
            if not valid_transactions:
                raise ValueError("No valid transactions found after validation")
            
            # Save to CSV
            self.save_to_csv(valid_transactions, csv_path)
            
            print(f"Successfully converted {len(valid_transactions)} transactions")
            if len(valid_transactions) < len(transactions):
                print(f"Note: {len(transactions) - len(valid_transactions)} invalid transactions were filtered out")
            print(f"CSV file saved: {csv_path}")
            
        except Exception as e:
            if isinstance(e, (FileNotFoundError, PermissionError, ValueError)):
                raise
            raise Exception(f"Conversion failed: {str(e)}")
    
    def _validate_bank_statement_text(self, text: str) -> bool:
        """Basic validation that text looks like a Bank Leumi statement"""
        # Expanded list of Bank Leumi statement indicators (including reversed Hebrew)
        indicators = [
            'בנק לאומי',      # Bank Leumi full name
            'ימואל קנב',      # Bank Leumi reversed
            'Bank Leumi',      # English name
            'לאומי',          # Short name
            'ימואל',          # Short name reversed
            'תנועות בחשבון',   # Account transactions
            'ןובשחב תועונת',   # Account transactions reversed
            'תנועות',         # Transactions
            'תועונת',         # Transactions reversed
            'חשבון',          # Account
            'ןובשח',          # Account reversed
            'יתרה',           # Balance
            'הרתי',           # Balance reversed
            'תאריך',          # Date
            'ךיראת',          # Date reversed
            'סכום',           # Amount
            'םוכס',           # Amount reversed
            'דוח',            # Report
            'חוד',            # Report reversed
            'עמוד',           # Page
            'דומע',          # Page reversed
            'זכות',           # Credit
            'תוכז',           # Credit reversed
            'חובה',           # Debit
            'הבוח',           # Debit reversed
            'הפקדה',          # Deposit
            'הדקפה',          # Deposit reversed
            'משיכה',          # Withdrawal
            'הכישמ',          # Withdrawal reversed
            'העברה',          # Transfer
            'הרבעה',          # Transfer reversed
        ]
        
        text_lower = text.lower()
        found_indicators = []
        
        for indicator in indicators:
            if indicator.lower() in text_lower:
                found_indicators.append(indicator)
        
        # Require at least 1 indicator (reduced from 2 for less strict validation)
        is_valid = len(found_indicators) >= 1
        
        # For debugging: print what indicators were found if verbose mode
        if hasattr(self, 'verbose') and self.verbose:
            print(f"Found indicators: {found_indicators}")
            print(f"Validation result: {is_valid}")
        
        return is_valid
    
    def _post_process_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Post-process transactions to calculate actual amounts and set types"""
        if not transactions:
            return transactions
        
        # Sort by date first
        transactions.sort(key=lambda x: x['date'])
        
        # Calculate actual transaction amounts based on balance changes
        for i, transaction in enumerate(transactions):
            if i == 0:
                # First transaction: assume the amount is correct as-is
                # But we need to determine the sign based on common patterns
                actual_amount = transaction['raw_amount']
                
                # Apply sign logic based on description patterns
                if self._is_expense_transaction(transaction['description']):
                    actual_amount = -abs(actual_amount)
                else:
                    actual_amount = abs(actual_amount)
            else:
                # Calculate amount from balance difference
                prev_balance = transactions[i-1]['balance']
                current_balance = transaction['balance']
                actual_amount = current_balance - prev_balance
            
            # Set the calculated amount with proper rounding
            transaction['amount'] = round(actual_amount, 2)
            
            # Classify transaction and extract category
            transaction['type'] = self.classify_transaction(transaction['description'], actual_amount)
            transaction['category'] = self.extract_category(transaction['description'])
            
            # Remove the raw_amount field as it's no longer needed
            del transaction['raw_amount']
        
        return transactions
    
    def _is_expense_transaction(self, description: str) -> bool:
        """Determine if a transaction is likely an expense based on description"""
        expense_indicators = [
            'כרטיסי אשראי', 'מכבי', 'משכנתא', 'גמל', 'פיננ', 'עמלות',
            'מס הכנסה', 'פיקדון', 'תשלום', 'העברה דיגיטל'
        ]
        
        income_indicators = [
            'משכורת', 'רבית', 'הפקדת שיק', 'זיכוי', 'החזר'
        ]
        
        # Check for income first
        for indicator in income_indicators:
            if indicator in description:
                return False
        
        # Check for expense indicators
        for indicator in expense_indicators:
            if indicator in description:
                return True
        
        # Default to expense if unsure
        return True
    
    def _validate_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Validate and filter transactions"""
        valid_transactions = []
        
        for transaction in transactions:
            try:
                # Basic validation
                if not all(key in transaction for key in ['date', 'description', 'amount', 'balance']):
                    continue
                
                # Validate date is reasonable
                if not isinstance(transaction['date'], datetime):
                    continue
                
                # Validate amounts are numbers
                if not isinstance(transaction['amount'], (int, float)) or not isinstance(transaction['balance'], (int, float)):
                    continue
                
                # Validate description is not empty
                if not transaction['description'] or not transaction['description'].strip():
                    continue
                
                # Validate amounts are reasonable (not extremely large)
                if abs(transaction['amount']) > 1000000000 or abs(transaction['balance']) > 1000000000:
                    continue
                
                valid_transactions.append(transaction)
                
            except Exception:
                # Skip invalid transactions
                continue
        
        return valid_transactions


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="Convert Bank Leumi PDF statements to CSV format"
    )
    parser.add_argument("input_pdf", help="Path to input PDF file")
    parser.add_argument("output_csv", nargs="?", help="Path to output CSV file (optional)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--force", "-f", action="store_true", help="Force processing even if validation fails")
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input_pdf)
    if not input_path.exists():
        print(f"Error: Input file '{args.input_pdf}' not found")
        sys.exit(1)
    
    if not input_path.suffix.lower() == '.pdf':
        print(f"Error: Input file must be a PDF")
        sys.exit(1)
    
    # Generate output filename if not provided
    if args.output_csv:
        output_path = args.output_csv
    else:
        output_path = input_path.stem + "_transactions.csv"
    
    # Convert PDF to CSV
    converter = BankLeumiPDFParser(verbose=args.verbose, force=args.force)
    
    try:
        if args.verbose:
            print(f"Converting {input_path} to {output_path}")
            print("Running in verbose mode...")
        
        converter.convert_pdf_to_csv(str(input_path), output_path)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()