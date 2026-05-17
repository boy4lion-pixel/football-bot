import requests
import time
from datetime import datetime

# ===== НАЛАШТУВАННЯ =====
TELEGRAM_TOKEN = "8440346164:AAFZzfshhUsgN6MWbrfXQE6OXGFTKhJ6eEk"
CHAT_ID = "439583139"
RAPIDAPI_KEY = "b4bd4a4ab1msh31fe8f92668fd14p1b8e80jsnfa2ae02b25cf"
CHECK_INTERVAL = 180

# ===== ТРИГЕРИ =====
TRIGGER_GOALS = [4]
TRIGGER_MAX_MINUTE = 75

# ===== АКТИВНИЙ ЧАС (UTC) =====
ACTIVE_HOUR_START = 7
ACTIVE_HOUR_END = 22

# ===== БЛОКУЄМО =====
BLOCKED_KEYWORDS = [
    # Вікові категорії
    "u16", "u17", "u18", "u19", "u20", "u21", "u23",
    "youth", "junior", "juniors", "academy",

    # Жіночі
    "women", "woman", "ladies", "female", "girls",

    # Резерви
    "reserve", "reserves", "b team",

    # Регіональні / низькі дивізіони — загальні
    "regional", "regionalliga",
    "amateur", "amateurs",
    "division 3", "division 4", "division 5",
    "3. liga", "4. liga", "5. liga",
    "3rd division", "4th division", "5th division",
    "iii liga", "iv liga",
    "iii division", "iv division",
    "third division", "fourth division",

    # Іспанія низькі
    "segunda b", "tercera", "tercera rfef", "segunda rfef",

    # Італія низькі
    "serie c", "serie d", "primavera",

    # Німеччина низькі
    "oberliga", "verbandsliga",

    # Фінляндія низькі
    "kakkonen", "kolmonen", "ykkonen",

    # Нідерланди низькі
    "tweede divisie", "derde divisie",

    # Чехія низькі
    "chnl", "msfl", "moravskoslezska",

    # Польща низькі
    "iii liga", "iv liga",

    # Скандинавія низькі
    "nakotnes", "nakotnes liga",

    # Балкани низькі
    "druga liga",
    "2. snl", "3. snl",
    "prva liga - rs", "prva liga rs",

    # Росія та окупована територія — повний блок
    "russia", "russian", "rpl",
    "crimea", "krym",
    "fnl 2", "fnl2",

    # Африка — повний блок
    "africa", "morocco", "maroc", "nigeria", "ghana",
    "kenya", "tanzania", "ethiopia", "cameroon", "senegal",
    "ivory coast", "algeria", "tunisia", "egypt", "libya",
    "sudan", "uganda", "zambia", "zimbabwe", "mozambique",
    "angola", "congo", "mali", "burkina", "togo", "benin",
    "coupe du trone", "botola",

    # Південна Америка низькі / непотрібні
    "serie b", "serie c", "serie d",
    "liga auf uruguaya", "torneo intermedio", "torneo apertura",
    "torneo clausura", "primera nacional", "primera b",
    "brasileiro", "brasileirao",
    "uruguay", "ecuador", "peru", "bolivia",
    "venezuela", "paraguay", "chile", "colombia",
    "argentina", "brazil",

    # Мікро-країни
    "andorra", "gibraltar", "faroe", "san marino",
    "liechtenstein",
]


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
            print(f"❌ Telegram: {r.text[:100]}")
    except Exception as e:
        print(f"❌ Telegram exception: {e}")


HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "flashscore4.p.rapidapi.com",
    "Content-Type": "application/json"
}


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
            print("✅ API OK")
            return r.json()
        else:
            print(f"❌ API: {r.status_code} - {r.text[:200]}")
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
        ht_home = scores.get("home_1st_half")
        ht_away = scores.get("away_1st_half")
        if ht_home is not None and ht_away is not None:
            return int(ht_home), int(ht_away)
    except:
        pass
    return None, None


def get_stats(match_id):
    data = api_get(
        "https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/stats",
        {"match_id": match_id}
    )
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
    data = api_get(
        "https://flashscore4.p.rapidapi.com/api/flashscore/v2/teams/results",
        {"team_id": team_id, "page": "1"}
    )
    if not data:
        return None
    try:
        max_g = 0
        count = 0
        blocks = data if isinstance(data, list) else []
        for block in blocks:
            if count >= 5:
                break
            matches = block.get("matches", []) if isinstance(block, dict) else []
            for m in matches:
                if count >= 5:
                    break
                s = m.get("scores", {})
                h = int(s.get("home", 0) or 0)
                a = int(s.get("away", 0) or 0)
                if h + a > max_g:
                    max_g = h + a
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
        blocks = data if isinstance(data, list) else []
        for block in blocks:
            if count >= 5:
                break
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


def check_matches(data):
    if not data:
        return
    total = filtered = 0
    for block in data:
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
                print(f"⚠️ {e}")
    print(f"📊 {filtered} матчів (всього {total})")


# ===== СТАН =====
alerted = {}


def process_match(match, tournament_name):
    match_id = match.get("match_id", "unknown")
    home_team = match.get("home_team", {})
    away_team = match.get("away_team", {})
    home = home_team.get("name", "Господарі")
    away = away_team.get("name", "Гості")
    home_id = home_team.get("team_id")
    away_id = away_team.get("team_id")

    status = match.get("match_status", {})
    stage = status.get("stage", "")

    # Тільки активні тайми
    if stage not in ["1st Half", "2nd Half"]:
        return

    minute_raw = status.get("live_time", "0")
    try:
        minute = int(str(minute_raw).replace("+", "").split("+")[0])
    except:
        minute = 0

    # Реальна хвилина матчу
    actual_minute = minute if stage == "1st Half" else 45 + minute

    # ✅ ФІКС: пропускаємо хвилини 45 і 90 — кінець таймів / завершені матчі
    if actual_minute in [45, 90]:
        return

    # Пропускаємо якщо хвилина 0 або перевищує ліміт
    if actual_minute < 1 or actual_minute > TRIGGER_MAX_MINUTE:
        return

    scores = match.get("scores", {})
    home_score = int(scores.get("home", 0) or 0)
    away_score = int(scores.get("away", 0) or 0)
    total_goals = home_score + away_score

    for threshold in TRIGGER_GOALS:
        if total_goals < threshold:
            break

        if match_id not in alerted:
            alerted[match_id] = set()
        if threshold in alerted[match_id]:
            continue

        alerted[match_id].add(threshold)

        # HT рахунок
        if stage == "1st Half":
            ht_home, ht_away = home_score, away_score
            ht_known = True
        else:
            ht_home, ht_away = get_match_details(match_id)
            ht_known = ht_home is not None        icon = "⚽" if threshold == 4 else ("🔥" if threshold == 5 else "💥")

        msg = f"{icon} <b>АЛЕРТ! {threshold}+ ГОЛІВ</b>\n"
        msg += f"🏆 {tournament_name}\n"
        msg += f"<b>{home} {home_score} - {away_score} {away}</b>\n"
        msg += f"🕐 Хвилина: {actual_minute}'\n"

        if ht_known:
            msg += f"📊 1-й тайм: {ht_home}-{ht_away}\n"

        msg += f"✅ Тригер спрацював!"

        print(f"\n🚨 {threshold} ГОЛІВ: {tournament_name}: {home} {home_score}-{away_score} {away} | {actual_minute}'\n")
        send_telegram(msg)


def main():
    print("🤖 Football Alert Bot FINAL запущено!")
    print(f"⚙️ Тригери: {TRIGGER_GOALS} голів до {TRIGGER_MAX_MINUTE}'")
    print(f"⏱️ Активний: 10:00-01:00 Київ | Перевірка кожні {CHECK_INTERVAL//60} хв\n")

    send_telegram(
        f"🤖 <b>Football Alert Bot FINAL!</b>\n"
        f"Алерти: 4+ голів до {TRIGGER_MAX_MINUTE}'\n"
        f"Всі ліги крім жіночих, юнацьких, регіональних, Африки, Пд.Америки\n"
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
