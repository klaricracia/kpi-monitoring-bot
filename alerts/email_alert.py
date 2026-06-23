"""Email alert sender for KPI Monitoring Bot."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def send_email(config: dict, alerts: list) -> bool:
    """Send an HTML email summarising all triggered alerts."""
    if not config.get("enabled") or not alerts:
        return False

    subject = f"⚠️ KPI Alert — {len(alerts)} anomaly{'s' if len(alerts) > 1 else ''} detected · {datetime.now().strftime('%b %d, %Y')}"

    rows = ""
    for a in alerts:
        color = "#FF4632" if a["direction"] == "drop" else "#F037A5"
        arrow = "▼" if a["direction"] == "drop" else "▲"
        rows += f"""
        <tr>
          <td style="padding:10px 16px; font-weight:700;">{a['kpi_label']}</td>
          <td style="padding:10px 16px; color:{color}; font-weight:700;">{arrow} {a['value']:,.1f}</td>
          <td style="padding:10px 16px; color:#9E9A9A;">{a['expected']:,.1f} expected</td>
          <td style="padding:10px 16px; color:{color};">{a['deviation']:+.1f}%</td>
          <td style="padding:10px 16px;">{a['message']}</td>
        </tr>"""

    html = f"""
    <html><body style="background:#191414; color:#F5F5F0; font-family:Arial,sans-serif; padding:32px;">
      <div style="max-width:700px; margin:0 auto;">
        <div style="background:linear-gradient(135deg,#4100F5,#F037A5,#FF4632); padding:24px 32px; border-radius:8px 8px 0 0;">
          <p style="font-size:11px; letter-spacing:0.2em; color:rgba(255,255,255,0.75); margin:0 0 8px;">KPI MONITORING BOT</p>
          <h1 style="font-size:24px; font-weight:900; margin:0; color:#fff;">
            {len(alerts)} KPI Anomaly{'s' if len(alerts) > 1 else ''} Detected
          </h1>
          <p style="margin:8px 0 0; color:rgba(255,255,255,0.8); font-size:14px;">
            {datetime.now().strftime('%A, %B %d %Y — %H:%M')}
          </p>
        </div>
        <div style="background:#1E1A1A; border:1px solid #2a2525; border-top:none; border-radius:0 0 8px 8px; overflow:hidden;">
          <table style="width:100%; border-collapse:collapse;">
            <thead>
              <tr style="background:#252020;">
                <th style="padding:10px 16px; text-align:left; font-size:10px; letter-spacing:0.15em; color:#9E9A9A;">KPI</th>
                <th style="padding:10px 16px; text-align:left; font-size:10px; letter-spacing:0.15em; color:#9E9A9A;">VALUE</th>
                <th style="padding:10px 16px; text-align:left; font-size:10px; letter-spacing:0.15em; color:#9E9A9A;">EXPECTED</th>
                <th style="padding:10px 16px; text-align:left; font-size:10px; letter-spacing:0.15em; color:#9E9A9A;">DEVIATION</th>
                <th style="padding:10px 16px; text-align:left; font-size:10px; letter-spacing:0.15em; color:#9E9A9A;">NOTE</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        <p style="margin-top:24px; font-size:12px; color:#9E9A9A;">
          Built by <a href="https://www.linkedin.com/in/klariartavia/" style="color:#4100F5;">Klarissa Artavia</a> ·
          <a href="https://github.com/klaricracia/kpi-monitoring-bot" style="color:#4100F5;">github.com/klaricracia</a>
        </p>
      </div>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = config["sender"]
    msg["To"]      = ", ".join(config["recipients"])
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["sender"], config["password"])
            server.sendmail(config["sender"], config["recipients"], msg.as_string())
        print(f"  ✓ Email sent to {', '.join(config['recipients'])}")
        return True
    except Exception as e:
        print(f"  ✗ Email failed: {e}")
        return False
