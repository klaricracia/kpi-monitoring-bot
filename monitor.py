"""
KPI Monitoring Bot
==================
Author: Klarissa Artavia — Data & AI Strategy
GitHub: https://github.com/klaricracia
LinkedIn: https://www.linkedin.com/in/klariartavia/

Monitors daily business KPIs for anomalies and sends alerts via email and Slack.
Designed to replace manual reporting cycles with automated, threshold-aware detection.

Usage:
    python monitor.py                  # run once (today's data)
    python monitor.py --date 2024-07-15  # backtest a specific date
    python monitor.py --demo           # demo mode: runs all planted anomalies

Schedule with cron (runs every morning at 8am):
    0 8 * * * /usr/bin/python3 /path/to/monitor.py
"""

import pandas as pd
import numpy as np
import yaml
import json
import csv
import os
import sys
import argparse
from datetime import datetime, timedelta

from alerts.email_alert import send_email
from alerts.slack_alert  import send_slack

# ── Load config ───────────────────────────────────────────────────────────────
with open("config.yaml") as f:
    CONFIG = yaml.safe_load(f)

os.makedirs("output", exist_ok=True)

# ── Argument parsing ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--date", help="Date to analyse (YYYY-MM-DD). Defaults to today.")
parser.add_argument("--demo", action="store_true", help="Run demo over all anomaly days.")
args = parser.parse_args()

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv(CONFIG["data"]["path"], parse_dates=[CONFIG["data"]["date_column"]])
df = df.sort_values("date").reset_index(drop=True)

# ── Anomaly detection ─────────────────────────────────────────────────────────
def detect_anomaly(series: pd.Series, idx: int, cfg: dict) -> dict | None:
    """
    Returns anomaly info dict if the value at `idx` is anomalous, else None.
    Uses z-score against a rolling window of prior days.
    """
    window  = CONFIG["detection"]["window"]
    z_thresh = CONFIG["detection"]["zscore_threshold"]
    alert_on = cfg.get("alert_on", "both")

    start = max(0, idx - window)
    history = series.iloc[start:idx]
    if len(history) < 3:
        return None

    mean = history.mean()
    std  = history.std()
    val  = series.iloc[idx]

    if std == 0:
        return None

    z = (val - mean) / std
    pct_dev = ((val - mean) / mean * 100) if mean != 0 else 0

    # Hard thresholds
    if "min_threshold" in cfg and val < cfg["min_threshold"]:
        return {"z": z, "mean": mean, "pct_dev": pct_dev, "direction": "drop", "trigger": "hard_floor"}
    if "max_threshold" in cfg and val > cfg["max_threshold"]:
        return {"z": z, "mean": mean, "pct_dev": pct_dev, "direction": "spike", "trigger": "hard_ceiling"}

    # Statistical detection
    if alert_on in ("drop", "both") and z < -z_thresh:
        return {"z": z, "mean": mean, "pct_dev": pct_dev, "direction": "drop", "trigger": "zscore"}
    if alert_on in ("spike", "both") and z > z_thresh:
        return {"z": z, "mean": mean, "pct_dev": pct_dev, "direction": "spike", "trigger": "zscore"}

    return None


def run_for_date(target_date: datetime) -> list:
    """Run all KPI checks for a given date. Returns list of triggered alerts."""
    date_str = target_date.strftime("%Y-%m-%d")
    matches  = df[df["date"] == target_date]

    if matches.empty:
        print(f"  No data found for {date_str}")
        return []

    idx     = matches.index[0]
    row     = matches.iloc[0]
    alerts  = []

    print(f"\n{'─'*56}")
    print(f"  KPI CHECK · {date_str}")
    print(f"{'─'*56}")

    for kpi_key, kpi_cfg in CONFIG["kpis"].items():
        col   = kpi_cfg["column"]
        label = kpi_cfg["label"]
        val   = row[col]

        result = detect_anomaly(df[col], idx, kpi_cfg)

        if result:
            direction = result["direction"]
            symbol    = "▼" if direction == "drop" else "▲"
            msg = (f"Revenue fell below minimum threshold (${val:,.0f})" if kpi_key == "revenue" and result["trigger"] == "hard_floor"
                   else f"{abs(result['pct_dev']):.1f}% {'below' if direction == 'drop' else 'above'} 14-day average")

            alerts.append({
                "date":       date_str,
                "kpi_key":    kpi_key,
                "kpi_label":  label,
                "value":      val,
                "expected":   result["mean"],
                "deviation":  result["pct_dev"],
                "z_score":    round(result["z"], 2),
                "direction":  direction,
                "trigger":    result["trigger"],
                "message":    msg,
            })
            print(f"  ⚠️  {label:<25} {symbol} {val:>10,.1f}   {result['pct_dev']:+.1f}%  z={result['z']:.2f}")
        else:
            print(f"  ✓  {label:<25}   {val:>10,.1f}   OK")

    return alerts


def log_alerts(alerts: list):
    """Append alerts to the CSV log."""
    log_path = CONFIG["output"]["log_path"]
    file_exists = os.path.exists(log_path)
    with open(log_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date","kpi_key","kpi_label","value","expected","deviation","z_score","direction","trigger","message"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(alerts)


class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        return super().default(obj)

def save_report(all_alerts: list, dates_checked: list):
    """Save a JSON summary of the last run."""
    report = {
        "run_at":        datetime.now().isoformat(),
        "dates_checked": [d.strftime("%Y-%m-%d") for d in dates_checked],
        "total_alerts":  len(all_alerts),
        "alerts":        all_alerts,
    }
    with open(CONFIG["output"]["report_path"], "w") as f:
        json.dump(report, f, indent=2, cls=_NumpyEncoder)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    all_alerts = []

    if args.demo:
        # Run over all planted anomaly days for demonstration
        anomaly_indices = [45, 120, 200, 310, 340]
        dates_to_check  = [df["date"].iloc[i] for i in anomaly_indices]
        print("\n🤖 DEMO MODE — running over planted anomaly days")
    elif args.date:
        dates_to_check = [pd.Timestamp(args.date)]
        print(f"\n🤖 KPI MONITORING BOT — checking {args.date}")
    else:
        dates_to_check = [df["date"].max()]
        print(f"\n🤖 KPI MONITORING BOT — checking latest data ({dates_to_check[0].date()})")

    for target_date in dates_to_check:
        alerts = run_for_date(target_date)
        all_alerts.extend(alerts)

        if alerts:
            print(f"\n  → {len(alerts)} alert(s) triggered. Sending notifications...")
            send_email(CONFIG["email"], alerts)
            send_slack(CONFIG["slack"], alerts)
            log_alerts(alerts)
        else:
            print(f"\n  → All KPIs within normal range. No alerts sent.")

    save_report(all_alerts, dates_to_check)

    print(f"\n{'─'*56}")
    print(f"  RUN COMPLETE · {len(all_alerts)} total alert(s) across {len(dates_to_check)} day(s)")
    print(f"  Log: {CONFIG['output']['log_path']}")
    print(f"{'─'*56}\n")


if __name__ == "__main__":
    main()
