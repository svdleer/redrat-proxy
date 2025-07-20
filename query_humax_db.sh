#!/bin/bash

echo "🎯 GETTING REAL HUMAX POWER FROM DATABASE VIA MYSQL CLIENT"
echo "=========================================================="

ssh -p 65001 -o StrictHostKeyChecking=no svdleer@access-engineering.nl << 'EOF'

echo "🐳 Checking running Docker containers..."
docker ps

echo ""
echo "🔍 Querying database for Humax POWER command..."

# Use docker exec to query MySQL directly
docker exec $(docker ps --format "{{.Names}}" | grep mysql || docker ps --format "{{.Names}}" | head -1) \
mysql -u redrat_user -predrat_password redrat_proxy -e "
SELECT signal_name, LEFT(signal_data, 100) as data_preview, port, power_level 
FROM ir_signals 
WHERE remote_name = 'Humax' AND signal_name LIKE '%POWER%' 
LIMIT 3;
" 2>/dev/null || echo "❌ MySQL query failed, trying alternative..."

echo ""
echo "📋 Let's check what tables and data exist..."

# Check tables
docker exec $(docker ps --format "{{.Names}}" | grep mysql || docker ps --format "{{.Names}}" | head -1) \
mysql -u redrat_user -predrat_password redrat_proxy -e "SHOW TABLES;" 2>/dev/null

echo ""
echo "🔍 Check remotes table..."
docker exec $(docker ps --format "{{.Names}}" | grep mysql || docker ps --format "{{.Names}}" | head -1) \
mysql -u redrat_user -predrat_password redrat_proxy -e "SELECT * FROM remotes WHERE name = 'Humax' LIMIT 1;" 2>/dev/null

echo ""
echo "🔍 Check signals table..."
docker exec $(docker ps --format "{{.Names}}" | grep mysql || docker ps --format "{{.Names}}" | head -1) \
mysql -u redrat_user -predrat_password redrat_proxy -e "SELECT remote_id, name, LEFT(data, 50) as data_preview FROM signals WHERE name LIKE '%POWER%' LIMIT 3;" 2>/dev/null

EOF

echo ""
echo "🔍 Database query complete!"
