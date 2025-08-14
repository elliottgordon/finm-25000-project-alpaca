# Step 5: Data Backup and Validation System
# Automated backup scheduler and data integrity checker

import os
import sys
import schedule
import time
import shutil
from datetime import datetime, timedelta
import logging

# Add current directory to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Import our data manager
from data_manager import MarketDataManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup_scheduler.log'),
        logging.StreamHandler()
    ]
)

class BackupScheduler:
    """
    Automated backup and data integrity management system
    """
    
    def __init__(self):
        self.data_manager = MarketDataManager()
        self.backup_retention_days = 30  # Keep backups for 30 days
        logging.info("BackupScheduler initialized")
    
    def daily_backup(self):
        """Create daily backup of all market data"""
        logging.info("Starting daily backup...")
        
        try:
            backup_name = f"daily_backup_{datetime.now().strftime('%Y%m%d')}"
            success = self.data_manager.create_backup(backup_name)
            
            if success:
                logging.info("✅ Daily backup completed successfully")
                self.cleanup_old_backups()
                return True
            else:
                logging.error("❌ Daily backup failed")
                return False
                
        except Exception as e:
            logging.error(f"Error during daily backup: {e}")
            return False
    
    def hourly_validation(self):
        """Perform hourly data integrity checks"""
        logging.info("Starting hourly validation...")
        
        try:
            # Get data summary
            summary = self.data_manager.get_data_summary()
            
            # Check for data issues
            issues = []
            
            if summary.get('total_records', 0) == 0:
                issues.append("No data records found")
            
            # Check if data is recent (within last 24 hours for daily data)
            if summary.get('date_range', {}).get('end'):
                end_date = datetime.fromisoformat(summary['date_range']['end'].replace(' ', 'T'))
                if datetime.now() - end_date > timedelta(days=2):
                    issues.append("Data appears stale (no updates in 2+ days)")
            
            if issues:
                logging.warning(f"Data validation issues found: {', '.join(issues)}")
            else:
                logging.info("✅ Data validation passed")
            
            return len(issues) == 0
            
        except Exception as e:
            logging.error(f"Error during validation: {e}")
            return False
    
    def cleanup_old_backups(self):
        """Remove backups older than retention period"""
        backup_dir = self.data_manager.backup_dir
        cutoff_date = datetime.now() - timedelta(days=self.backup_retention_days)
        
        try:
            if not os.path.exists(backup_dir):
                return
            
            for item in os.listdir(backup_dir):
                item_path = os.path.join(backup_dir, item)
                
                if os.path.isdir(item_path):
                    # Check if directory name contains date
                    if 'backup_' in item:
                        try:
                            # Extract date from backup name
                            date_str = item.split('_')[-1][:8]  # YYYYMMDD format
                            backup_date = datetime.strptime(date_str, '%Y%m%d')
                            
                            if backup_date < cutoff_date:
                                shutil.rmtree(item_path)
                                logging.info(f"Removed old backup: {item}")
                        except (ValueError, IndexError):
                            # Skip if date parsing fails
                            continue
                            
        except Exception as e:
            logging.error(f"Error during backup cleanup: {e}")
    
    def run_scheduler(self):
        """Run the backup scheduler"""
        # Schedule daily backups at 2 AM
        schedule.every().day.at("02:00").do(self.daily_backup)
        
        # Schedule hourly validations
        schedule.every().hour.do(self.hourly_validation)
        
        logging.info("Backup scheduler started")
        logging.info("Daily backups scheduled for 2:00 AM")
        logging.info("Hourly validations scheduled")
        
        # Run initial validation
        self.hourly_validation()
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logging.info("Backup scheduler stopped by user")
                break
            except Exception as e:
                logging.error(f"Error in backup scheduler: {e}")
                time.sleep(60)  # Continue after errors

def main():
    """Run the backup scheduler"""
    scheduler = BackupScheduler()
    
    print("🔄 BACKUP SCHEDULER STARTING")
    print("=" * 50)
    print("Daily backups: 2:00 AM")
    print("Hourly validation: Every hour")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        scheduler.run_scheduler()
    except KeyboardInterrupt:
        print("\n🛑 Backup scheduler stopped")

if __name__ == "__main__":
    main()
