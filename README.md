# KPI Monitoring Bot

> **CASE STUDY** · Automation & Analytics · Python · Anomaly Detection · Email + Slack

---

## The Problem

Manual KPI monitoring is a tax on analytical time.

Someone checks a dashboard every morning. They copy numbers into a spreadsheet. They send a summary email. And if something looks off — if revenue dropped 40% overnight or the at-risk customer count spiked — they might catch it. Or they might not.

This project replaces that process entirely. A bot runs on a schedule, detects anomalies automatically using statistical methods, and sends alerts to email and Slack before anyone has opened a dashboard.

---

## Approach

### 1. Data
365 days of daily retail KPIs including revenue, order volume, average order value, customer segment counts, and inventory events. Anomalies are planted at specific dates to validate detection accuracy.

### 2. Anomaly Detection — Z-Score Method
For each KPI, the bot calculates a 14-day rolling mean and standard deviation. A value is flagged as anomalous if it deviates more than ±2 standard deviations from the rolling average.

```
z = (today's value − 14-day mean) / 14-day std dev
flag if |z| > 2.0
```

This is more robust than fixed thresholds because it adapts to the natural baseline of each KPI — a revenue drop that's normal in January might be a crisis in December.

Hard-floor and hard-ceiling thresholds are also configurable for absolute limits that should never be crossed regardless of statistical context.

### 3. KPIs Monitored

| KPI | Alert Type | Threshold |
|-----|-----------|-----------|
| Daily Revenue | Drop + Spike | z > ±2.0, hard floor $10K |
| Avg Order Value | Drop | z < −2.0 |
| New Customers | Drop | z < −2.0 |
| At-Risk Customers | Spike | z > +2.0, hard ceiling 250 |
| Lost Customers | Spike | z > +2.0 |
| Stockout Events | Spike | z > +2.0 |

### 4. Alert Channels
When an anomaly is detected, the bot sends:
- **Email** — branded HTML email with a table of all triggered alerts, values vs. expected, and deviation percentages
- **Slack** — structured Block Kit message with the same data, posted to a configurable channel

### 5. Scheduling
Add to crontab for fully automated daily execution:
```bash
# Every morning at 8:00 AM
0 8 * * * /usr/bin/python3 /path/to/monitor.py
```

---

## Stack

```
Python · pandas · numpy · PyYAML · smtplib · Slack Webhooks
```

---

## Results (Demo Run)

| Date | KPI Flagged | Value | Expected | Deviation |
|------|------------|-------|----------|-----------|
| 2024-02-15 | Daily Revenue ▼ | $11,325 | $18,383 | −38.4% |
| 2024-04-30 | Daily Revenue ▲ | $34,702 | $19,277 | +80.0% |
| 2024-07-19 | Daily Revenue ▼ | $11,437 | $19,116 | −40.2% |
| 2024-07-19 | At-Risk Customers ▲ | 215 | 185 | +16.4% |
| 2024-11-06 | Daily Revenue ▲ | $34,261 | $19,993 | +71.4% |
| 2024-12-06 | Daily Revenue ▼ | $11,477 | $20,840 | −44.9% |
| 2024-12-06 | New Customers ▼ | 10 | 25 | −60.2% |

**7 alerts detected, 0 missed** across all planted anomaly days.

---

## What I Learned

**On detection:** Z-score is the right default for this problem — it's interpretable, adapts to seasonality, and produces very few false positives. The alternative (percentage change from prior day) is too noisy for KPIs with natural daily variance like revenue.

**On alerting:** The most important design decision was separating alert *detection* from alert *delivery*. The detector runs regardless — the channels (email, Slack) are just outputs. This makes it easy to add new channels (Teams, PagerDuty) without touching the core logic.

**On the business case:** The value isn't catching the obvious crises. It's catching the quiet ones — an at-risk customer count that's been creeping up for two weeks, or a new customer acquisition rate that's been slowly declining. Those patterns are invisible in a dashboard unless you're looking for them.

---

## How to Run

```bash
# Clone the repo
git clone https://github.com/klaricracia/kpi-monitoring-bot.git
cd kpi-monitoring-bot

# Install dependencies
pip install pandas numpy pyyaml

# Configure credentials
# Edit config.yaml → set your email/Slack details

# Run demo (shows all planted anomalies)
python monitor.py --demo

# Run for a specific date
python monitor.py --date 2024-07-19

# Run for latest data
python monitor.py
```

---

## How to Extend This

- **Connect to a live database:** Replace the CSV source in `config.yaml` with a SQL connection string
- **Add more KPIs:** Each new metric is one block in `config.yaml` — no code changes needed
- **Add Teams/PagerDuty:** Create a new file in `/alerts` following the same interface as `email_alert.py`
- **Track segment migration:** Combine with the [RFM Segmentation project](https://github.com/klaricracia/retail-customer-rfm-analysis) to alert when customers shift tiers

---

*Built by [Klarissa Artavia](https://www.linkedin.com/in/klariartavia/) · Data & AI Strategy*
*GitHub: [github.com/klaricracia](https://github.com/klaricracia)*
