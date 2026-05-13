import requests
import time
from datetime import datetime

# ===== НАЛАШТУВАННЯ =====
TELEGRAM_TOKEN = "8440346164:AAFZzfshhUsgN6MWbrfXQE6OXGFTKhJ6eEk"
CHAT_ID = "439583139"
RAPIDAPI_KEY = "b4bd4a4ab1msh31fe8f92668fd14p1b8e80jsnfa2ae02b25cf"
CHECK_INTERVAL = 180

# ===== ТРИГЕРИ =====
TRIGGER_GOALS = [4, 5, 6]
TRIGGER_MAX_MINUTE = 75

# ===== АКТИВНИЙ ЧАС (UTC) =====
ACTIVE_HOUR_START = 7
ACTIVE_HOUR_END = 22

# ===== БЛОКУЄМО ТІЛЬКИ ЦЕ =====
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
    n = name.lower()
    return not any(kw in n for kw in BLOCKED_KEYWORDS)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
        if r.status_code == 200:
            print("✅ Telegram надіслано")
        else:
            print(f"❌ Telegram: {r.text}")
    except Exception as e:
        print(f"❌ Telegram exception: {e}")


def api_get(url, params):
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        return r.json() if r.status_code == 200 else None
    except:
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
            data = r.json()

            # ===== ДЕБАГ =====
            print(f"\n🔍 RAW тип даних: {type(data)}")
            if isinstance(data, dict):
                print(f"🔍 RAW ключі: {list(data.keys())}")
                print(f"🔍 RAW перші 500 символів: {str(data)[:500]}")
            elif isinstance(data, list):
                print(f"🔍 RAW список, {len(data)} елементів")
                print(f"🔍 RAW перший елемент: {str(data[0])[:300] if data else 'пустий'}")
            else:
                print(f"🔍 RAW: {str(data)[:500]}")
            # ===== КІНЕЦЬ ДЕБАГУ =====

            print("✅ API OK")
            return data
        else:
            print(f"❌ API: {r.status_code} - {r.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ API exception: {e}")
        return None


def get_ht_score(match_id):
    data = api_get("https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/details", {"match_id": match_id})
    if not data:
        return None, None
    try:
        scores = data.get("scores", {})
        ht_h = scores.get("ht_home", scores.get("halftime_home"))
        ht_a = scores.get("ht_away", scores.get("halftime_away"))
        if ht_h is not None:
            return int(ht_h), int(ht_a)
    except:
        pass
    return None, None


def get_stats(match_id):
    data = api_get("https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/stats", {"match_id": match_id})
    xg_h = xg_a = sh_h = sh_a = pos_h = pos_a = None
    if not data:
        return xg_h, xg_a, sh_h, sh_a, pos_h, pos_a
    items = data if isinstance(data, list) else data.get("stats", data.get("data", []))
    for item in items:
        name = str(item.get("name", item.get("stat_name", ""))).lower()
        hv = item.get("home", item.get("home_value", ""))
        av = item.get("away", item.get("away_value", ""))
        if "expected goals" in name or name == "xg":
            xg_h, xg_a = hv, av
        elif "shot" in name and "target" not in name and sh_h is None:
            sh_h, sh_a = hv, av
        elif "possession" in name:
            pos_h, pos_a = hv, av
    return xg_h, xg_a, sh_h, sh_a, pos_h, pos_a


def get_team_max_goals(team_id):
    data = api_get("https://flashscore4.p.rapidapi.com/api/flashscore/v2/teams/results", {"team_id": team_id, "page": "1"})
    if not data:
        return None
    try:
        matches = data if isinstance(data, list) else data.get("matches", data.get("results", data.get("data", [])))
        max_g = 0
        for i, m in enumerate(matches):
            if i >= 5:
                break
            s = m.get("scores", {})
            total = int(s.get("home", 0) or 0) + int(s.get("away", 0) or 0)
            if total > max_g:
                max_g = total
        return max_g
    except:
        return None


def get_h2h_max(match_id):
    data = api_get("https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/h2h", {"match_id": match_id})
    if not data:
        return None, None
    try:
        matches = data if isinstance(data, list) else data.get("matches", data.get("h2h", data.get("data", [])))
        max_g = 0
        max_score = ""
        for i, m in enumerate(matches):
            if i >= 5:
                break
            s = m.get("scores", {})
            h = int(s.get("home", 0) or 0)
            a = int(s.get("away", 0) or 0)
            if h + a > max_g:
                max_g = h + a
                max_score = f"{h}-{a}"
        return (max_g, max_score) if max_g > 0 else (None, None)
    except:
        return None, None


def check_matches(data):
    if not data:
        print("⚠️ data порожній, нічого перевіряти")
        return

    # ===== ДЕБАГ: розбираємо структуру =====
    if isinstance(data, dict):
        # Можливо матчі лежать в якомусь ключі
        possible_keys = ["matches", "data", "events", "results", "live"]
        for key in possible_keys:
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
    # ===== КІНЕЦЬ ДЕБАГУ =====

    total = filtered = 0
    for block in data:
        # Блок може бути або {"name": "Liga", "matches": [...]}
        # або просто матчем напряму
        if isinstance(block, dict) and "matches" in block:
            name = block.get("name", "")
            matches = block.get("matches", [])
        elif isinstance(block, dict) and "match_id" in block:
            # Матч напряму без обгортки
            name = block.get("tournament", {}).get("name", "Unknown")
            matches = [block]
        else:
            print(f"🔍 Незнайома структура блоку: {str(block)[:200]}")
            continue

        total += len(matches)
        if not is_allowed_league(name):
            continue
        filtered += len(matches)
        for match in matches:
            try:
                process_match(match, name)
            except Exception as e:
                print(f"⚠️ {e}")

    print(f"📊 {filtered} матчів (всього {total})")


def process_match(match, tournament_name):
    match_id = match.get("match_id", "unknown")
    home_team = match.get("home_team", {})
    away_team = match.get("away_team", {})
    home = home_team.get("name", "Господарі")
    away = away_team.get("name", "Гості")
    home_id = home_team.get("id")
    away_id = away_team.get("id")

    status = match.get("match_status", {})
    stage = status.get("stage", "")
    minute_raw = status.get("live_time", "0")

    try:
        minute = int(str(minute_raw).replace("+", "").split("+")[0])
    except:
        minute = 0

    if stage == "1st Half":
        actual_minute = minute
    elif stage == "2nd Half":
        actual_minute = 45 + minute
    else:
        return

    if actual_minute == 0 or actual_minute > TRIGGER_MAX_MINUTE:
        return

    scores = match.get("scores", {})
    home_score = int(scores.get("home", 0) or 0)
    away_score = int(scores.get("away", 0) or 0)
    total_goals = home_score + away_score

    # ===== ДЕБАГ: матчі з голами =====
    if total_goals >= 3:
        print(f"👀 Матч з {total_goals} голами: {home} {home_score}-{away_score} {away} | {stage} {actual_minute}'")
    # ===== КІНЕЦЬ ДЕБАГУ =====

    for threshold in TRIGGER_GOALS:
        if total_goals < threshold:
            break

        if match_id not in alerted:
            alerted[match_id] = set()
        if threshold in alerted[match_id]:
            continue

        alerted[match_id].add(threshold)

        if stage == "1st Half":
            ht_home, ht_away = home_score, away_score
            ht_known = True
        else:
            ht_home, ht_away = get_ht_score(match_id)
            ht_known = ht_home is not None

        xg_h, xg_a, sh_h, sh_a, pos_h, pos_a = get_stats(match_id)
        home_max = get_team_max_goals(home_id) if home_id else None
        away_max = get_team_max_goals(away_id) if away_id else None
        h2h_max, h2h_score = get_h2h_max(match_id)

        icon = "⚽" if threshold == 4 else ("🔥" if threshold == 5 else "💥")

        msg = f"{icon} <b>АЛЕРТ! {threshold} ГОЛИ!</b>\n"
        msg += f"🏆 {tournament_name}\n"
        msg += f"<b>{home} {home_score} - {away_score} {away}</b>\n"
        msg += f"🕐 Хвилина: {actual_minute}'\n"

        if ht_known:
            msg += f"📊 1-й тайм: {ht_home}-{ht_away} ({ht_home+ht_away} голів)\n"
        else:
            msg += f"📊 1-й тайм: невідомо\n"

        msg += f"📈 Всього голів: {total_goals}\n"

        if any(x is not None for x in [xg_h, sh_h, pos_h]):
            msg += f"{'━'*10}\n"
            if xg_h is not None:
                msg += f"📐 xG: {xg_h} - {xg_a}\n"
            if sh_h is not None:
                msg += f"⚽ Удари: {sh_h} - {sh_a}\n"
            if pos_h is not None:
                msg += f"🎯 Володіння: {pos_h}% - {pos_a}%\n"

        if home_max is not None or away_max is not None:
            msg += f"{'━'*10}\n📋 Форма (останні 5):\n"
            if home_max is not None:
                msg += f"  {home}: макс {home_max} голів\n"
            if away_max is not None:
                msg += f"  {away}: макс {away_max} голів\n"

        if h2h_max is not None:
            msg += f"🤝 H2H макс: {h2h_max} голів ({h2h_score})\n"

        msg += f"✅ Тригер спрацював!"

        print(f"\n🚨 {threshold} ГОЛІВ: {tournament_name}: {home} {home_score}-{away_score} {away} | {actual_minute}'\n")
        send_telegram(msg)


def main():
    print("🤖 Football Alert Bot v15 (debug) запущено!")
    print(f"⚙️ Тригери: {TRIGGER_GOALS} голів до {TRIGGER_MAX_MINUTE}'")

    send_telegram(
        f"🤖 <b>Football Alert Bot v15 (debug)!</b>\n"
        f"Алерти: {', '.join(str(g)+'+' for g in TRIGGER_GOALS)} голів до {TRIGGER_MAX_MINUTE}'\n"
        f"Всі ліги крім жіночих та юнацьких\n"
        f"Активний: 10:00-01:00 (Київ)"
    )

    while True:
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")

        if ACTIVE_HOUR_START <= now.hour < ACTIVE_HOUR_END:
            print(f"\n⏰ [{time_str}] Перевіряю матчі...")
            data = get_live_matches()
            check_matches(data)
            print(f"💤 Чекаю {CHECK_INTERVAL} сек...")
            time.sleep(CHECK_INTERVAL)
        else:
            print(f"😴 [{time_str}] Сплю до 10:00 Київ...")
            time.sleep(600)


if __name__ == "__main__":
    main()
