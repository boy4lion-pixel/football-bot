import requests
import time
from datetime import datetime

# ===== НАЛАШТУВАННЯ =====
TELEGRAM_TOKEN = "8440346164:AAFZzfshhUsgN6MWbrfXQE6OXGFTKhJ6eEk"
CHAT_ID = "439583139"
RAPIDAPI_KEY = "b4bd4a4ab1msh31fe8f92668fd14p1b8e80jsnfa2ae02b25cf"

CHECK_INTERVAL = 180
TRIGGER_GOALS = [5]
TRIGGER_MAX_MINUTE = 80

ACTIVE_HOUR_START = 7
ACTIVE_HOUR_END = 22

BLOCKED_KEYWORDS = [
    "u16", "u17", "u18", "u19", "u20", "u21", "u23",
    "youth", "junior", "juniors", "academy",
    "women", "woman", "ladies", "female", "girls",
    "reserve", "reserves", "b team",
]

alerted = {}

HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "flashscore4.p.rapidapi.com",
    "Content-Type": "application/json"
}


def is_allowed_league(name):
    if not name:
        return True
    return not any(kw in name.lower() for kw in BLOCKED_KEYWORDS)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
        print("✅ Telegram надіслано" if r.status_code == 200 else f"❌ Telegram: {r.status_code}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")


def api_get(url, params=None):
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=12)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        print(f"❌ API error: {e}")
        return None


def get_live_matches():
    try:
        r = requests.get(
            "https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/live",
            headers=HEADERS,
            params={"sport_id": "1", "timezone": "Europe/Berlin"},
            timeout=15
        )
        if r.status_code == 200:
            print("✅ API OK")
            return r.json()
        else:
            print(f"❌ API: {r.status_code}")
            return None
    except Exception as e:
        print(f"❌ API exception: {e}")
        return None


def is_match_live(status):
    """Жорстка перевірка — чи матч ще точно живий"""
    if not status:
        return False
    
    stage = str(status.get("stage", "")).lower()
    status_type = str(status.get("type", "")).lower()
    minute_raw = str(status.get("live_time", "0"))

    # Якщо статус явно finished
    if any(x in status_type for x in ["finish", "ft", "end", "penalt", "after"]):
        return False
    
    # Якщо хвилина 80+ і великий рахунок — вважаємо finished
    try:
        minute = int(minute_raw.replace("+", "").split("+")[0])
        if minute >= 80 and (status.get("stage") == "2nd Half"):
            return False
    except:
        pass

    # Якщо матч у 2nd Half і рахунок вже 6+ — теж часто finished
    return True


def process_match(match, tournament_name):
    match_id = str(match.get("match_id", ""))
    if not match_id:
        return

    home_team = match.get("home_team", {})
    away_team = match.get("away_team", {})
    home = home_team.get("name", "Господарі")
    away = away_team.get("name", "Гості")

    status = match.get("match_status", {})

    # === ФІЛЬТРАЦІЯ ===
    if not is_match_live(status):
        return

    stage = status.get("stage", "")
    if stage not in ["1st Half", "2nd Half"]:
        return

    minute_raw = status.get("live_time", "0")
    try:
        minute = int(str(minute_raw).replace("+", "").split("+")[0])
    except:
        minute = 0

    actual_minute = minute if stage == "1st Half" else 45 + minute

    if actual_minute < 1 or actual_minute > TRIGGER_MAX_MINUTE:
        return

    scores = match.get("scores", {})
    home_score = int(scores.get("home", 0) or 0)
    away_score = int(scores.get("away", 0) or 0)
    total_goals = home_score + away_score

    # Дебаг
    if total_goals >= 4:
        print(f"🔎 {home} vs {away} | {home_score}-{away_score} | {actual_minute}' | Stage: {stage} | Type: {status.get('type')}")

    for threshold in TRIGGER_GOALS:
        if total_goals < threshold:
            break

        if match_id not in alerted:
            alerted[match_id] = set()
        if threshold in alerted[match_id]:
            continue

        alerted[match_id].add(threshold)

        msg = f"🔥 <b>АЛЕРТ! {threshold}+ ГОЛІВ!</b>\n"
        msg += f"🏆 {tournament_name}\n"
        msg += f"<b>{home} {home_score} - {away_score} {away}</b>\n"
        msg += f"🕐 Хвилина: {actual_minute}'\n"
        msg += f"✅ Live алерт!"

        print(f"\n🚨 АЛЕРТ {threshold}+: {home} vs {away} ({actual_minute}')\n")
        send_telegram(msg)


def check_matches(data):
    if not data:
        return

    total = filtered = 0
    for block in data:
        if not isinstance(block, dict):
            continue
        name = block.get("name", "")
        matches = block.get("matches", [])
        total += len(matches)

        if not is_allowed_league(name):
            continue

        filtered += len(matches)
        for match in matches:
            try:
                process_match(match, name)
            except Exception as e:
                print(f"⚠️ Error: {e}")

    print(f"📊 Перевірено: {filtered} матчів (всього {total})")


def main():
    print("🤖 Football Alert Bot v18 (жорстка фільтрація) запущено!")

    send_telegram("🤖 <b>Bot v18 запущено</b>\nЖорстка фільтрація завершених матчів")

    while True:
        now = datetime.now()
        if ACTIVE_HOUR_START <= now.hour < ACTIVE_HOUR_END:
            print(f"\n⏰ [{now.strftime('%H:%M:%S')}] Перевіряю live...")
            data = get_live_matches()
            check_matches(data)
            print(f"💤 Чекаю {CHECK_INTERVAL} сек...")
            time.sleep(CHECK_INTERVAL)
        else:
            print(f"😴 Спимо...")
            time.sleep(600)


if __name__ == "__main__":
    main()
