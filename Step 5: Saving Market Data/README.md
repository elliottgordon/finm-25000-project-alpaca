# Step 5: Saving Market Data

This folder contains all scripts, data, and documentation related to the storage, cleaning, backup, and export of market data collected from Alpaca.

## Overview
Step 5 focuses on efficiently saving, organizing, and maintaining the integrity of your market data for backtesting, analysis, and trading strategy development.

## Folder Structure
- `market_data.db` — Main SQLite database storing all market data.
- `data_backups/` — Automated backups of historical data in CSV and PKL formats, organized by date and asset.
- `exports/` — Exported data files for analysis or sharing.
- `data_export.py` — Script for exporting data from the database to various formats.
- `data_management.py` — Utility script for cleaning, validating, and managing stored data.
- `database_migration.py` — Script for updating or migrating the database schema as needed.

## Key Features
- **Database Storage:** All market data is stored in a structured SQLite database for efficient querying and analysis.
- **File Backups:** Regular backups are created in both CSV and PKL formats for redundancy and portability.
- **Automated Updates:** Scripts are designed to run on a schedule, ensuring data is always up to date.
- **Data Cleaning & Validation:** Utility scripts help maintain data quality and integrity.
- **Backtesting Ready:** Data is organized for easy access by backtesting and analytics scripts.

## Usage
1. **Export Data:**
   - Run `data_export.py` to export data from the database to CSV or PKL files in the `exports/` folder.
2. **Manage Data:**
   - Use `data_management.py` to clean, validate, or update stored data as needed.
3. **Database Migration:**
   - If the database schema changes, use `database_migration.py` to migrate or update tables.

## Best Practices
- Keep only storage, cleaning, and export scripts in this folder.
- Use the provided scripts to automate regular backups and data validation.
- Organize backup and export files by asset and date for easy retrieval.

---
For more details, see the main project README or the assignment instructions.
