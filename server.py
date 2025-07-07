#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Server for Bank Leumi P&L Dashboard
Handles PDF upload and processing, serves HTML dashboard
"""

import os
import tempfile
import uuid
from pathlib import Path

try:
    from flask import Flask, request, jsonify, send_from_directory, send_file
    from flask_cors import CORS
except ImportError:
    print("Error: Flask is not installed. Install with: pip install flask flask-cors")
    exit(1)

from pdf2csv import BankLeumiPDFParser

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'pdf', 'csv'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_extension(filename):
    """Get file extension"""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

@app.route('/')
def index():
    """Serve the main dashboard"""
    return send_file('pnl_dashboard.html')

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    """Handle PDF upload and conversion"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not supported. Please upload PDF or CSV files only.'}), 400
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': f'File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB'}), 400
        
        # Get file extension
        file_ext = get_file_extension(file.filename)
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # Save uploaded file
        file.save(file_path)
        
        try:
            if file_ext == 'pdf':
                # Process PDF file
                parser = BankLeumiPDFParser()
                
                # Extract text from PDF
                text = parser.extract_text_from_pdf(file_path)
                
                if not text.strip():
                    return jsonify({'error': 'No text could be extracted from the PDF. Please ensure it\'s a text-based PDF.'}), 400
                
                # Parse transactions
                transactions = parser.parse_transactions(text)
                
                if not transactions:
                    return jsonify({'error': 'No transactions found in the PDF. Please check the file format.'}), 400
                
                # Sort transactions by date
                transactions.sort(key=lambda x: x['date'])
                
                # Convert to CSV format using proper CSV writer
                import io
                import csv as csv_module
                
                output = io.StringIO()
                csv_writer = csv_module.writer(output, quoting=csv_module.QUOTE_MINIMAL)
                
                # Write header
                csv_writer.writerow(["Date", "Description", "Amount", "Balance"])
                
                # Write transactions with proper escaping and rounding
                for transaction in transactions:
                    csv_writer.writerow([
                        transaction['date'].strftime('%Y-%m-%d'),
                        transaction['description'],
                        round(transaction['amount'], 2),
                        round(transaction['balance'], 2)
                    ])
                
                csv_content = output.getvalue()
                output.close()
                
                # Debug: Print first few lines of generated CSV
                print("=== Generated CSV Content (first 500 chars) ===")
                print(csv_content[:500])
                print("=== End CSV Debug ===")
                
                return jsonify({
                    'success': True,
                    'csv_data': csv_content,
                    'transaction_count': len(transactions),
                    'message': f'Successfully processed {len(transactions)} transactions from PDF'
                })
                
            elif file_ext == 'csv':
                # For CSV files, just read and return the content
                with open(file_path, 'r', encoding='utf-8') as f:
                    csv_content = f.read()
                
                # Count lines (approximate transaction count)
                line_count = len(csv_content.strip().split('\n')) - 1  # Minus header
                
                return jsonify({
                    'success': True,
                    'csv_data': csv_content,
                    'transaction_count': max(0, line_count),
                    'message': f'Successfully processed CSV file with {max(0, line_count)} transactions'
                })
        
        finally:
            # Clean up uploaded file
            try:
                os.remove(file_path)
            except OSError:
                pass  # File cleanup failed, but continue
        
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Server is running'})

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({'error': 'File too large'}), 413

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Starting Bank Leumi P&L Dashboard Server...")
    print("=" * 50)
    print(f"📊 Dashboard URL: http://localhost:5001")
    print(f"🔧 API Health Check: http://localhost:5001/health")
    print(f"📁 Upload Endpoint: http://localhost:5001/upload-pdf")
    print("=" * 50)
    print("Features:")
    print("✅ PDF processing with Bank Leumi format support")
    print("✅ CSV file processing")
    print("✅ Hebrew text support")
    print("✅ Automatic transaction classification")
    print("✅ CORS enabled for cross-origin requests")
    print("=" * 50)
    print("Usage:")
    print("1. Navigate to http://localhost:5001 in your browser")
    print("2. Upload a Bank Leumi PDF statement or CSV file")
    print("3. View your P&L analysis")
    print("=" * 50)
    print("Press Ctrl+C to stop the server")
    print()
    
    app.run(debug=True, host='localhost', port=5001)