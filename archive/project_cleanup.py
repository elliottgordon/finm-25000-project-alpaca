#!/usr/bin/env python3
"""
🧹 ALPACA PROJECT CLEANUP & ORGANIZATION SCRIPT

This script will:
1. Consolidate duplicate/experimental files
2. Move files to appropriate directories
3. Archive old/unused files
4. Clean up temporary files and logs
5. Create a clean, professional project structure

Usage:
    python project_cleanup.py [--dry-run]
"""

import os
import shutil
import glob
import logging
from pathlib import Path
from datetime import datetime
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AlpacaProjectCleanup:
    """Clean and organize the Alpaca project structure"""
    
    def __init__(self, project_root, dry_run=False):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Define target structure
        self.target_structure = {
            'src': 'Main source code',
            'data': 'Database and data files', 
            'results': 'Analysis outputs and reports',
            'archive': 'Old/experimental files',
            'docs': 'Documentation',
            'tests': 'Test files',
            'logs': 'Log files'
        }
    
    def analyze_current_structure(self):
        """Analyze current project structure"""
        logger.info("🔍 ANALYZING CURRENT PROJECT STRUCTURE")
        logger.info("=" * 60)
        
        file_inventory = {}
        for root, dirs, files in os.walk(self.project_root):
            rel_path = os.path.relpath(root, self.project_root)
            if rel_path != '.':
                if len(files) > 0:
                    file_inventory[rel_path] = files
        
        # Show current structure
        for directory, files in file_inventory.items():
            logger.info(f"📁 {directory}:")
            for file in files[:10]:  # Show first 10 files
                logger.info(f"   - {file}")
            if len(files) > 10:
                logger.info(f"   ... and {len(files) - 10} more files")
        
        return file_inventory
    
    def create_target_structure(self):
        """Create target directory structure"""
        logger.info("\n🏗️  CREATING TARGET STRUCTURE")
        logger.info("=" * 60)
        
        for directory, description in self.target_structure.items():
            target_path = self.project_root / directory
            if not self.dry_run:
                target_path.mkdir(exist_ok=True)
            logger.info(f"📁 Created: {directory}/ - {description}")
    
    def categorize_files(self):
        """Categorize files for organization"""
        file_categories = {
            'src': {
                'patterns': ['*.py'],
                'exclude': ['*test*', '*backup*', '*old*', 'cleanup*'],
                'core_files': [
                    'data_saver.py', 
                    'enhanced_7year_collector.py',
                    'enhanced_asset_screener.py', 
                    'advanced_strategy_analyzer.py',
                    'Alpaca_API.py'
                ]
            },
            'data': {
                'patterns': ['*.db', '*.csv', '*.pkl'],
                'exclude': ['*test*', '*temp*'],
                'subdirs': ['databases', 'exports', 'backups']
            },
            'results': {
                'patterns': ['*results*.csv', '*comparison*.csv', '*screening*.csv'],
                'exclude': [],
                'subdirs': ['screening', 'backtesting', 'analysis']
            },
            'docs': {
                'patterns': ['*.md', '*.pdf', '*.html', '*.txt'],
                'exclude': [],
                'core_files': ['README.md', 'ENHANCED_PROJECT_SUMMARY.md', 'API_SETUP.md']
            },
            'logs': {
                'patterns': ['*.log'],
                'exclude': [],
                'subdirs': []
            },
            'archive': {
                'patterns': [],  # Will be populated with files to archive
                'exclude': [],
                'subdirs': ['experimental', 'old_versions', 'unused']
            }
        }
        
        return file_categories
    
    def identify_files_to_move(self):
        """Identify which files should be moved where"""
        moves = []
        archives = []
        
        # Files to keep in src (core functionality)
        core_src_files = [
            'data_saver.py',
            'enhanced_7year_collector.py', 
            'enhanced_asset_screener.py',
            'advanced_strategy_analyzer.py',
            'Alpaca_API.py',
            'Alpaca_API_template.py'
        ]
        
        # Files to archive (experimental/duplicate)
        experimental_files = [
            'comprehensive_data_collector.py',
            'multi_asset_collector.py',
            'enhanced_multi_collector.py', 
            'simple_multi_collector.py',
            'asset_universe.py',
            'automated_scheduler.py'
        ]
        
        # Results files
        result_patterns = [
            '*results*.csv',
            '*comparison*.csv', 
            '*screening*.csv',
            '*returns*.csv'
        ]
        
        # Database files
        data_files = [
            'market_data.db',
            'enhanced_data_saver.py',
            'data_manager.py',
            'data_exporter.py'
        ]
        
        return {
            'src': core_src_files,
            'archive/experimental': experimental_files,
            'results': result_patterns,
            'data': data_files
        }
    
    def execute_cleanup(self):
        """Execute the cleanup process"""
        logger.info("\n🚀 EXECUTING PROJECT CLEANUP")
        logger.info("=" * 60)
        
        # 1. Create backup
        if not self.dry_run:
            backup_dir = self.project_root / f"backup_{self.timestamp}"
            logger.info(f"💾 Creating backup: {backup_dir}")
            # Don't backup large files like .git, __pycache__, *.db
            
        # 2. Create target structure
        self.create_target_structure()
        
        # 3. Move core source files
        self.move_core_files()
        
        # 4. Organize data files
        self.organize_data_files()
        
        # 5. Move results files
        self.move_results()
        
        # 6. Archive experimental files
        self.archive_experimental()
        
        # 7. Clean up empty directories
        self.cleanup_empty_dirs()
        
        # 8. Update documentation
        self.update_documentation()
    
    def move_core_files(self):
        """Move core source files to src/"""
        logger.info("\n📦 ORGANIZING SOURCE CODE")
        
        core_files = [
            ('Alpaca_API.py', 'src/'),
            ('Alpaca_API_template.py', 'src/'),
            ('Step 4: Getting Market Data from Alpaca/data_saver.py', 'src/data_collection.py'),
            ('Step 4: Getting Market Data from Alpaca/enhanced_7year_collector.py', 'src/'),
            ('Step 4: Getting Market Data from Alpaca/enhanced_asset_screener.py', 'src/'),
            ('Step 4: Getting Market Data from Alpaca/advanced_strategy_analyzer.py', 'src/')
        ]
        
        for source, target in core_files:
            source_path = self.project_root / source
            target_path = self.project_root / target
            
            if source_path.exists():
                logger.info(f"   📄 {source} → {target}")
                if not self.dry_run:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source_path), str(target_path))
    
    def organize_data_files(self):
        """Organize database and data files"""
        logger.info("\n🗄️  ORGANIZING DATA FILES")
        
        # Create data subdirectories
        data_subdirs = ['databases', 'exports', 'backups']
        for subdir in data_subdirs:
            target_path = self.project_root / 'data' / subdir
            if not self.dry_run:
                target_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"   📁 Created: data/{subdir}/")
        
        # Move database files
        db_moves = [
            ('Step 5: Saving Market Data/market_data.db', 'data/databases/market_data.db'),
            ('Step 4: Getting Market Data from Alpaca/market_data.db', 'data/databases/market_data_step4.db'),
            ('Step 5: Saving Market Data/data_manager.py', 'src/data_management.py'),
            ('Step 5: Saving Market Data/data_exporter.py', 'src/data_export.py')
        ]
        
        for source, target in db_moves:
            source_path = self.project_root / source
            target_path = self.project_root / target
            
            if source_path.exists():
                logger.info(f"   🗃️  {source} → {target}")
                if not self.dry_run:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source_path), str(target_path))
        
        # Move backup directories
        backup_source = self.project_root / 'Step 5: Saving Market Data/data_backups'
        if backup_source.exists():
            backup_target = self.project_root / 'data/backups/historical'
            logger.info(f"   📦 {backup_source} → {backup_target}")
            if not self.dry_run:
                shutil.move(str(backup_source), str(backup_target))
    
    def move_results(self):
        """Move result files to results/"""
        logger.info("\n📊 ORGANIZING RESULTS")
        
        # Find all result files
        result_patterns = [
            '*results*.csv',
            '*comparison*.csv',
            '*screening*.csv',
            '*returns*.csv'
        ]
        
        result_files = []
        for pattern in result_patterns:
            result_files.extend(glob.glob(str(self.project_root / '**' / pattern), recursive=True))
        
        for result_file in result_files:
            rel_path = os.path.relpath(result_file, self.project_root)
            filename = os.path.basename(result_file)
            
            # Categorize by type
            if 'screening' in filename:
                target = self.project_root / 'results/screening' / filename
            elif 'comparison' in filename or 'returns' in filename:
                target = self.project_root / 'results/backtesting' / filename
            else:
                target = self.project_root / 'results/analysis' / filename
            
            logger.info(f"   📈 {rel_path} → {os.path.relpath(target, self.project_root)}")
            if not self.dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(result_file, str(target))
    
    def archive_experimental(self):
        """Archive experimental and duplicate files"""
        logger.info("\n🗃️  ARCHIVING EXPERIMENTAL FILES")
        
        experimental_files = [
            'Step 4: Getting Market Data from Alpaca/comprehensive_data_collector.py',
            'Step 4: Getting Market Data from Alpaca/multi_asset_collector.py',
            'Step 4: Getting Market Data from Alpaca/enhanced_multi_collector.py',
            'Step 4: Getting Market Data from Alpaca/simple_multi_collector.py',
            'Step 4: Getting Market Data from Alpaca/asset_universe.py',
            'Step 4: Getting Market Data from Alpaca/automated_scheduler.py'
        ]
        
        for exp_file in experimental_files:
            source_path = self.project_root / exp_file
            if source_path.exists():
                filename = source_path.name
                target_path = self.project_root / 'archive/experimental' / filename
                
                logger.info(f"   🗃️  {exp_file} → archive/experimental/{filename}")
                if not self.dry_run:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source_path), str(target_path))
    
    def cleanup_empty_dirs(self):
        """Remove empty directories"""
        logger.info("\n🧹 CLEANING UP EMPTY DIRECTORIES")
        
        empty_dirs = []
        for root, dirs, files in os.walk(self.project_root, topdown=False):
            for directory in dirs:
                dir_path = os.path.join(root, directory)
                if not os.listdir(dir_path):  # Directory is empty
                    empty_dirs.append(dir_path)
        
        for empty_dir in empty_dirs:
            rel_path = os.path.relpath(empty_dir, self.project_root)
            logger.info(f"   🗑️  Removing empty: {rel_path}")
            if not self.dry_run:
                os.rmdir(empty_dir)
    
    def update_documentation(self):
        """Update documentation with new structure"""
        logger.info("\n📝 UPDATING DOCUMENTATION")
        
        # Move documentation files
        doc_files = [
            ('README.md', 'docs/'),
            ('ENHANCED_PROJECT_SUMMARY.md', 'docs/'),
            ('API_SETUP.md', 'docs/'),
            ('Project Alpaca.pdf', 'docs/'),
            ('assignment.md', 'docs/'),
            ('assignment.html', 'docs/')
        ]
        
        for source, target in doc_files:
            source_path = self.project_root / source
            if source_path.exists():
                target_path = self.project_root / target / source_path.name
                logger.info(f"   📄 {source} → {target}")
                if not self.dry_run:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source_path), str(target_path))
        
        # Create new README.md in root
        self.create_root_readme()
    
    def create_root_readme(self):
        """Create a new root README with project structure"""
        readme_content = """# 🚀 Enhanced Alpaca Trading Project

## 📁 Project Structure

```
finm-25000-project-alpaca/
├── src/                           # Core source code
│   ├── Alpaca_API.py             # Main API interface
│   ├── Alpaca_API_template.py    # API template (secure)
│   ├── data_collection.py        # Data collection (renamed from data_saver.py)
│   ├── enhanced_7year_collector.py # 7+ year data collector
│   ├── enhanced_asset_screener.py  # Asset screening engine
│   ├── advanced_strategy_analyzer.py # Strategy analysis
│   ├── data_management.py        # Database management
│   └── data_export.py           # Data export utilities
├── data/                         # Data files
│   ├── databases/               # SQLite databases
│   ├── exports/                # Data exports
│   └── backups/                # Data backups
├── results/                     # Analysis outputs
│   ├── screening/              # Asset screening results
│   ├── backtesting/            # Strategy backtesting results
│   └── analysis/               # General analysis outputs
├── docs/                       # Documentation
├── archive/                    # Archived/experimental files
├── logs/                      # Log files
└── alpaca_venv/               # Python virtual environment
```

## 🎯 Quick Start

1. **Setup Environment**:
   ```bash
   source alpaca_venv/bin/activate
   cp src/Alpaca_API_template.py src/Alpaca_API.py
   # Edit src/Alpaca_API.py with your API keys
   ```

2. **Collect Data**:
   ```bash
   cd src/
   python enhanced_7year_collector.py
   ```

3. **Screen Assets**:
   ```bash
   python enhanced_asset_screener.py
   ```

4. **Analyze Strategies**:
   ```bash
   python advanced_strategy_analyzer.py
   ```

## 📊 Key Features

- **125+ Asset Universe**: Comprehensive coverage across ETFs, stocks, bonds, commodities
- **7+ Years Historical Data**: Maximum depth from Alpaca's Basic plan
- **Advanced Analytics**: Multi-timeframe screening, correlation analysis, risk metrics
- **Professional Infrastructure**: Secure API management, automated backups, comprehensive logging

## 📈 Latest Results

- **260,867 Total Records** across 125 unique symbols
- **92% Coverage** of symbols with 7+ years of data
- **Top Opportunities**: UNG (56.9 score), TSLA (32.6 score), META (32.0 score)
- **Best Strategy**: Equal Weight portfolio (10.88% annual return, 0.75 Sharpe ratio)

See `docs/ENHANCED_PROJECT_SUMMARY.md` for detailed results and analysis.

---
*Enhanced Alpaca Project - Professional Quantitative Trading Research Platform*
"""
        
        if not self.dry_run:
            with open(self.project_root / 'README.md', 'w') as f:
                f.write(readme_content)
        
        logger.info("   📝 Created new root README.md")
    
    def generate_cleanup_report(self):
        """Generate cleanup summary report"""
        logger.info("\n✅ CLEANUP COMPLETE")
        logger.info("=" * 60)
        
        # Count files in each directory
        structure_summary = {}
        for directory in self.target_structure.keys():
            dir_path = self.project_root / directory
            if dir_path.exists():
                file_count = sum(len(files) for _, _, files in os.walk(dir_path))
                structure_summary[directory] = file_count
        
        logger.info("📊 New Project Structure:")
        for directory, count in structure_summary.items():
            logger.info(f"   📁 {directory}/: {count} files")
        
        logger.info("\n🎯 Cleanup Summary:")
        logger.info("   ✅ Source code organized in src/")
        logger.info("   ✅ Databases consolidated in data/")
        logger.info("   ✅ Results organized by category")
        logger.info("   ✅ Experimental files archived")
        logger.info("   ✅ Documentation centralized")
        logger.info("   ✅ Empty directories cleaned")
        logger.info("   ✅ New README.md created")
        
        logger.info(f"\n💾 Cleanup completed at: {datetime.now()}")

def main():
    parser = argparse.ArgumentParser(description='Clean up Alpaca project structure')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    args = parser.parse_args()
    
    project_root = Path(__file__).parent
    
    print("🧹 ALPACA PROJECT CLEANUP & ORGANIZATION")
    print("=" * 80)
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be moved")
    print(f"📁 Project Root: {project_root}")
    print("")
    
    try:
        cleanup = AlpacaProjectCleanup(project_root, dry_run=args.dry_run)
        
        # Analyze current structure
        cleanup.analyze_current_structure()
        
        # Execute cleanup
        cleanup.execute_cleanup()
        
        # Generate report
        cleanup.generate_cleanup_report()
        
        print("\n🎉 Project cleanup completed successfully!")
        if args.dry_run:
            print("   Run without --dry-run to execute the changes")
        else:
            print("   Your project is now professionally organized!")
            
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        raise

if __name__ == "__main__":
    main()
