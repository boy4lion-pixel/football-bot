import requests
import time
from datetime import datetime

# ===== НАЛАШТУВАННЯ =====
TELEGRAM_TOKEN = "8440346164:AAFZzfshhUsgN6MWbrfXQE6OXGFTKhJ6eEk"
CHAT_ID = "439583139"
RAPIDAPI_KEY = "b4bd4a4ab1msh31fe8f92668fd14p1b8e80jsnfa2ae02b25cf"

CHECK_INTERVAL = 180

# ===== ТРИГЕРИ =====
TRIGGER_GOALS = [5]
TRIGGER_MAX_MINUTE = 80

# ===== АКТИВНИЙ ЧАС (UTC) =====
ACTIVE_HOUR_START = 7
ACTIVE_HOUR_END = 22

# ===== БЛОКУЄМО =====
BLOCKED_KEYWORDS = [
    "u16", "u17", "u18", "u19", "u20", "u21", "u23",
    "youth", "junior", "juniors", "academy",
    "women", "woman", "ladies", "female", "girls",
    "reserve", "reserves", "b team",
]

# ===== СТАН =====
alerted = {}

HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "flashscore4.p.rapidapi.com",
    "Content-Type": "application/json"
}


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
        if r.status_code == 200:
            print("✅ Telegram надіслано")
        else:
            print(f"❌ Telegram: {r.status_code}")
    except Exception as e:
        print(f"❌ Telegram exception: {e}")


def api_get(url, params=None):
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=12)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"❌ API {r.status_code}")
            return None
    except Exception as e:
        print(f"❌ API exception: {e}")
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


def get_match_details(match_id):
    data = api_get(
        "https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/details",
        {"match_id": match_id}
    )
    if not data:
        return None, None
    try:
        scores = data.get("scores", {})
        ht_home = scores.get("home_1st_half") or scores.get("ht_home")
        ht_away = scores.get("away_1st_half") or scores.get("ht_away")
        if ht_home is not None and ht_away is not None:
            return int(ht_home), int(ht_away)
    except:
        pass
    return None, None


def get_team_max_goals(team_id):
    if not team_id:
        return None
    data = api_get(
        "https://flashscore4.p.rapidapi.com/api/flashscore/v2/teams/results",
        {"team_id": team_id, "page": "1"}
    )
    if not data:
        return None
    try:
        max_g = 0
        count = 0
        blocks = data if isinstance(data, list) else [data]
        for block in blocks:
            matches = block.get("matches", []) if isinstance(block, dict) else []
            for m in matches:
                if count >= 5:
                    break
                s = m.get("scores", {})
                total = int(s.get("home", 0) or 0) + int(s.get("away", 0) or 0)
                if total > max_g:
                    max_g = total
                count += 1
        return max_g if count > 0 else None
    except:
        return None


def get_h2h_max(match_id):
    data = api_get(
        "https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/h2h",
        {"match_id": match_id}
    )
    if not data:
        return None, None
    try:
        max_g = 0
        max_score = ""
        count = 0
        blocks = data if isinstance(data, list) else [data]
        for block in blocks:
            matches = block.get("matches", []) if isinstance(block, dict) else []
            for m in matches:
                if count >= 5:
                    break
                s = m.get("scores", {})
                h = int(s.get("home", 0) or 0)
                a = int(s.get("away", 0) or 0)
                if h + a > max_g:
                    max_g = h + a
                    max_score = f"{h}-{a}"
                count += 1
        return (max_g, max_score) if max_g > 0 else (None, None)
    except:
        return None, None


def process_match(match, tournament_name):
    match_id = str(match.get("match_id", ""))
    if not match_id:
        return

    home_team = match.get("home_team", {})
    away_team = match.get("away_team", {})
    home = home_team.get("name", "Господарі")
    away = away_team.get("name", "Гості")
    home_id = home_team.get("team_id") or home_team.get("id")
    away_id = away_team.get("team_id") or away_team.get("id")

    status = match.get("match_status", {})
    stage = status.get("stage", "")
    status_type = str(status.get("type", "")).lower()
    status_code = status.get("code")

    # === ФІЛЬТР ЗАВЕРШЕНИХ МАТЧІВ ===
    if any(word in status_type for word in ["finish", "ft", "end", "penalties", "after"]) or status_code in [100, 200]:
        return

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
        print(f"🔎 {home} vs {away} | {home_score}-{away_score} | {actual_minute}' | Stage: {stage}")

    for threshold in TRIGGER_GOALS:
        if total_goals < threshold:
            break

        if match_id not in alerted:
            alerted[match_id] = set()
        if threshold in alerted[match_id]:
            continue

        alerted[match_id].add(threshold)

        # HT score
        if stage == "1st Half":
            ht_home, ht_away = home_score, away_score
            ht_known = True
        else:
            ht_home, ht_away = get_match_details(match_id)
            ht_known = ht_home is not None

        home_max = get_team_max_goals(home_id)
        away_max = get_team_max_goals(away_id)
        h2h_max, h2h_score = get_h2h_max(match_id)

        msg = f"🔥 <b>АЛЕРТ! {threshold}+ ГОЛІВ!</b>\n"
        msg += f"🏆 {tournament_name}\n"
        msg += f"<b>{home} {home_score} - {away_score} {away}</b>\n"
        msg += f"🕐 Хвилина: {actual_minute}'\n"

        if ht_known:
            msg += f"📊 1-й тайм: {ht_home}-{ht_away}\n"

        if home_max or away_max:
            msg += f"{'━'*10}\n📋 Форма (останні 5 матчів):\n"
            if home_max:
                msg += f"• {home}: макс {home_max} голів\n"
            if away_max:
                msg += f"• {away}: макс {away_max} голів\n"

        if h2h_max:
            msg += f"🤝 H2H максимум: {h2h_max} голів ({h2h_score})\n"

        msg += f"✅ Тригер спрацював!"

        print(f"\n🚨 АЛЕРТ {threshold}+ голів: {home} vs {away} ({actual_minute}')\n")
        send_telegram(msg)


def check_matches(data):
    if not data:
        print("⚠️ Дані порожні")
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
                print(f"⚠️ Помилка в process_match: {e}")

    print(f"📊 Перевірено: {filtered} матчів (всього {total})")


def main():
    print("🤖 Football Alert Bot v16 (оновлений) запущено!")
    print(f"Тригер: {TRIGGER_GOALS[0]}+ голів до {TRIGGER_MAX_MINUTE}' хвилини")

    send_telegram(
        f"🤖 <b>Football Alert Bot v16 запущено!</b>\n"
        f"Алерт: {TRIGGER_GOALS[0]}+ голів до {TRIGGER_MAX_MINUTE}'\n"
        f"Тільки live матчі"
    )

    while True:
        now = datetime.now()
        if ACTIVE_HOUR_START <= now.hour < ACTIVE_HOUR_END:
            print(f"\n⏰ [{now.strftime('%H:%M:%S')}] Перевіряю live матчі...")
            data = get_live_matches()
            check_matches(data)
            print(f"💤 Чекаю {CHECK_INTERVAL} секунд...")
            time.sleep(CHECK_INTERVAL)
        else:
            print(f"😴 [{now.strftime('%H:%M')}] Спимо...")
            time.sleep(600)


if __name__ == "__main__":
    main()
