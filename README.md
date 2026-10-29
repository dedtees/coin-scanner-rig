# 🪙 Automated Coin Scanner Rig

Automated coin scanning using a rotating table, dual cameras, and AI analysis via the Coin Scanner API.

## Quick Start

### On the Raspberry Pi:
```bash
# Install dependencies
pip3 install opencv-python requests RPi.GPIO

# Start the dashboard (runs in background)
python3 dashboard.py &

# Start scanning
python3 coin_scanner_rig.py --denomination quarter
```

### On your phone/tablet (same WiFi):
Open browser → `http://<PI-IP-ADDRESS>:8080`

### Test without hardware (any computer):
```bash
python3 coin_scanner_rig.py --simulate --denomination quarter
```

## Files

| File | Purpose |
|------|---------|
| `coin_scanner_rig.py` | Main control script — motor, cameras, API, sorting |
| `dashboard.py` | Web dashboard — view results on phone/tablet |

## Hardware Wiring

### GPIO Pins (Raspberry Pi)
| Pin | Component | Notes |
|-----|-----------|-------|
| GPIO 17 | Stepper STEP | DRV8825 STEP input |
| GPIO 27 | Stepper DIR | DRV8825 DIR input |
| GPIO 18 | Stepper ENABLE | DRV8825 ENABLE (LOW=enabled) |
| GPIO 23 | IR Sensor | Break beam signal (with pull-up) |
| GPIO 24 | Solenoid | Via relay or transistor, 12V switched |

### Power
- **5V USB-C**: Powers the Raspberry Pi
- **12V 2A wall adapter**: Powers stepper motor + solenoid (via L298N VMOT)

### Cameras
- **Top camera**: `/dev/video0` (USB port 1)
- **Bottom camera**: `/dev/video1` (USB port 2)

## How It Works

1. Load coins into the template slots on the rotating table
2. Stepper motor rotates one slot at a time under the cameras
3. IR sensor confirms a coin is present
4. Both cameras fire simultaneously (top + bottom)
5. Images sent to Coin Scanner API on Render (Haiku vision + OCR + rules)
6. Result displayed on phone dashboard: 🟢 common / 🟡 check / 🔴 rare
7. If flagged, solenoid pushes the coin up for retrieval
8. Table advances to next slot and repeats

## API

The rig calls `https://coin-scanner-api.onrender.com/api/detect` with front + back images. The API returns denomination, year, mint mark, estimated value, rarity assessment, and varieties to check.

Cost: ~$0.002 per scan (Haiku vision).