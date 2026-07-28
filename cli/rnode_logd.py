#!/usr/bin/env python3
"""rnode log daemon + analyzer — the RF blackhole.

sample mode: polls the station on three channels and appends JSONL:
  rf   (every 5s)  — RNode via rnstatus: noise floor, airtime, channel load,
                     traffic counters, CPU temp, interface up/down
  ble  (every 30s) — local Bluetooth LE population (bleak scan via the rns venv)
  wifi (every 60s) — visible WiFi networks (system_profiler)

analyze mode: harmonic-sequencing protocol at micro level — the noise-floor
series is symbolized exactly like a voice pitch contour (S steady / U up /
D down / R interface-down, on 2 dB quanta), motifs are mined as n-grams,
and anomalies (>=6 dB jumps, airtime spikes, BLE churn) are surfaced.

stdlib only. Usage:
  rnode_logd.py sample <minutes> <outfile>
  rnode_logd.py analyze <outfile> [--json]
"""
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HOME = Path.home()
RNSTATUS = HOME / ".local/bin/rnstatus"
RNS_PY = HOME / ".local/pipx/venvs/rns/bin/python"

BLE_SNIPPET = (
    "import asyncio,json;from bleak import BleakScanner\n"
    "async def m():\n"
    " d=await BleakScanner.discover(timeout=6.0,return_adv=True)\n"
    " print(json.dumps([{'name':v[0].name,'addr':a,'rssi':v[1].rssi}"
    " for a,v in d.items()]))\n"
    "asyncio.run(m())"
)


def _bytes(s):
    m = re.match(r"([\d.]+)\s*(B|KB|MB|GB)", s.strip())
    if not m:
        return 0
    mult = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}[m.group(2)]
    return int(float(m.group(1)) * mult)


def sample_rf():
    try:
        out = subprocess.run([str(RNSTATUS)], capture_output=True, text=True,
                             timeout=12).stdout
    except (subprocess.TimeoutExpired, OSError):
        return {"kind": "rf", "status_up": False, "error": "rnstatus unavailable"}
    chunk = next((c for c in out.split("\n\n") if "RNodeInterface" in c), "")
    if not chunk:
        return {"kind": "rf", "status_up": False, "error": "interface missing"}
    d = {"kind": "rf", "status_up": "Status    : Up" in chunk}
    m = re.search(r"Noise Fl\.\s*:\s*(-?\d+)\s*dBm", chunk)
    d["noise_dbm"] = int(m.group(1)) if m else None
    m = re.search(r"CPU temp\s*:\s*(\d+)", chunk)
    d["cpu_temp_c"] = int(m.group(1)) if m else None
    m = re.search(r"Airtime\s*:\s*([\d.]+)%\s*\(15s\)", chunk)
    d["airtime15_pct"] = float(m.group(1)) if m else None
    m = re.search(r"Ch\. Load\s*:\s*([\d.]+)%\s*\(15s\)", chunk)
    d["chload15_pct"] = float(m.group(1)) if m else None
    up = re.search(r"↑\s*([\d.]+\s*\w+)", chunk)
    dn = re.search(r"↓\s*([\d.]+\s*\w+)", chunk)
    d["up_bytes"] = _bytes(up.group(1)) if up else 0
    d["down_bytes"] = _bytes(dn.group(1)) if dn else 0
    m = re.search(r"Intrfrnc\.\s*:\s*(.+)", chunk)
    if m:
        d["interference"] = m.group(1).strip()
    return d


def sample_ble():
    try:
        out = subprocess.run([str(RNS_PY), "-c", BLE_SNIPPET],
                             capture_output=True, text=True, timeout=25).stdout
        devs = json.loads(out.strip() or "[]")
        return {"kind": "ble", "count": len(devs),
                "devices": [{"name": x.get("name"), "addr": x.get("addr"),
                             "rssi": x.get("rssi")} for x in devs]}
    except Exception as e:
        return {"kind": "ble", "error": str(e)[:80]}


def sample_wifi():
    try:
        out = subprocess.run(["system_profiler", "SPAirPortDataType", "-json"],
                             capture_output=True, text=True, timeout=25).stdout
        data = json.loads(out)
        nets = set()
        def walk(o):
            if isinstance(o, dict):
                if "_name" in o and ("spairport_signal_noise" in o or
                                     "spairport_network_channel" in o):
                    nets.add(o["_name"])
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(data)
        return {"kind": "wifi", "networks": sorted(nets), "count": len(nets)}
    except Exception as e:
        return {"kind": "wifi", "error": str(e)[:80]}


def run_sampler(minutes: float, outfile: Path, channels: str = "rf"):
    """channels: 'rf' = LoRa only (default); 'all' = + BLE/WiFi sweeps."""
    outfile.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + minutes * 60
    last_ble = last_wifi = 0.0
    n = 0
    with open(outfile, "a") as f:
        f.write(json.dumps({"kind": "session", "start": time.time(),
                            "minutes": minutes, "channels": channels}) + "\n")
        while time.time() < deadline:
            tick = time.time()
            rows = [sample_rf()]
            if channels == "all" and tick - last_ble >= 30:
                rows.append(sample_ble()); last_ble = tick
            if channels == "all" and tick - last_wifi >= 60:
                rows.append(sample_wifi()); last_wifi = tick
            for r in rows:
                r["ts"] = round(tick, 2)
                f.write(json.dumps(r) + "\n")
            f.flush()
            n += len(rows)
            time.sleep(max(0.0, 5 - (time.time() - tick)))
    print(f"blackhole closed: {n} samples -> {outfile}")


# ---- analysis: the harmonic-sequencing protocol, micro level ---------------

def symbolize_noise(rf_rows, quantum_db=2.0):
    toks, last = [], None
    for r in rf_rows:
        if not r.get("status_up") or r.get("noise_dbm") is None:
            toks.append("R"); last = None; continue
        v = r["noise_dbm"]
        if last is None:
            toks.append("S")
        else:
            d = v - last
            toks.append("U" if d >= quantum_db else "D" if d <= -quantum_db else "S")
        last = v
    out = []
    for t in toks:
        if out and out[-1][0] == t:
            out[-1][1] += 1
        else:
            out.append([t, 1])
    return toks, " ".join(f"{c}{n}" if n > 1 else c for c, n in out)


def mine_motifs(toks, lo=2, hi=6, top=8):
    counts = Counter()
    for n in range(lo, hi + 1):
        for i in range(len(toks) - n + 1):
            gram = "".join(toks[i:i + n])
            if set(gram) != {"S"}:          # all-steady is silence, not signal
                counts[gram] += 1
    return [{"motif": g, "count": c} for g, c in counts.most_common(top) if c > 1]


def analyze(outfile: Path, as_json=False):
    if not outfile.exists():
        print("no blackhole log yet — run: rnode log start [minutes]")
        return
    rows = []
    for line in outfile.read_text().strip().splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    rf = [r for r in rows if r.get("kind") == "rf"]
    ble = [r for r in rows if r.get("kind") == "ble" and "count" in r]
    wifi = [r for r in rows if r.get("kind") == "wifi" and "count" in r]
    if not rf:
        print("no rf samples logged yet"); return

    noises = [r["noise_dbm"] for r in rf if r.get("noise_dbm") is not None]
    toks, symbols = symbolize_noise(rf)
    motifs = mine_motifs(toks)

    anomalies = []
    for a, b in zip(rf, rf[1:]):
        na, nb = a.get("noise_dbm"), b.get("noise_dbm")
        if na is not None and nb is not None and abs(nb - na) >= 6:
            anomalies.append({"ts": b["ts"], "noise_jump_db": nb - na})
        if b.get("airtime15_pct") and b["airtime15_pct"] >= 5:
            anomalies.append({"ts": b["ts"], "airtime_pct": b["airtime15_pct"]})
        if a.get("status_up") and not b.get("status_up"):
            anomalies.append({"ts": b["ts"], "event": "interface went down"})
    rx_delta = rf[-1].get("down_bytes", 0) - rf[0].get("down_bytes", 0)
    tx_delta = rf[-1].get("up_bytes", 0) - rf[0].get("up_bytes", 0)

    ble_names = set()
    for r in ble:
        for d in r.get("devices", []):
            ble_names.add(d.get("name") or d.get("addr", "?")[:8])
    wifi_nets = set()
    for r in wifi:
        wifi_nets.update(r.get("networks", []))

    report = {
        "rf_samples": len(rf),
        "span_minutes": round((rf[-1]["ts"] - rf[0]["ts"]) / 60, 1) if len(rf) > 1 else 0,
        "noise_dbm": {"min": min(noises), "median": sorted(noises)[len(noises)//2],
                      "max": max(noises)} if noises else None,
        "uptime_ratio": round(sum(1 for r in rf if r.get("status_up")) / len(rf), 3),
        "rx_bytes": rx_delta, "tx_bytes": tx_delta,
        "symbols": symbols,
        "motifs": motifs,
        "anomalies": anomalies[:20],
        "ble_unique_devices": sorted(ble_names),
        "ble_population": [r["count"] for r in ble],
        "wifi_networks": sorted(wifi_nets),
    }
    if as_json:
        print(json.dumps(report))
        return
    print(f"— RF blackhole report ({report['span_minutes']} min, "
          f"{report['rf_samples']} samples, uptime {report['uptime_ratio']*100:.0f}%) —")
    if report["noise_dbm"]:
        n = report["noise_dbm"]
        print(f"noise floor : {n['min']}..{n['max']} dBm (median {n['median']})")
    print(f"traffic     : ↓{rx_delta} B  ↑{tx_delta} B")
    print(f"symbols     : {symbols[:200]}{'…' if len(symbols) > 200 else ''}")
    print(f"motifs      : " + (", ".join(f"{m['motif']}×{m['count']}" for m in motifs) or "none — flat environment"))
    print(f"anomalies   : {len(anomalies)}" + (f" — first: {anomalies[0]}" if anomalies else ""))
    print(f"ble         : {len(ble_names)} unique devices: {', '.join(list(ble_names)[:8]) or '—'}")
    print(f"wifi        : {len(wifi_nets)} networks visible")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "sample" and len(args) >= 3:
        run_sampler(float(args[1]), Path(args[2]),
                    "all" if "all" in args[3:] else "rf")
    elif args and args[0] == "analyze" and len(args) >= 2:
        analyze(Path(args[1]), as_json="--json" in args)
    else:
        print(__doc__)
