"""Slack alert sender for KPI Monitoring Bot."""

import urllib.request
import urllib.error
import json
from datetime import datetime


def send_slack(config: dict, alerts: list) -> bool:
    """Post a Slack message summarising all triggered alerts."""
    if not config.get("enabled") or not alerts:
        return False

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"⚠️ {len(alerts)} KPI Anomaly{'s' if len(alerts) > 1 else ''} Detected"}
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"*KPI Monitoring Bot* · {datetime.now().strftime('%b %d, %Y %H:%M')}"}]
        },
        {"type": "divider"}
    ]

    for a in alerts:
        arrow  = "🔴" if a["direction"] == "drop" else "🟣"
        symbol = "▼" if a["direction"] == "drop" else "▲"
        blocks.append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*{a['kpi_label']}*\n{arrow} `{symbol} {a['value']:,.1f}` _(expected ~{a['expected']:,.1f})_"},
                {"type": "mrkdwn", "text": f"*Deviation*\n`{a['deviation']:+.1f}%`\n{a['message']}"}
            ]
        })

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "Built by <https://www.linkedin.com/in/klariartavia/|Klarissa Artavia> · <https://github.com/klaricracia/kpi-monitoring-bot|View on GitHub>"}]
    })

    payload = json.dumps({
        "username": config.get("username", "KPI Bot"),
        "channel":  config.get("channel", "#kpi-alerts"),
        "blocks":   blocks
    }).encode()

    try:
        req = urllib.request.Request(
            config["webhook_url"],
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as r:
            if r.status == 200:
                print(f"  ✓ Slack message sent to {config.get('channel')}")
                return True
    except Exception as e:
        print(f"  ✗ Slack failed: {e}")
    return False
