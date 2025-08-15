#!/usr/bin/env python3
"""
Project Directory Cleanup and Organization Script
Moves non-essential files to archive while keeping core functionality
"""

import os
import shutil
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class ProjectOrganizer:
    def __init__(self, project_root):
        self.project_root = project_root
        self.archive_root = os.path.join(project_root, 'archive')
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def move_file(self, source, destination_dir, filename=None):
        """Move file to destination directory"""
        if not os.path.exists(source):
            logging.warning(f"Source file not found: {source}")
            return
            
        os.makedirs(destination_dir, exist_ok=True)
        
        if filename is None:
            filename = os.path.basename(source)
        
        destination = os.path.join(destination_dir, filename)
        
        try:
            shutil.move(source, destination)
            logging.info(f"Moved: {os.path.basename(source)} -> archive/{os.path.relpath(destination_dir, self.archive_root)}/")
        except Exception as e:
            logging.error(f"Error moving {source}: {e}")
    
    def organize_project(self):
        """Main organization function"""
        print("🧹 Project Directory Cleanup & Organization")
        print("=" * 60)
        
        # 1. Move development/debugging files
        dev_files_dir = os.path.join(self.archive_root, 'development_files')
        
        # Root level development files
        dev_files = [
            'database_inspector.py',
            'market_data.ipynb',
            'Alpaca_API_template.py'  # Keep original, move template
        ]
        
        for file in dev_files:
            self.move_file(os.path.join(self.project_root, file), dev_files_dir)
        
        # 2. Move logs and temporary outputs
        logs_dir = os.path.join(self.archive_root, 'logs_and_outputs')
        
        # Step 4 logs
        step4_path = os.path.join(self.project_root, 'Step 4: Getting Market Data from Alpaca')
        log_files_step4 = [
            'enhanced_multi_collector.log'
        ]
        for file in log_files_step4:
            self.move_file(os.path.join(step4_path, file), logs_dir)
        
        # Step 5 logs
        step5_path = os.path.join(self.project_root, 'Step 5: Saving Market Data')
        log_files_step5 = [
            'backup_scheduler.log',
            'data_manager.log', 
            'enhanced_data_saver.log'
        ]
        for file in log_files_step5:
            self.move_file(os.path.join(step5_path, file), logs_dir)
            
        # Step 7 logs
        step7_path = os.path.join(self.project_root, 'Step 7: Trading Strategy')
        log_files_step7 = [
            'trading_strategy.log'
        ]
        for file in log_files_step7:
            self.move_file(os.path.join(step7_path, file), logs_dir)
        
        # 3. Move generated reports and analysis files
        reports_dir = os.path.join(self.archive_root, 'generated_reports')
        
        # Step 7 generated files
        report_files = [
            'asset_screening_20250814_224507.png',
            'multi_asset_portfolio_20250814_224647.csv',
            'multi_asset_portfolio_20250814_224803.csv', 
            'multi_asset_trades_20250814_224803.csv',
            'screening_results_20250814_224522.csv',
            'strategy_analysis_SPY_20250814_223016.png',
            'STEP_7_COMPLETION_SUMMARY.html',
            'STEP_7_COMPLETION_SUMMARY_files'
        ]
        
        for file in report_files:
            source_path = os.path.join(step7_path, file)
            if os.path.exists(source_path):
                if os.path.isdir(source_path):
                    shutil.move(source_path, os.path.join(reports_dir, file))
                    logging.info(f"Moved directory: {file} -> archive/generated_reports/")
                else:
                    self.move_file(source_path, reports_dir)
        
        # 4. Move deprecated/alternative scripts
        deprecated_dir = os.path.join(self.archive_root, 'deprecated_scripts')
        
        # Step 4 deprecated scripts
        deprecated_step4 = [
            'multi_asset_collector.py',
            'simple_multi_collector.py',
            'real_time_data.py',
            'scheduler.py'
        ]
        for file in deprecated_step4:
            self.move_file(os.path.join(step4_path, file), deprecated_dir)
        
        # Step 5 deprecated scripts
        deprecated_step5 = [
            'backup_scheduler.py',
            'database_migration.py'
        ]
        for file in deprecated_step5:
            self.move_file(os.path.join(step5_path, file), deprecated_dir)
        
        # Step 7 deprecated/analysis scripts
        deprecated_step7 = [
            'strategy_analyzer.py',  # Keep core strategy, move analyzer
            'strategy_diagnostics.py'  # Move diagnostics
        ]
        for file in deprecated_step7:
            self.move_file(os.path.join(step7_path, file), deprecated_dir)
        
        # 5. Move __pycache__ directories
        pycache_dirs = [
            os.path.join(self.project_root, '__pycache__'),
            os.path.join(step4_path, '__pycache__'),
            os.path.join(step7_path, '__pycache__')
        ]
        
        for pycache_dir in pycache_dirs:
            if os.path.exists(pycache_dir):
                destination = os.path.join(dev_files_dir, f'pycache_{os.path.basename(os.path.dirname(pycache_dir)) or "root"}')
                try:
                    shutil.move(pycache_dir, destination)
                    logging.info(f"Moved: __pycache__ -> archive/development_files/")
                except Exception as e:
                    logging.error(f"Error moving __pycache__: {e}")
        
        # 6. Create README for archive
        self.create_archive_readme()
        
        print(f"\n✅ Organization complete! Files archived to: ./archive/")
        self.show_final_structure()
    
    def create_archive_readme(self):
        """Create README for archive directory"""
        readme_content = f"""# Archive Directory - FINM 25000 Project Alpaca
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This directory contains files that were moved during project cleanup and organization.

## Directory Structure:

### development_files/
- Development and debugging scripts
- Database inspector utilities  
- Jupyter notebooks
- __pycache__ directories
- Template files

### logs_and_outputs/
- Log files from data collection
- Strategy execution logs
- System operation logs

### generated_reports/
- Analysis charts and graphs
- CSV export files
- HTML reports
- Performance visualizations

### deprecated_scripts/
- Alternative implementation attempts
- Superseded utility scripts
- Analysis and diagnostic tools
- Backup and migration scripts

## Core Project Files (Kept in Main Directory):
- Alpaca_API.py - Main API integration
- Step 4: Getting Market Data from Alpaca/
  - data_saver.py - Core data collection
  - enhanced_multi_collector.py - Multi-asset collector
  - asset_universe.py - Asset definitions
  - automated_scheduler.py - Automation system
- Step 5: Saving Market Data/
  - data_manager.py - Database management
  - enhanced_data_saver.py - Enhanced data saving
  - data_exporter.py - Export utilities
- Step 7: Trading Strategy/
  - trading_strategy.py - Core strategy implementation
  - asset_screener.py - Asset screening system
  - multi_asset_strategy.py - Portfolio management

All archived files are preserved and can be restored if needed.
"""
        
        readme_path = os.path.join(self.archive_root, 'README.md')
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        logging.info("Created archive README.md")
    
    def show_final_structure(self):
        """Display the final clean directory structure"""
        print(f"\n📁 FINAL PROJECT STRUCTURE:")
        print("=" * 40)
        
        # Essential files that remain
        essential_structure = {
            "Root Level": [
                "Alpaca_API.py",
                "PROJECT_SUMMARY_REPORT.py", 
                "README.md",
                "Project Alpaca.pdf",
                "assignment.md"
            ],
            "Step 4: Getting Market Data from Alpaca": [
                "data_saver.py",
                "enhanced_multi_collector.py",
                "asset_universe.py",
                "automated_scheduler.py",
                "market_data.db"
            ],
            "Step 5: Saving Market Data": [
                "data_manager.py",
                "enhanced_data_saver.py", 
                "data_exporter.py",
                "market_data.db",
                "data_backups/",
                "exports/"
            ],
            "Step 7: Trading Strategy": [
                "trading_strategy.py",
                "asset_screener.py",
                "multi_asset_strategy.py",
                "STEP_7_COMPLETION_SUMMARY.md"
            ]
        }
        
        for directory, files in essential_structure.items():
            print(f"\n{directory}:")
            for file in files:
                print(f"  ✓ {file}")
        
        print(f"\n📦 ARCHIVED (./archive/):")
        print("  📁 development_files/")
        print("  📁 logs_and_outputs/")
        print("  📁 generated_reports/")
        print("  📁 deprecated_scripts/")

def main():
    """Run the organization process"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    organizer = ProjectOrganizer(project_root)
    organizer.organize_project()

if __name__ == "__main__":
    main()
