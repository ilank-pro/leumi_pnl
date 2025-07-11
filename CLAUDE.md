# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a P&L (Profit & Loss) analysis dashboard project for Bank Leumi financial data. The project provides a complete solution for analyzing financial statements through both PDF processing and CSV file analysis, with both server-side PDF conversion and client-side data processing capabilities.

## Architecture

### Core Components
- **Flask Server** (`server.py`): Handles PDF upload, processing, and serves the dashboard
- **PDF Parser** (`pdf2csv.py`): Converts Bank Leumi PDF statements to CSV format
- **Interactive Dashboard** (`pnl_dashboard.html`): Main web interface with CSV/PDF upload
- **Static Dashboard** (`bank_leumi_analysis.html`): Reference dashboard with hardcoded data

### Technology Stack
- **Backend**: Flask with CORS support for file uploads
- **PDF Processing**: pdfplumber for text extraction with Hebrew RTL support
- **Frontend**: Vanilla JavaScript with Chart.js for visualization
- **Styling**: CSS Grid with responsive design and RTL Hebrew support
- **Data Processing**: Client-side CSV parsing with smart transaction classification

## Development Commands

### Environment Setup
```bash
# Initial setup (creates venv and installs dependencies)
./setup_dev.sh

# Manual setup alternative
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Server Operations
```bash
# Start server with auto-setup
./start_server.sh

# Manual server start
source venv/bin/activate
python server.py

# Server runs on http://localhost:5001
# Health check: http://localhost:5001/health
```

### PDF Processing (Standalone)
```bash
# Convert PDF to CSV directly
python pdf2csv.py input.pdf output.csv

# With verbose debugging
python pdf2csv.py input.pdf output.csv --verbose
```

## Data Flow Architecture

### PDF Processing Pipeline
1. **Upload**: PDF file uploaded via `/upload-pdf` endpoint
2. **Validation**: File type and Bank Leumi format validation
3. **Text Extraction**: pdfplumber extracts Hebrew text with RTL handling
4. **Transaction Parsing**: Regex patterns extract transactions (balance amount reference description date date)
5. **CSV Generation**: Proper CSV escaping with UTF-8 encoding
6. **Response**: JSON with CSV data and transaction count

### CSV Processing Pipeline
1. **Client Upload**: FileReader processes CSV with UTF-8 encoding
2. **Format Detection**: Identifies Bank Format V1/V2 or Standard format
3. **Line Ending Handling**: Normalizes Windows (\r\n) and Unix (\n) line endings
4. **Data Classification**: Smart transaction categorization (Income/Expense/Transfer)
5. **Monthly Aggregation**: Groups by month for P&L analysis
6. **Chart Generation**: Chart.js renders interactive visualizations

## Key Features Implementation

### Date Range Filtering
- **Filter Controls**: Start/end month dropdowns with Hebrew locale
- **Active Filtering**: `dateFilterActive` flag and `filteredData` array
- **UI Integration**: Filter status display and reset functionality
- **Data Processing**: Modified `processData()` function handles filtered datasets

### Smart Transaction Classification
- **Bank Format V1**: DD/MM/YY dates with balance-based amount calculation
- **Bank Format V2**: YYYY-MM-DD dates with signed amounts
- **Standard Format**: User-defined categories and types
- **Hebrew Text Processing**: RTL text handling and character encoding

### File Processing Support
```javascript
// Supported CSV formats
Bank V1: Date,Description,Amount,Balance (DD/MM/YY)
Bank V2: Date,Description,Amount,Balance (YYYY-MM-DD) 
Standard: Date,Description,Amount,Category,Type
```

## Code Organization

### Critical Functions
- **`parseCSV()`**: Main CSV processing entry point with format detection
- **`processData()`**: Core data aggregation with date filtering support  
- **`populateDateFilters()`**: Builds month selection dropdowns from data
- **`applyDateFilter()`** / **`resetDateFilter()`**: Filter management
- **`BankLeumiPDFParser.parse_transactions()`**: PDF transaction extraction

### Global State Management
```javascript
// Core data arrays
let pnlData = [];              // All transaction data
let filteredData = null;       // Date-filtered subset
let monthlyData = {};          // Aggregated monthly P&L
let expensesByCategory = {};   // Category breakdowns
let availableCategories = []; // Unique category list

// Filter state
let dateFilterActive = false; // Whether filtering is active
```

### Hebrew/RTL Considerations
- All text uses `direction: rtl` CSS
- PDF parsing handles reversed Hebrew text
- Date formatting uses Hebrew locale (`he-IL`)
- Number formatting includes RTL-aware currency symbols

## Server Configuration

### Flask Routes
- `GET /`: Serves main dashboard (`pnl_dashboard.html`)
- `POST /upload-pdf`: Handles PDF/CSV file uploads
- `GET /health`: Server health check endpoint

### File Upload Handling
- **Allowed formats**: PDF, CSV
- **Size limit**: 16MB maximum
- **Processing**: Temporary file storage with UUID naming
- **Error handling**: Comprehensive validation and cleanup

## Dependencies

### Python (requirements.txt)
- `flask>=2.3.0`: Web server framework
- `flask-cors>=4.0.0`: Cross-origin request handling  
- `pdfplumber>=0.11.0`: PDF text extraction
- `pandas>=2.0.0`: Data manipulation utilities

### JavaScript (CDN)
- Chart.js 3.9.1: Data visualization library
- No build process required - all dependencies loaded via CDN

## Debugging and Troubleshooting

### Common Issues
- **Line endings**: CSV files with Windows line endings require normalization
- **Hebrew encoding**: Ensure UTF-8 encoding for Hebrew text processing
- **PDF validation**: Bank Leumi format detection via Hebrew text indicators
- **Number precision**: Server-side rounding prevents client-side parsing errors

### Debug Features
- Extensive console logging in `parseCSV()` function
- Server debug output for PDF processing in `server.py`
- CSV content validation with character code analysis
- PDF text extraction debugging with verbose mode