# Automated Daily Data Collection Scheduler
# Runs asynchronously to update market data daily after market close

import os
import sys
import schedule
import time
import logging
from datetime import datetime, timedelta
import asyncio
import subprocess

# Add parent directory to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from asset_universe import get_priority_universe

# Setup logging for scheduler
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automated_scheduler.log'),
        logging.StreamHandler()
    ]
)

class AutomatedDataScheduler:
    """
    Automated scheduler for daily market data collection
    Runs after market close and handles multiple asset tiers
    """
    
    def __init__(self):
        self.python_path = os.path.join(PARENT_DIR, 'alpaca_venv', 'bin', 'python')
        self.collector_script = os.path.join(CURRENT_DIR, 'enhanced_multi_collector.py')
        self.is_running = False
        
        logging.info("Automated Data Scheduler initialized")
    
    def is_market_day(self):
        """Check if today is a market day (Monday-Friday, excluding holidays)"""
        today = datetime.now()
        
        # Skip weekends
        if today.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # TODO: Add holiday checking logic if needed
        # For now, assume weekdays are market days
        return True
    
    def run_data_collection(self, tier='all'):
        """Run data collection for specified tier"""
        if self.is_running:
            logging.warning("Collection already running, skipping")
            return False
        
        if not self.is_market_day():
            logging.info("Market closed today, skipping collection")
            return False
        
        try:
            self.is_running = True
            start_time = datetime.now()
            
            logging.info(f"🚀 Starting automated data collection - Tier: {tier}")
            
            # Run the enhanced multi collector
            result = subprocess.run(
                [self.python_path, self.collector_script],
                cwd=CURRENT_DIR,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if result.returncode == 0:
                logging.info(f"✅ Data collection completed successfully in {duration:.1f}s")
                logging.info(f"Output: {result.stdout[-500:]}")  # Last 500 chars of output
                return True
            else:
                logging.error(f"❌ Data collection failed with code {result.returncode}")
                logging.error(f"Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logging.error("❌ Data collection timed out after 30 minutes")
            return False
        except Exception as e:
            logging.error(f"❌ Data collection failed with exception: {str(e)}")
            return False
        finally:
            self.is_running = False
    
    def run_tier_2_collection(self):
        """Run collection for Tier 2 assets (bonds)"""
        logging.info("📊 Tier 2 Collection: Bonds")
        return self.run_data_collection('tier_2')
    
    def run_tier_3_collection(self):
        """Run collection for Tier 3 assets (commodities)"""  
        logging.info("📊 Tier 3 Collection: Commodities")
        return self.run_data_collection('tier_3')
    
    def run_emergency_collection(self):
        """Emergency collection that can be triggered manually"""
        logging.info("🚨 Emergency collection triggered")
        return self.run_data_collection('emergency')
    
    def setup_schedule(self):
        """Setup the automated collection schedule"""
        # Main collection: Daily at 5:30 PM ET (after market close at 4 PM)
        schedule.every().monday.at("17:30").do(self.run_data_collection, 'daily')
        schedule.every().tuesday.at("17:30").do(self.run_data_collection, 'daily')
        schedule.every().wednesday.at("17:30").do(self.run_data_collection, 'daily')
        schedule.every().thursday.at("17:30").do(self.run_data_collection, 'daily')
        schedule.every().friday.at("17:30").do(self.run_data_collection, 'daily')
        
        # Weekend maintenance: Extended collection on Sunday evening
        schedule.every().sunday.at("20:00").do(self.run_tier_2_collection)
        schedule.every().sunday.at("20:30").do(self.run_tier_3_collection)
        
        # Backup collection: Early morning check
        schedule.every().day.at("06:00").do(self.run_data_collection, 'backup')
        
        logging.info("📅 Collection schedule configured:")
        logging.info("   - Weekdays at 5:30 PM ET (main collection)")
        logging.info("   - Daily at 6:00 AM ET (backup check)")
        logging.info("   - Sunday at 8:00 PM ET (extended collection)")
    
    def run_scheduler(self):
        """Run the scheduler continuously"""
        self.setup_schedule()
        
        logging.info("⚡ Automated scheduler started")
        logging.info("   Press Ctrl+C to stop")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logging.info("🛑 Scheduler stopped by user")
        except Exception as e:
            logging.error(f"❌ Scheduler error: {str(e)}")
    
    def test_collection(self):
        """Test the collection system"""
        logging.info("🧪 Testing collection system...")
        success = self.run_data_collection('test')
        
        if success:
            logging.info("✅ Test successful - scheduler ready for deployment")
        else:
            logging.error("❌ Test failed - check configuration")
        
        return success

def create_systemd_service():
    """Create a systemd service file for Linux systems"""
    service_content = f"""[Unit]
Description=Alpaca Market Data Collector
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'user')}
WorkingDirectory={CURRENT_DIR}
ExecStart={os.path.join(PARENT_DIR, 'alpaca_venv', 'bin', 'python')} {os.path.join(CURRENT_DIR, 'automated_scheduler.py')}
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
"""
    
    service_file = '/tmp/alpaca-data-collector.service'
    
    with open(service_file, 'w') as f:
        f.write(service_content)
    
    logging.info(f"📝 Systemd service file created: {service_file}")
    logging.info("To install: sudo cp /tmp/alpaca-data-collector.service /etc/systemd/system/")
    logging.info("Then: sudo systemctl enable alpaca-data-collector && sudo systemctl start alpaca-data-collector")

def create_launchd_plist():
    """Create a launchd plist file for macOS systems"""
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.alpaca-data-collector</string>
    <key>ProgramArguments</key>
    <array>
        <string>{os.path.join(PARENT_DIR, 'alpaca_venv', 'bin', 'python')}</string>
        <string>{os.path.join(CURRENT_DIR, 'automated_scheduler.py')}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{CURRENT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{os.path.join(CURRENT_DIR, 'scheduler_out.log')}</string>
    <key>StandardErrorPath</key>
    <string>{os.path.join(CURRENT_DIR, 'scheduler_err.log')}</string>
</dict>
</plist>
"""
    
    plist_file = f"{os.path.expanduser('~')}/Library/LaunchAgents/com.user.alpaca-data-collector.plist"
    
    with open(plist_file, 'w') as f:
        f.write(plist_content)
    
    logging.info(f"📝 LaunchAgent plist created: {plist_file}")
    logging.info("To install: launchctl load ~/Library/LaunchAgents/com.user.alpaca-data-collector.plist")

def main():
    """Main function for automated scheduler"""
    scheduler = AutomatedDataScheduler()
    
    print("🤖 Alpaca Automated Data Collection Scheduler")
    print("=" * 60)
    print("This scheduler will automatically collect market data daily")
    print("after market close and keep your database updated.")
    print()
    
    # Show next scheduled runs
    priority_universe = get_priority_universe()
    total_symbols = sum(len(symbols) for symbols in priority_universe.values())
    
    print(f"📊 Asset Universe: {total_symbols} symbols across 5 tiers")
    print(f"📅 Schedule:")
    print(f"   • Weekdays 5:30 PM ET - Main collection")
    print(f"   • Daily 6:00 AM ET - Backup check")  
    print(f"   • Sunday 8:00 PM ET - Extended collection")
    print()
    
    # Options
    print("Options:")
    print("1. Run test collection now")
    print("2. Start automated scheduler") 
    print("3. Create system service files")
    print("4. Run single collection now")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        scheduler.test_collection()
    elif choice == "2":
        scheduler.run_scheduler()
    elif choice == "3":
        if sys.platform.startswith('linux'):
            create_systemd_service()
        elif sys.platform == 'darwin':
            create_launchd_plist()
        else:
            print("System service creation not supported on this platform")
    elif choice == "4":
        scheduler.run_data_collection('manual')
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
