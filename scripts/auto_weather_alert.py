import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen
from zoneinfo import ZoneInfo

ALERT_FILE = Path("alert.json")
MANAGED_ID = "auto-weather-alert"

URL_ZH = "https://www.td.gov.hk/tc/special_news/spnews.htm"
URL_EN = "https://www.td.gov.hk/en/special_news/spnews.htm"

HKO_URL_TC = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=warnsum&lang=tc"
HKO_URL_EN = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=warnsum&lang=en"


def fetch_json(url: str) -> dict:
    with urlopen(url, timeout=20) as response:
        return json.load(response)


def hk_time(offset_minutes: int = 0) -> str:
    return (
        datetime.now(ZoneInfo("Asia/Hong_Kong")) + timedelta(minutes=offset_minutes)
    ).replace(microsecond=0).isoformat()


warnsum_tc = fetch_json(HKO_URL_TC)
warnsum_en = fetch_json(HKO_URL_EN)

warning_parts_zh = []
warning_parts_en = []

tc_code = warnsum_en.get("WTCSGNL", {}).get("code", "")
match = re.match(r"^TC(\d+)", tc_code)
tc_signal = int(match.group(1)) if match else 0

# Typhoon first.
if tc_signal >= 8:
    warning_parts_zh.append(
        warnsum_tc.get("WTCSGNL", {}).get("name") or f"{tc_signal}號熱帶氣旋警告信號"
    )
    warning_parts_en.append(
        warnsum_en.get("WTCSGNL", {}).get("name") or f"No. {tc_signal} Tropical Cyclone Warning Signal"
    )

# Black rain second.
if warnsum_en.get("WRAIN", {}).get("code") == "WRAINB":
    warning_parts_zh.append(
        warnsum_tc.get("WRAIN", {}).get("name") or "黑色暴雨警告"
    )
    warning_parts_en.append(
        warnsum_en.get("WRAIN", {}).get("name") or "Black Rainstorm Warning"
    )

try:
    current = json.loads(ALERT_FILE.read_text(encoding="utf-8"))
except FileNotFoundError:
    current = {}

extras = current.get("extras") if isinstance(current.get("extras"), list) else []

# Remove only the alert previously created by this script.
extras = [alert for alert in extras if alert.get("_managedBy") != MANAGED_ID]

if warning_parts_zh:
    extras.insert(0, {
        "_managedBy": MANAGED_ID,
        "content": {
            "zh": f"{'及'.join(warning_parts_zh)}現正生效",
            "en": f"{' & '.join(warning_parts_en)} in force",
        },
        "url": URL_ZH,
        "urlEn": URL_EN,
        "validFrom": hk_time(-5),
        "validTo": hk_time(15),
    })

current["extras"] = extras

ALERT_FILE.write_text(
    json.dumps(current, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)