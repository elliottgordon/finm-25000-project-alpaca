#!/usr/bin/env python3
"""
Simple Data Update Scheduler for Step 4
Runs continuously to keep market data updated
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
import pytz
from typing import List, Dict

# Add current directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from comprehensive_data_collector import ComprehensiveDataCollector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

class DataUpdateScheduler:
    """
    Simple scheduler for keeping market data updated
    """
    
    def __init__(self):
        self.collector = ComprehensiveDataCollector()
        self.eastern = pytz.timezone('US/Eastern')
        
        # Scheduling parameters
        self.daily_update_time = "16:00"  # 4 PM ET
        self.weekly_update_day = "sunday"
        self.weekly_update_time = "02:00"  # 2 AM ET
        self.check_interval = 60  # Check every minute
        
        # Track last updates
        self.last_daily_update = None
        self.last_weekly_update = None
        
        logging.info("DataUpdateScheduler initialized")
    
    def should_run_daily_update(self) -> bool:
        """Check if daily update should run"""
        now = self.eastern.localize(datetime.now())
        current_time = now.strftime("%H:%M")
        
        # Check if it's time for daily update
        if current_time == self.daily_update_time:
            # Check if we already ran today
            if self.last_daily_update is None or self.last_daily_update.date() < now.date():
                return True
        
        return False
    
    def should_run_weekly_update(self) -> bool:
        """Check if weekly update should run"""
        now = self.eastern.localize(datetime.now())
        current_day = now.strftime("%A").lower()
        current_time = now.strftime("%H:%M")
        
        # Check if it's time for weekly update
        if current_day == self.weekly_update_day and current_time == self.weekly_update_time:
            # Check if we already ran this week
            if self.last_weekly_update is None or (now - self.last_weekly_update).days >= 7:
                return True
        
        return False
    
    def run_daily_update(self):
        """Run daily incremental update"""
        try:
            logging.info("🔄 Running daily incremental update...")
            results = self.collector.incremental_update()
            
            successful = sum(results.values())
            total = len(results)
            
            logging.info(f"✅ Daily update complete: {successful}/{total} symbols updated")
            self.last_daily_update = self.eastern.localize(datetime.now())
            
        except Exception as e:
            logging.error(f"❌ Daily update failed: {e}")
    
    def run_weekly_update(self):
        """Run weekly full update"""
        try:
            logging.info("📥 Running weekly full data collection...")
            results = self.collector.collect_missing_data()
            
            successful = sum(results.values())
            total = len(results)
            
            logging.info(f"✅ Weekly update complete: {successful}/{total} symbols updated")
            self.last_weekly_update = self.eastern.localize(datetime.now())
            
        except Exception as e:
            logging.error(f"❌ Weekly update failed: {e}")
    
    def run_continuous_scheduler(self):
        """Run the scheduler continuously"""
        logging.info("🚀 Starting continuous data update scheduler...")
        logging.info(f"   Daily updates: {self.daily_update_time} ET")
        logging.info(f"   Weekly updates: {self.weekly_update_day} at {self.weekly_update_time} ET")
        logging.info(f"   Check interval: {self.check_interval} seconds")
        logging.info("   Press Ctrl+C to stop")
        
        try:
            while True:
                now = self.eastern.localize(datetime.now())
                
                # Check for daily update
                if self.should_run_daily_update():
                    self.run_daily_update()
                
                # Check for weekly update
                if self.should_run_weekly_update():
                    self.run_weekly_update()
                
                # Log status every hour
                if now.minute == 0:
                    logging.info(f"📊 Scheduler running - {now.strftime('%Y-%m-%d %H:%M:%S')} ET")
                    if self.last_daily_update:
                        logging.info(f"   Last daily update: {self.last_daily_update.strftime('%Y-%m-%d %H:%M:%S')}")
                    if self.last_weekly_update:
                        logging.info(f"   Last weekly update: {self.last_weekly_update.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Wait before next check
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logging.info("⏹️  Scheduler stopped by user")
        except Exception as e:
            logging.error(f"❌ Scheduler error: {e}")
            raise

def main():
    """Main function"""
    print("🚀 DATA UPDATE SCHEDULER")
    print("=" * 40)
    print("This will run continuously to keep your market data updated")
    print("=" * 40)
    
    scheduler = DataUpdateScheduler()
    
    print("\n📅 SCHEDULE:")
    print(f"   Daily Updates: {scheduler.daily_update_time} ET (incremental)")
    print(f"   Weekly Updates: {scheduler.weekly_update_day} at {scheduler.weekly_update_time} ET (full)")
    print(f"   Check Interval: {scheduler.check_interval} seconds")
    
    print("\n🎯 OPTIONS:")
    print("   1. Run continuous scheduler")
    print("   2. Run single daily update now")
    print("   3. Run single weekly update now")
    print("   4. Check data status")
    print("   5. Exit")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == '1':
        print("\n⏰ Starting continuous scheduler...")
        scheduler.run_continuous_scheduler()
        
    elif choice == '2':
        print("\n🔄 Running daily update now...")
        scheduler.run_daily_update()
        
    elif choice == '3':
        print("\n📥 Running weekly update now...")
        scheduler.run_weekly_update()
        
    elif choice == '4':
        print("\n📊 Checking data status...")
        gaps = scheduler.collector.calculate_data_gaps(scheduler.collector.load_watchlist())
        
        missing = sum(1 for g in gaps.values() if g['status'] == 'missing')
        needs_update = sum(1 for g in gaps.values() if g['status'] == 'needs_update')
        current = sum(1 for g in gaps.values() if g['status'] == 'current')
        
        print(f"   Total Symbols: {len(gaps)}")
        print(f"   Missing Data: {missing}")
        print(f"   Needs Update: {needs_update}")
        print(f"   Current: {current}")
        
        # Data quality report
        quality_report = scheduler.collector.get_data_quality_report()
        if quality_report:
            print(f"\n   Total Records: {quality_report['total_records']:,}")
            print(f"   Data Completeness: {quality_report['data_completeness']:.1f}%")
        
    elif choice == '5':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
