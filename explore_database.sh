#!/bin/bash

echo "🎯 EXPLORING DATABASE STRUCTURE FOR SIGNAL DATA"
echo "=============================================="

ssh -p 65001 -o StrictHostKeyChecking=no svdleer@access-engineering.nl << 'EOF'

echo "🐍 Activating venv..."
source /home/svdleer/scripts/python/venv/bin/activate

echo "🔍 Exploring database tables for IR signal data..."

python3 << 'EXPLORE_EOF'
import mysql.connector

try:
    conn = mysql.connector.connect(
        host='localhost',
        port=3306,
        database='redrat_proxy',
        user='redrat',
        password='Clad6DytmucAr'
    )
    
    cursor = conn.cursor()
    
    print("✅ Connected to database!")
    print("📋 Exploring table structures...")
    
    # Get all tables
    cursor.execute("SHOW TABLES")
    tables = [table[0] for table in cursor.fetchall()]
    
    # Look for tables that might contain signal data
    signal_tables = ['commands', 'command_templates', 'sequences', 'sequence_commands']
    
    for table in signal_tables:
        if table in tables:
            print(f"\n🔍 Table: {table}")
            
            # Get table structure
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            print(f"   Columns: {[col[0] for col in columns]}")
            
            # Get sample data
            cursor.execute(f"SELECT * FROM {table} LIMIT 3")
            rows = cursor.fetchall()
            if rows:
                print(f"   Sample data ({len(rows)} rows):")
                for i, row in enumerate(rows):
                    print(f"     Row {i+1}: {str(row)[:200]}...")
            else:
                print("   (No data)")
    
    # Look for anything with "Humax" or "POWER" 
    print(f"\n🔍 Searching for 'Humax' or 'POWER' in all tables...")
    for table in tables:
        try:
            cursor.execute(f"SELECT * FROM {table}")
            columns = [desc[0] for desc in cursor.description]
            
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            for row in rows:
                row_str = str(row).upper()
                if 'HUMAX' in row_str or 'POWER' in row_str:
                    print(f"   🎯 Found in {table}: {str(row)[:150]}...")
                    
        except Exception as e:
            print(f"   Error checking {table}: {e}")
    
    # Check remotes table specifically
    if 'remotes' in tables:
        print(f"\n📺 Checking remotes table for Humax...")
        cursor.execute("SELECT * FROM remotes WHERE name LIKE '%Humax%' OR name LIKE '%humax%'")
        humax_remotes = cursor.fetchall()
        if humax_remotes:
            print(f"   Found Humax remotes: {humax_remotes}")
        else:
            print("   No Humax remotes found")
            
        # Show all remotes
        cursor.execute("SELECT id, name FROM remotes LIMIT 10")
        all_remotes = cursor.fetchall()
        print(f"   Available remotes: {all_remotes}")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
EXPLORE_EOF

# Let's also check if there are any XML or JSON files with signal data
echo ""
echo "🔍 Checking for IR data files on filesystem..."
find /home/svdleer -name "*.xml" -o -name "*.json" 2>/dev/null | grep -i "humax\|remote\|ir" | head -5

EOF

echo ""
echo "🏁 Database exploration complete!"
