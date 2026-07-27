# Flashing RNode firmware (any supported board)

This toolkit drives boards running [RNode firmware](https://github.com/markqvist/RNode_Firmware).
Flashing is handled by `rnodeconf`, which ships with Reticulum:

```bash
pipx install rns          # provides rnodeconf, rnsd, rnstatus
rnodeconf /dev/<port> --autoinstall
```

The installer downloads the right firmware, flashes it, provisions the EEPROM,
and signs the firmware hash. Pick your board from its menu:

| # | Board | Notes |
|---|-------|-------|
| 1 | A specific kind of RNode | vendor/recipe-built RNodes |
| 2 | Homebrew RNode | your own design |
| 3 | LilyGO LoRa32 v2.1 (T3 v1.6/v1.6.1) | |
| 4 | LilyGO LoRa32 v2.0 | |
| 5 | LilyGO LoRa32 v1.0 | |
| 6 | LilyGO T-Beam | |
| 7 | Heltec LoRa32 v2 | |
| 8 | Heltec LoRa32 v3 | ESP32-S3, BLE |
| 9 | **Heltec LoRa32 v4** | ESP32-S3, 28 dBm PA — needs fw ≥1.84 (≥1.86 for V4.3); band menu: 868/915/923 |
| 10 | LilyGO LoRa T3S3 | ESP32-S3 |
| 11 | RAK4631 | nRF52840 |
| 12 | LilyGO T-Echo | nRF52840 |
| 13 | LilyGO T-Beam Supreme | |
| 14 | LilyGO T-Deck | |
| 15 | Heltec T114 | nRF52840 |
| 16 | Seeed XIAO ESP32S3 Wio-SX1262 | |

(Menu numbering as of rnodeconf 2.5.0 / firmware 1.86 — the list grows; run it and read.)

## Finding your serial port

- **macOS:** `ls /dev/cu.usbmodem*` (native-USB boards like ESP32-S3) or
  `/dev/cu.SLAB_USBtoUART` / `/dev/cu.wchusbserial*` (CP210x/CH340 boards)
- **Linux:** `ls /dev/ttyACM* /dev/ttyUSB*`
- Use a **data** USB cable — charge-only cables are the #1 "device not found"

## Alternative: web flasher

No Python needed: [liamcottle.github.io/rnode-flasher](https://liamcottle.github.io/rnode-flasher/)
in Chrome. Hold **BOOT**, tap **RST**, release BOOT to enter bootloader, flash,
then **complete the Provision + Set Firmware Hash steps** — skipping them
causes "Missing config" errors.

## Verify

```bash
rnodeconf /dev/<port> --info     # firmware version, EEPROM checksum, signature
rnode status                     # if you've set up this toolkit
```

## Gotchas we learned the hard way

- **Coming from Meshtastic?** Back up first: `meshtastic --export-config > backup.yaml`
  (restore later = Meshtastic web flasher + `meshtastic --configure backup.yaml`).
- **Quit anything holding the serial port** (Meshtastic desktop app, MeshChat)
  before flashing — a half-triggered reset with the port busy can wedge the
  board's USB until you press RST or replug.
- **Reflashed a board your computer had paired over Bluetooth?** The OS keeps
  the old bond and refuses new connections ("peer removed pairing
  information"). Forget the device in Bluetooth settings — on macOS the stale
  entry may still show the board's *old* name.
- Ports can **re-enumerate** after flashing; re-run `ls /dev/cu.usbmodem*`.
- If auto-reset fails: hold **BOOT**, tap **RST**, release — then re-run.
