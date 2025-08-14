import sqlite3
import pandas as pd

# Check the database
# Updated to check Step 5 database
conn = sqlite3.connect('Step 5: Saving Market Data/market_data.db')

# Get record count
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM market_data')
count = cursor.fetchone()[0]
print(f'📊 Records in database: {count}')

if count > 0:
    # Show sample data
    df = pd.read_sql('SELECT * FROM market_data LIMIT 5', conn)
    print('\n📈 Sample data:')
    print(df)
    
    # Show unique symbols
    cursor.execute('SELECT DISTINCT symbol FROM market_data')
    symbols = [row[0] for row in cursor.fetchall()]
    print(f'\n🎯 Symbols in database: {symbols}')
    
    # Show date range
    cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM market_data')
    date_range = cursor.fetchone()
    print(f'📅 Date range: {date_range[0]} to {date_range[1]}')
else:
    print("No data found in database")

conn.close()
print('\n✅ Database check completed!')
