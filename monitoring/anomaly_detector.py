"""
FinCloud AI Anomaly Detection Script

Pulls logs from CloudWatch, detects anomalies using rule-based checks,
then sends suspicious events to OpenAI API for intelligent analysis.

Runs on a schedule (not continuously) to stay within free-tier limits.
CloudWatch free tier: 5GB log ingestion, 5 custom metrics.

Usage:
    python anomaly_detector.py                 # One-time run
    python anomaly_detector.py --schedule 60   # Run every 60 minutes
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("anomaly-detector")

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
LOG_GROUPS = [
    "/ecs/fincloud/user-service",
    "/ecs/fincloud/transaction-service",
    "/aws/lambda/fincloud-fraud-detection",
    "/api-gateway/fincloud",
]
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
LOOKBACK_MINUTES = int(os.environ.get("LOOKBACK_MINUTES", "60"))


class CloudWatchLogFetcher:
    def __init__(self, region: str = AWS_REGION):
        self.client = boto3.client("logs", region_name=region)

    def fetch_logs(self, log_group: str, minutes_back: int = LOOKBACK_MINUTES) -> list[dict]:
        end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_time = int((datetime.now(timezone.utc) - timedelta(minutes=minutes_back)).timestamp() * 1000)

        events = []
        try:
            paginator = self.client.get_paginator("filter_log_events")
            for page in paginator.paginate(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                limit=500,
            ):
                for event in page.get("events", []):
                    events.append({
                        "log_group": log_group,
                        "timestamp": datetime.fromtimestamp(
                            event["timestamp"] / 1000, tz=timezone.utc
                        ).isoformat(),
                        "message": event["message"].strip(),
                    })
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.warning(f"Log group {log_group} not found — skipping")
            else:
                logger.error(f"Error fetching logs from {log_group}: {e}")

        return events

    def fetch_all_logs(self) -> list[dict]:
        all_events = []
        for group in LOG_GROUPS:
            logger.info(f"Fetching logs from {group}...")
            events = self.fetch_logs(group)
            all_events.extend(events)
            logger.info(f"  Found {len(events)} events")
        return all_events


class RuleBasedDetector:
    """Fast, local anomaly detection using pattern matching."""

    ANOMALY_PATTERNS = [
        {
            "name": "high_value_transfer",
            "pattern": r"amount[=:]?\s*\$?(\d+\.?\d*)",
            "threshold": 5000,
            "severity": "medium",
        },
        {
            "name": "authentication_failure",
            "pattern": r"(401|unauthorized|invalid.?token|invalid.?credentials)",
            "severity": "low",
        },
        {
            "name": "server_error",
            "pattern": r"(500|internal.?server.?error|traceback|exception)",
            "severity": "high",
        },
        {
            "name": "rapid_requests",
            "pattern": r"(rate.?limit|too.?many.?requests|429)",
            "severity": "medium",
        },
        {
            "name": "anomaly_flagged",
            "pattern": r"(ANOMALY.?DETECTED|flagged|suspicious|fraud)",
            "severity": "high",
        },
    ]

    def analyze(self, events: list[dict]) -> list[dict]:
        anomalies = []
        error_count = 0
        auth_failure_count = 0
        flagged_transactions = []

        for event in events:
            msg = event["message"].lower()

            for pattern_def in self.ANOMALY_PATTERNS:
                match = re.search(pattern_def["pattern"], msg, re.IGNORECASE)
                if match:
                    if pattern_def["name"] == "high_value_transfer" and match.group(1):
                        amount = float(match.group(1))
                        if amount < pattern_def.get("threshold", 0):
                            continue

                    anomaly = {
                        "rule": pattern_def["name"],
                        "severity": pattern_def["severity"],
                        "timestamp": event["timestamp"],
                        "log_group": event["log_group"],
                        "message": event["message"][:300],
                    }
                    anomalies.append(anomaly)

                    if pattern_def["name"] == "server_error":
                        error_count += 1
                    elif pattern_def["name"] == "authentication_failure":
                        auth_failure_count += 1
                    elif pattern_def["name"] == "anomaly_flagged":
                        flagged_transactions.append(event)

        if error_count > 5:
            anomalies.append({
                "rule": "error_spike",
                "severity": "high",
                "message": f"Error spike detected: {error_count} server errors in the analysis window",
            })

        if auth_failure_count > 10:
            anomalies.append({
                "rule": "brute_force_attempt",
                "severity": "high",
                "message": f"Possible brute force: {auth_failure_count} auth failures detected",
            })

        return anomalies


class OpenAIAnalyzer:
    """Sends suspicious events to OpenAI for intelligent analysis."""

    def __init__(self):
        if not OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set — AI analysis disabled")
            self.client = None
            return
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=OPENAI_API_KEY)
        except ImportError:
            logger.warning("openai package not installed — AI analysis disabled")
            self.client = None

    def analyze(self, anomalies: list[dict], events_summary: dict) -> str:
        if not self.client:
            return self._generate_local_summary(anomalies, events_summary)

        prompt = self._build_prompt(anomalies, events_summary)

        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a fintech security analyst. Analyze the following anomaly "
                            "data from a cloud-native financial platform. Provide a concise, "
                            "actionable summary of potential security threats, fraud patterns, "
                            "and recommended actions. Be specific about severity levels."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return self._generate_local_summary(anomalies, events_summary)

    def _build_prompt(self, anomalies: list[dict], events_summary: dict) -> str:
        return f"""Analyze these anomalies from our fintech platform:

**Events Summary (last {LOOKBACK_MINUTES} minutes):**
- Total log events analyzed: {events_summary.get('total_events', 0)}
- Log groups monitored: {', '.join(events_summary.get('log_groups', []))}

**Detected Anomalies ({len(anomalies)} total):**
{json.dumps(anomalies[:20], indent=2, default=str)}

Provide:
1. Risk assessment (Critical / High / Medium / Low)
2. Summary of suspicious patterns
3. Recommended actions
4. Whether this looks like normal activity or a genuine threat"""

    def _generate_local_summary(self, anomalies: list[dict], events_summary: dict) -> str:
        if not anomalies:
            return (
                f"✅ No anomalies detected in the last {LOOKBACK_MINUTES} minutes. "
                f"Analyzed {events_summary.get('total_events', 0)} events across "
                f"{len(events_summary.get('log_groups', []))} log groups."
            )

        high = sum(1 for a in anomalies if a.get("severity") == "high")
        medium = sum(1 for a in anomalies if a.get("severity") == "medium")
        low = sum(1 for a in anomalies if a.get("severity") == "low")

        lines = [
            f"⚠️  Anomaly Report — {len(anomalies)} anomalies detected",
            f"   High: {high} | Medium: {medium} | Low: {low}",
            f"   Period: last {LOOKBACK_MINUTES} minutes",
            f"   Events analyzed: {events_summary.get('total_events', 0)}",
            "",
            "Findings:",
        ]

        seen_rules = set()
        for a in anomalies:
            rule = a.get("rule", "unknown")
            if rule not in seen_rules:
                seen_rules.add(rule)
                lines.append(f"  - [{a.get('severity', 'unknown').upper()}] {a.get('message', rule)}")

        return "\n".join(lines)


def run_analysis():
    logger.info("=" * 60)
    logger.info("FinCloud Anomaly Detection — Starting analysis")
    logger.info("=" * 60)

    fetcher = CloudWatchLogFetcher()
    events = fetcher.fetch_all_logs()

    events_summary = {
        "total_events": len(events),
        "log_groups": list(set(e["log_group"] for e in events)),
    }

    logger.info(f"Total events collected: {len(events)}")

    detector = RuleBasedDetector()
    anomalies = detector.analyze(events)

    logger.info(f"Rule-based anomalies found: {len(anomalies)}")

    analyzer = OpenAIAnalyzer()
    report = analyzer.analyze(anomalies, events_summary)

    logger.info("\n" + "=" * 60)
    logger.info("ANOMALY DETECTION REPORT")
    logger.info("=" * 60)
    print(report)
    logger.info("=" * 60)

    return {"anomalies": len(anomalies), "report": report}


def main():
    parser = argparse.ArgumentParser(description="FinCloud AI Anomaly Detector")
    parser.add_argument(
        "--schedule",
        type=int,
        default=0,
        help="Run on schedule every N minutes (0 = one-time run)",
    )
    args = parser.parse_args()

    if args.schedule > 0:
        import schedule

        logger.info(f"Running anomaly detection every {args.schedule} minutes")
        schedule.every(args.schedule).minutes.do(run_analysis)
        run_analysis()  # Run immediately on start
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        run_analysis()


if __name__ == "__main__":
    main()
