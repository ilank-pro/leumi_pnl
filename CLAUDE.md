# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a P&L (Profit & Loss) analysis dashboard project for Bank Leumi financial data. The project includes both a static dashboard with hardcoded data and an interactive dashboard that processes CSV files for dynamic P&L analysis.

## Architecture

- **Two main dashboards**:
  - `bank_leumi_analysis.html`: Static dashboard with hardcoded financial data
  - `pnl_dashboard.html`: Interactive dashboard with CSV upload functionality
- **Charts**: Uses Chart.js library (CDN) for data visualization
- **File processing**: Client-side CSV parsing and data analysis
- **Responsive design**: Mobile-friendly layout with CSS Grid
- **RTL support**: Right-to-left text direction for Hebrew content

## Key Components

### Static Dashboard (`bank_leumi_analysis.html`)
- **Monthly data**: Hardcoded financial data from December 2024 to July 2025
- **Summary statistics**: Total income, expenses, net flow, and current balance
- **Interactive charts**: Line chart for accumulated cash flow, bar chart for monthly comparison
- **Expense analysis**: Top spending categories with amounts

### Interactive P&L Dashboard (`pnl_dashboard.html`)
- **CSV upload**: Drag-and-drop or file selection functionality
- **Data processing**: Client-side CSV parsing and validation
- **Dynamic charts**: Updates based on uploaded data
- **Monthly P&L analysis**: Automatic calculation of monthly profit/loss
- **Expense categorization**: Pie chart showing expense distribution
- **Cumulative tracking**: Line chart showing cumulative profit over time

## File Structure

```
├── pnl_dashboard.html - Interactive P&L dashboard with CSV upload
├── bank_leumi_analysis.html - Static dashboard with hardcoded data
├── data/
│   └── sample_pnl.csv - Sample CSV file showing required format
├── README.md - User documentation
└── CLAUDE.md - Developer documentation
```

## CSV Data Format

The dashboard expects CSV files with the following columns:
- `Date`: Transaction date (YYYY-MM-DD format)
- `Description`: Transaction description
- `Amount`: Transaction amount (positive for income, negative for expenses)
- `Category`: Transaction category
- `Type`: Transaction type (Income/Expense)

## Development Notes

- Both dashboards are self-contained HTML files
- No build process or server required
- Client-side processing only - no data sent to servers
- Uses Hebrew text with RTL layout styling
- Responsive design works on mobile and desktop
- Error handling for invalid CSV files and data formats