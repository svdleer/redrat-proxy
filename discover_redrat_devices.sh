#!/bin/bash

echo "================================================"
echo "Discovering Available RedRat Devices and Ports"
echo "================================================"

# SSH into the host and scan for RedRat devices
ssh -p 65001 -o StrictHostKeyChecking=no svdleer@access-engineering.nl << 'EOF'

echo "Current network configuration:"
ip addr show

echo ""
echo "Scanning for RedRat devices on common ports..."

# Test different IP addresses and ports
for ip in "172.16.6.62" "192.168.1.62" "10.0.0.62"; do
  for port in "10001" "10002" "65001" "80" "8080"; do
    echo -n "Testing ${ip}:${port} ... "
    timeout 2 bash -c "</dev/tcp/${ip}/${port}" 2>/dev/null && echo "OPEN ✓" || echo "closed ✗"
  done
done

echo ""
echo "Checking for any listening RedRat services:"
netstat -tlnp 2>/dev/null | grep -E ":10001|:10002|:65001" || echo "No RedRat ports found listening"

echo ""
echo "Checking Docker containers:"
docker ps | grep -i redrat || echo "No RedRat containers running"

echo ""
echo "Looking for RedRat processes:"
ps aux | grep -i redrat || echo "No RedRat processes found"

EOF

echo ""
echo "Device discovery complete!"
