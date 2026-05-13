import requests
import time
import json
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# ===== НАЛАШТУВАННЯ =====
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

CHECK_INTERVAL = 180
TRIGGER_GOALS = [4, 5, 6]
TRIGGER_MAX_MINUTE = 75

# Активний час (Київський час)
ACTIVE_HOUR_START = 7
ACTIVE_HOUR_END = 23

BLOCKED_KEYWORDS = [
    "u16", "u17", "u18", "u19", "u20", "u21", "u23",
    "youth", "junior", "juniors", "academy", "women", "woman",
    "ladies", "female", "girls", "reserve", "reserves", "b team"
]

# ===== СТАН =====
ALERTED_FILE = "alerted.json"
alerted = {}
HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "flashscore4.p.rapidapi.com",
    "Content-Type": "application/json"
}

# =========================
def load_alerted():
    global alerted
    if os.path.exists(ALERTED_FILE):
        try:
            with open(ALERTED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                alerted = {k: set(v) for k, v in data.items()}
        except:
            alerted = {}

def save_alerted():
    try:
        with open(ALERTED_FILE, "w", encoding="utf-8") as f:
            json.dump({k: list(v) for k, v in alerted.items()}, f, ensure_ascii=False)
    except:
        pass

# =========================
def is_allowed_league(name):
    if not name:
        return True
    n = name.lower()
    return not any(kw in n for kw in BLOCKED_KEYWORDS)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        print(f"Telegram: {r.status_code}")
    except Exception as e:
        print(f"Telegram error: {e}")

def api_get(url, params=None):
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=12)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"API Error {r.status_code}: {r.text[:150]}")
            return None
    except Exception as e:
        print(f"API Exception: {e}")
        return None

def get_live_matches():
    data = api_get(
        "https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/live",
        {"sport_id": "1", "timezone": "Europe/Berlin"}
    )

    # ===== ДЕБАГ API =====
    if data is not None:
        print(f"\n🔍 RAW тип даних: {type(data)}")
        if isinstance(data, dict):
            print(f"🔍 RAW ключі: {list(data.keys())}")
            print(f"🔍 RAW перші 500 символів: {str(data)[:500]}")
        elif isinstance(data, list):
            print(f"🔍 RAW список, {len(data)} елементів")
            print(f"🔍 RAW перший елемент: {str(data[0])[:300] if data else 'пустий'}")
    else:
        print("🔍 RAW: None — API не відповів")
    # ===== КІНЕЦЬ ДЕБАГУ =====

    return data

# =========================
def get_match_extra_info(match_id):
    ht = api_get("https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/details", {"match_id": match_id})
    stats = api_get("https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/stats", {"match_id": match_id})
    return ht, stats

# =========================
def check_matches(data):
    if not data:
        print("⚠️ data порожній, нічого перевіряти")
        return

    if isinstance(data, dict):
        for key in ["matches", "data", "events", "live"]:
            if key in data:
                print(f"🔍 Знайдено ключ '{key}' в data, використовую його")
                data = data[key]
                break
        else:
            print(f"🔍 data це dict але без відомих ключів. Ключі: {list(data.keys())}")
            return

    if not isinstance(data, list):
        print(f"⚠️ data не список і не dict з матчами: {type(data)}")
        return

    total = filtered = 0
    for block in data:
        if isinstance(block, dict) and "matches" in block:
            tournament_name = block.get("name", "Unknown")
            matches = block.get("matches", [])
        elif isinstance(block, dict) and "match_id" in block:
            tournament_name = block.get("tournament", {}).get("name", "Unknown")
            matches = [block]
        else:
            print(f"🔍 Незнайома структура блоку: {str(block)[:200]}")
            continue

        total += len(matches)
        if not is_allowed_league(tournament_name):
            continue
        filtered += len(matches)

        for match in matches:
            try:
                process_match(match, tournament_name)
            except Exception as e:
                print(f"Error processing match: {e}")

    print(f"📊 {filtered} матчів оброблено (всього {total})")

def process_match(match, tournament_name):
    match_id = str(match.get("match_id"))
    if not match_id:
        return

    home = match.get("home_team", {}).get("name", "Господарі")
    away = match.get("away_team", {}).get("name", "Гості")

    scores = match.get("scores", {})
    home_score = int(scores.get("home", 0) or 0)
    away_score = int(scores.get("away", 0) or 0)
    total_goals = home_score + away_score

    status = match.get("match_status", {})
    stage = status.get("stage", "")
    minute_raw = status.get("live_time", "0")

    # ===== ДЕБАГ: логуємо всі матчі з 3+ голами ДО фільтрації =====
    if total_goals >= 3:
        print(f"🔎 {home} vs {away} | stage='{stage}' | minute_raw='{minute_raw}' | score={home_score}-{away_score}")
    # ===== КІНЕЦЬ ДЕБАГУ =====

    try:
        minute = int(str(minute_raw).replace("+", "").split("+")[0])
    except:
        minute = 0

    if stage == "1st Half":
        actual_minute = minute
    elif stage == "2nd Half":
        actual_minute = 45 + minute
    else:
        # ===== ДЕБАГ: показуємо що відкинули і чому =====
        if total_goals >= 3:
            print(f"  ⏭️ Пропускаємо — stage='{stage}' не є 1st/2nd Half")
        # ===== КІНЕЦЬ ДЕБАГУ =====
        return

    if actual_minute < 1 or actual_minute > TRIGGER_MAX_MINUTE:
        if total_goals >= 3:
            print(f"  ⏭️ Пропускаємо — хвилина {actual_minute}' поза діапазоном (1-{TRIGGER_MAX_MINUTE})")
        return

    for threshold in TRIGGER_GOALS:
        if total_goals < threshold:
            break

        if match_id not in alerted:
            alerted[match_id] = set()

        if threshold in alerted[match_id]:
            print(f"  ✔️ {threshold} голів вже надсилали для {home} vs {away}")
            continue

        # === Тригер! ===
        alerted[match_id].add(threshold)
        save_alerted()

        ht_data, stats_data = get_match_extra_info(match_id)

        icon = "⚽" if threshold == 4 else "🔥" if threshold == 5 else "💥"

        msg = f"{icon} <b>{threshold} ГОЛІВ!</b>\n"
        msg += f"🏆 {tournament_name}\n"
        msg += f"<b>{home} {home_score} - {away_score} {away}</b>\n"
        msg += f"🕐 {actual_minute}' хвилина\n"
        msg += f"📈 Всього: {total_goals} голів\n"
        msg += f"✅ Алерт!"

        print(f"\n🚨 АЛЕРТ {threshold} голів: {home} vs {away} | {actual_minute}'\n")
        send_telegram(msg)

# =========================
def main():
    load_alerted()
    print("🤖 Football Alert Bot v17+debug запущено!")
    print(f"Тригери: {TRIGGER_GOALS} голів до {TRIGGER_MAX_MINUTE}' | Інтервал: {CHECK_INTERVAL} сек")

    send_telegram("🤖 <b>Football Alert Bot v17+debug запущено!</b>\nАлерти на 4-5-6 голів")

    while True:
        now = datetime.now(timezone(timedelta(hours=3)))  # Київський час
        hour = now.hour

        if ACTIVE_HOUR_START <= hour < ACTIVE_HOUR_END:
            print(f"\n⏰ [{now.strftime('%H:%M')}] Перевіряю live матчі...")
            data = get_live_matches()
            check_matches(data)
        else:
            print(f"😴 [{now.strftime('%H:%M')}] Спимо...")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
