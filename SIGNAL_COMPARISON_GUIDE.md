# RedRat Signal Comparison Guide

This guide helps you compare IR signals between your RedRat Proxy tool and the official RedRat tool using ERSPAN packet capture.

## 📋 Overview

**Goal:** Compare IR signal quality, timing, and accuracy between:
- Your RedRat Proxy (Docker) - `your-tool`
- Official RedRat tool - `official-tool`

**Method:** ERSPAN packet capture + analysis

## 🚀 Quick Start

### 1. Deploy Tools to Remote Server

From your local machine:
```bash
./deploy_signal_tools.sh
```

### 2. SSH to Remote Server

```bash
ssh -p 65001 svdleer@access-engineering.nl
cd /tmp/redrat_signal_tools
```

### 3. Run Comparison

```bash
./signal_comparison.sh compare
```

## 📁 Tool Files

| File | Purpose |
|------|---------|
| `deploy_signal_tools.sh` | Deploy all tools to remote server |
| `signal_comparison.sh` | Interactive signal capture workflow |
| `analyze_redrat_signals.py` | Detailed PCAP analysis and comparison |
| `redrat_docker_test.sh` | Test your Docker RedRat proxy |

## 🔍 Detailed Process

### Step 1: Setup ERSPAN Capture

Ensure ERSPAN is configured to capture traffic to/from your RedRat device:
- **RedRat Device IP:** (e.g., `192.168.1.100`)
- **RedRat Port:** `10001` (default)
- **Capture Interface:** Configure in your ERSPAN setup

### Step 2: Prepare Both Tools

**Your RedRat Proxy (Docker):**
```bash
# Check container status
sudo docker ps | grep redrat

# Test API
curl http://localhost:5000/api/health

# Test specific command
./redrat_docker_test.sh test 1 power_on 1 50
```

**Official RedRat Tool:**
- Ensure official tool is accessible
- Have same command available
- Note the device IP/port settings

### Step 3: Capture Signals

**Automated (Recommended):**
```bash
./signal_comparison.sh compare
```

**Manual:**
```bash
# Start capture for proxy tool
sudo tcpdump -i any -w proxy_capture.pcap host 192.168.1.100 and port 10001 &
TCPDUMP_PID=$!

# Execute command via your proxy
curl -X POST http://localhost:5000/api/commands -H "Content-Type: application/json" \
  -d '{"remote_id":1,"command":"power_on","redrat_device_id":1,"ir_port":1,"power":50}' \
  -b cookies.txt

# Stop capture
kill $TCPDUMP_PID

# Repeat for official tool...
```

### Step 4: Analyze Results

**Compare captures:**
```bash
python3 analyze_redrat_signals.py proxy_capture.pcap official_capture.pcap --compare
```

**Detailed analysis:**
```bash
python3 analyze_redrat_signals.py *.pcap --output analysis.json
```

## 📊 Analysis Metrics

### Signal Quality Indicators

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| **Timing Difference** | <10ms | 10-100ms | >100ms |
| **Packet Count** | Same | ±1-2 | >2 difference |
| **Message Types** | Identical | Similar | Different |
| **Payload Match** | 100% | >95% | <95% |

### Key Comparisons

1. **IR Signal Timing**
   - Pulse/pause patterns
   - Inter-signal delays
   - Total command duration

2. **Protocol Compliance**
   - RedRat message types
   - Packet structure
   - Response timing

3. **Power Levels**
   - Signal strength consistency
   - Modulation accuracy

4. **Repeat Patterns**
   - Number of repeats
   - Repeat timing
   - Signal consistency

## 🔧 Troubleshooting

### Common Issues

**No packets captured:**
- Check RedRat device IP
- Verify ERSPAN configuration
- Ensure RedRat device is accessible

**Authentication failed:**
- Check login credentials (admin/admin)
- Verify API endpoint accessibility
- Check Docker container status

**Command not found:**
- List available remotes: `curl http://localhost:5000/api/remotes`
- Check remote ID and command name
- Verify remote file uploaded

### Debug Commands

```bash
# Check Docker logs
sudo docker logs redrat-proxy

# Test API health
curl -v http://localhost:5000/api/health

# List available commands
./redrat_docker_test.sh

# Check ERSPAN capture
sudo tcpdump -i any -c 10 host 192.168.1.100
```

## 📈 Expected Results

### Ideal Comparison
- **Timing difference:** <5ms
- **Packet count:** Identical
- **Message types:** Same
- **IR data:** 100% match

### Acceptable Variations
- **Minor timing jitter:** <50ms
- **Power level differences:** ±5-10%
- **Additional handshake packets:** Normal

### Concerning Differences
- **Major timing drift:** >100ms
- **Missing IR data packets**
- **Different message types**
- **Protocol errors**

## 🎯 Signal Comparison Checklist

- [ ] ERSPAN capturing RedRat traffic
- [ ] Docker RedRat proxy running
- [ ] Official RedRat tool ready
- [ ] Same IR command available in both tools
- [ ] RedRat device IP/port confirmed
- [ ] Packet captures completed
- [ ] Analysis comparison run
- [ ] Results documented

## 💡 Tips

1. **Use simple commands first** (power_on/off)
2. **Test multiple IR ports** (1, 5, 8)
3. **Vary power levels** (25, 50, 75, 100)
4. **Capture multiple iterations** for consistency
5. **Document RedRat device model** and firmware version

## 🔍 Next Steps After Comparison

Based on results:

**If signals match well:**
- ✅ Your proxy is accurate
- Document any minor differences
- Test with more complex commands

**If significant differences found:**
- 🔍 Analyze timing differences
- Check IR data encoding
- Review power level handling
- Compare modulation frequencies

**If major issues detected:**
- ❌ Review RedRat protocol implementation
- Check binary data conversion
- Validate timing calculations
- Test with different devices
