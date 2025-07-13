#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XLS to CSV Converter for Bank Leumi Statements
Converts Bank Leumi XLS statements (HTML format) to CSV format compatible with PNL Dashboard
"""

import argparse
import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: BeautifulSoup4 is not installed. Install with: pip install beautifulsoup4")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("Error: pandas is not installed. Install with: pip install pandas")
    sys.exit(1)


class BankLeumiXLSParser:
    """Parser for Bank Leumi XLS statements (HTML format)"""
    
    def __init__(self, verbose=False, force=False):
        self.verbose = verbose
        self.force = force
        
        # Hebrew month names mapping
        self.hebrew_months = {
            'ינואר': 1, 'פברואר': 2, 'מרץ': 3, 'אפריל': 4,
            'מאי': 5, 'יוני': 6, 'יולי': 7, 'אוגוסט': 8,
            'ספטמבר': 9, 'אוקטובר': 10, 'נובמבר': 11, 'דצמבר': 12
        }
        
        # Category mappings (similar to PDF parser)
        self.category_map = {
            'לאומי ויזא': 'כרטיסי אשראי',
            'כרטיסי אשראי': 'כרטיסי אשראי',
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
            'עמל.ערוץ יש': 'עמלות בנק',
            'הפקדת שיק': 'הפקדות',
            'שיק': 'שיקים',
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
    
    def extract_html_from_xls(self, xls_path: str) -> str:
        """Extract HTML content from XLS file"""
        try:
            # Validate file exists and is readable
            if not os.path.exists(xls_path):
                raise FileNotFoundError(f"XLS file not found: {xls_path}")
            
            if not os.access(xls_path, os.R_OK):
                raise PermissionError(f"Cannot read XLS file: {xls_path}")
            
            # Check file size (avoid processing very large files)
            file_size = os.path.getsize(xls_path)
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                raise ValueError(f"XLS file too large: {file_size / (1024*1024):.1f}MB (max 50MB)")
            
            if file_size == 0:
                raise ValueError("XLS file is empty")
            
            # Read the HTML content from the XLS file
            with open(xls_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            if not html_content.strip():
                raise ValueError("XLS file contains no content")
            
            # Debug output if verbose
            if self.verbose:
                print(f"Successfully extracted HTML content ({len(html_content)} characters)")
                print("First 500 characters of HTML:")
                print("-" * 50)
                print(html_content[:500])
                print("-" * 50)
            
            return html_content
            
        except Exception as e:
            if isinstance(e, (FileNotFoundError, PermissionError, ValueError)):
                raise
            raise Exception(f"Unexpected error reading XLS file: {str(e)}")
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string in various formats"""
        if not date_str:
            return None
            
        # Remove extra whitespace
        date_str = date_str.strip()
        
        # Try different date formats
        date_formats = [
            "%d/%m/%y", "%d/%m/%Y", "%d-%m-%Y", "%d-%m-%y",
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
        
        return None
    
    def parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string and return float"""
        if not amount_str:
            return None
        
        # Clean the amount string
        amount_str = amount_str.strip()
        
        # Remove currency symbols and commas
        amount_str = amount_str.replace("₪", "").replace("$", "").replace(",", "").strip()
        
        # Handle empty string after cleaning
        if not amount_str or amount_str == "0.00":
            return 0.0
        
        try:
            return float(amount_str)
        except ValueError:
            # Try to handle malformed numbers
            # Remove any remaining non-numeric characters except decimal point
            cleaned = re.sub(r'[^\d\.]', '', amount_str)
            if cleaned:
                try:
                    return float(cleaned)
                except ValueError:
                    return None
            return None
    
    def extract_category(self, description: str) -> str:
        """Extract category from transaction description"""
        for keyword, category in self.category_map.items():
            if keyword in description:
                return category
        return "אחר"
    
    def parse_transactions(self, html_content: str) -> List[Dict]:
        """Parse transactions from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            transactions = []
            
            # Find the table with transactions
            # Look for table with Hebrew headers
            table = None
            for t in soup.find_all('table'):
                # Check if this table has transaction headers
                headers = t.find_all('td', class_='xlHeader')
                if len(headers) >= 6:  # Should have at least 6 columns
                    header_texts = [h.get_text(strip=True) for h in headers]
                    if any('תאריך' in text for text in header_texts):
                        table = t
                        break
            
            if not table:
                raise ValueError("Could not find transaction table in HTML")
            
            if self.verbose:
                print("Found transaction table")
            
            # Find all transaction rows (skip header row)
            rows = table.find_all('tr')
            header_found = False
            
            for row in rows:
                cells = row.find_all('td')
                
                # Skip header row
                if not header_found:
                    if any(cell.get('class') and 'xlHeader' in cell.get('class', []) for cell in cells):
                        header_found = True
                        if self.verbose:
                            headers = [cell.get_text(strip=True) for cell in cells]
                            print(f"Headers found: {headers}")
                        continue
                    continue
                
                # Process transaction rows
                if len(cells) >= 7:  # Should have at least 7 columns
                    try:
                        # Extract data from cells
                        date_str = cells[0].get_text(strip=True)  # תאריך
                        # cells[1] is תאריך ערך (value date) - we can skip this
                        description = cells[2].get_text(strip=True)  # תיאור
                        # cells[3] is אסמכתא (reference) - we can skip this
                        debit_str = cells[4].get_text(strip=True)  # בחובה
                        credit_str = cells[5].get_text(strip=True)  # בזכות
                        balance_str = cells[6].get_text(strip=True)  # היתרה בש"ח
                        
                        # Parse date
                        date = self.parse_date(date_str)
                        if not date:
                            if self.verbose:
                                print(f"Skipping row with invalid date: {date_str}")
                            continue
                        
                        # Parse amounts
                        debit = self.parse_amount(debit_str)
                        credit = self.parse_amount(credit_str)
                        balance = self.parse_amount(balance_str)
                        
                        if balance is None:
                            if self.verbose:
                                print(f"Skipping row with invalid balance: {balance_str}")
                            continue
                        
                        # Calculate transaction amount
                        # If debit > 0, it's a negative amount (expense)
                        # If credit > 0, it's a positive amount (income)
                        if debit and debit > 0:
                            amount = -debit
                        elif credit and credit > 0:
                            amount = credit
                        else:
                            # Edge case: both are 0 or invalid
                            if self.verbose:
                                print(f"Skipping row with no valid amount: debit={debit_str}, credit={credit_str}")
                            continue
                        
                        # Clean description
                        description = description.strip()
                        if not description:
                            description = "תנועה"
                        
                        transaction = {
                            'date': date,
                            'description': description,
                            'amount': round(amount, 2),
                            'balance': round(balance, 2),
                            'category': self.extract_category(description)
                        }
                        
                        transactions.append(transaction)
                        
                        if self.verbose:
                            print(f"Parsed: {date.strftime('%Y-%m-%d')} | {description[:30]} | {amount} | {balance}")
                    
                    except Exception as e:
                        if self.verbose:
                            print(f"Error processing row: {e}")
                        continue
            
            if self.verbose:
                print(f"Total transactions parsed: {len(transactions)}")
            
            # Sort transactions by date (oldest first)
            transactions.sort(key=lambda x: x['date'])
            
            return transactions
            
        except Exception as e:
            raise Exception(f"Failed to parse transactions from HTML: {str(e)}")
    
    def save_to_csv(self, transactions: List[Dict], output_path: str) -> None:
        """Save transactions to CSV file"""
        if not transactions:
            raise ValueError("No transactions to save")
        
        # Create CSV data
        csv_data = []
        for transaction in transactions:
            csv_data.append({
                'Date': transaction['date'].strftime('%Y-%m-%d'),
                'Description': transaction['description'],
                'Amount': transaction['amount'],
                'Balance': transaction['balance']
            })
        
        # Write to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Date', 'Description', 'Amount', 'Balance']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
    
    def convert_xls_to_csv(self, xls_path: str, csv_path: str) -> None:
        """Main conversion function"""
        try:
            # Validate input parameters
            if not xls_path or not isinstance(xls_path, str):
                raise ValueError("Invalid XLS path provided")
            
            if not csv_path or not isinstance(csv_path, str):
                raise ValueError("Invalid CSV path provided")
            
            # Extract HTML from XLS file
            html_content = self.extract_html_from_xls(xls_path)
            
            if not html_content.strip():
                raise ValueError("No HTML content could be extracted from the XLS file")
            
            # Basic validation that this looks like a bank statement
            if not self.force and not self._validate_bank_statement_html(html_content):
                if self.verbose:
                    print("Validation failed. HTML content sample:")
                    print(html_content[:1000])
                raise ValueError("XLS does not appear to be a Bank Leumi statement (use --force to bypass)")
            
            # Parse transactions
            if self.verbose:
                print("Attempting to parse transactions...")
            
            transactions = self.parse_transactions(html_content)
            
            if self.verbose:
                print(f"Found {len(transactions)} transactions")
            
            if not transactions:
                if self.verbose:
                    print("No transactions found.")
                raise ValueError("No transactions found in the XLS file. Please check the file format.")
            
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
    
    def _validate_bank_statement_html(self, html_content: str) -> bool:
        """Basic validation that HTML looks like a Bank Leumi statement"""
        indicators = [
            'בנק לאומי',      # Bank Leumi full name
            'Bank Leumi',      # English name
            'לאומי',          # Short name
            'תנועות בחשבון',   # Account transactions
            'תנועות',         # Transactions
            'חשבון',          # Account
            'יתרה',           # Balance
            'תאריך',          # Date
            'סכום',           # Amount
            'זכות',           # Credit
            'חובה',           # Debit
            'בחובה',          # In debit
            'בזכות',          # In credit
            'היתרה',          # The balance
            'תיאור',          # Description
        ]
        
        html_lower = html_content.lower()
        found_indicators = []
        
        for indicator in indicators:
            if indicator.lower() in html_lower:
                found_indicators.append(indicator)
        
        # Require at least 3 indicators for validation
        is_valid = len(found_indicators) >= 3
        
        if self.verbose:
            print(f"Found indicators: {found_indicators}")
            print(f"Validation result: {is_valid}")
        
        return is_valid
    
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
        description="Convert Bank Leumi XLS statements to CSV format"
    )
    parser.add_argument("input_xls", help="Path to input XLS file")
    parser.add_argument("output_csv", nargs="?", help="Path to output CSV file (optional)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--force", "-f", action="store_true", help="Force processing even if validation fails")
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input_xls)
    if not input_path.exists():
        print(f"Error: Input file '{args.input_xls}' not found")
        sys.exit(1)
    
    if not input_path.suffix.lower() == '.xls':
        print(f"Error: Input file must be an XLS file")
        sys.exit(1)
    
    # Generate output filename if not provided
    if args.output_csv:
        output_path = args.output_csv
    else:
        output_path = input_path.stem + "_transactions.csv"
    
    # Convert XLS to CSV
    converter = BankLeumiXLSParser(verbose=args.verbose, force=args.force)
    
    try:
        if args.verbose:
            print(f"Converting {input_path} to {output_path}")
            print("Running in verbose mode...")
        
        converter.convert_xls_to_csv(str(input_path), output_path)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()