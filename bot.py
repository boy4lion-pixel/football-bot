import requests
import time
from datetime import datetime

# ===== НАЛАШТУВАННЯ =====
TELEGRAM_TOKEN = "8440346164:AAFZzfshhUsgN6MWbrfXQE6OXGFTKhJ6eEk"
CHAT_ID = "439583139"
RAPIDAPI_KEY = "b4bd4a4ab1msh31fe8f92668fd14p1b8e80jsnfa2ae02b25cf"
CHECK_INTERVAL = 180  # раз в 3 хвилини

# ===== ТРИГЕРИ =====
TRIGGER_HT_GOALS = 2
TRIGGER_TOTAL_GOALS = 4
TRIGGER_MAX_MINUTE = 75

# ===== АКТИВНИЙ ЧАС (UTC) =====
ACTIVE_HOUR_START = 7
ACTIVE_HOUR_END = 20

# ===== БІЛИЙ СПИСОК ЛІГИ =====
ALLOWED_LEAGUES = [
    "austria: bundesliga", "austria: 2. liga",
    "azerbaijan: premier", "azerbaijan: 1. liga",
    "albania: superliga",
    "algeria: ligue", "algeria: division",
    "england: premier", "england: championship", "england: fa cup",
    "argentina: primera", "argentina: nacional b", "argentina: federal",
    "belgium: jupiler", "belgium: challenger",
    "belarus: vysheyshaya", "belarus: pershaya", "belarus: first",
    "bulgaria: first", "bulgaria: second",
    "bosnia: premijer", "bosnia: liga",
    "brazil: serie a", "brazil: serie b", "brazil: serie c", "brazil: serie d",
    "armenia: premier",
    "georgia: erovnuli",
    "denmark: superliga", "denmark: 1st", "denmark: 2nd",
    "estonia: meistriliiga", "estonia: esiliiga",
    "egypt: premier",
    "israel: premier", "israel: leumit",
    "iraq: stars league",
    "ireland: premier", "ireland: first",
    "spain: laliga", "spain: segunda",
    "italy: serie a", "italy: serie b",
    "jordan: premier",
    "qatar: qsl", "qatar: stars",
    "kenya: premier", "kenya: super",
    "china: super", "china: league one", "china: league two",
    "cyprus: first", "cyprus: division",
    "latvia: virsliga", "latvia: nakotnes",
    "lithuania: a lyga", "lithuania: 1 lyga",
    "morocco: botola",
    "moldova: super",
    "nigeria: premier",
    "netherlands: eredivisie", "netherlands: eerste",
    "germany: bundesliga", "germany: 2. bundesliga", "germany: 3. liga",
    "norway: eliteserien", "norway: obos",
    "uae: arabian", "uae: division",
    "oman: professional",
    "paraguay: primera",
    "peru: liga 1", "peru: liga 2",
    "south africa: premier",
    "south korea: k league", "korea: k league",
    "northern ireland: premier",
    "poland: ekstraklasa", "poland: i liga", "poland: ii liga",
    "portugal: primeira", "portugal: segunda",
    "romania: superliga", "romania: liga 2",
    "saudi arabia: professional", "saudi arabia: division",
    "serbia: super",
    "slovakia: nike liga", "slovakia: super",
    "turkey: super lig", "turkey: 1. lig",
    "hungary: nb i",
    "wales: cymru",
    "uzbekistan: super",
    "ukraine: premier", "ukraine: persha", "ukraine: druha",
    "uruguay: primera", "uruguay: segunda",
    "champions league", "europa league", "conference league", "euro ", "world cup",
    "faroe islands: premier", "faroe islands: 1. deild",
    "finland: veikkausliiga",
    "france: ligue 1", "france: ligue 2", "france: national",
    "croatia: hnl", "croatia: prva",
    "czech: first", "czech: fortuna liga", "czech: druha",
    "chile: primera", "chile: segunda",
    "montenegro: first",
    "switzerland: super", "switzerland: challenge",
    "sweden: allsvenskan", "sweden: superettan",
    "scotland: premier", "scotland: championship",
    "japan: j1", "japan: j2", "japan: j3",
    "usa: mls",
]

# ===== СТАН =====
alerted_trigger = set()

HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "flashscore4.p.rapidapi.com",
    "Content-Type": "application/json"
}


def is_allowed_league(name):
    n = name.lower()
    return any(l in n for l in ALLOWED_LEAGUES)


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
    url = "https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/live"
    try:
        r = requests.get(url, headers=HEADERS, params={"sport_id": "1", "timezone": "Europe/Berlin"}, timeout=15)
        if r.status_code == 200:
            print("✅ API OK")
            return r.json()
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
    print(f"📊 {filtered} матчів з дозволених ліг (всього {total})")


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
    if stage != "2nd Half":
        return

    minute_raw = status.get("live_time", "0")
    try:
        minute = int(str(minute_raw).replace("+", "").split("+")[0])
    except:
        minute = 0

    if minute > TRIGGER_MAX_MINUTE:
        return

    scores = match.get("scores", {})
    home_score = int(scores.get("home", 0) or 0)
    away_score = int(scores.get("away", 0) or 0)
    total_goals = home_score + away_score

    if total_goals < TRIGGER_TOTAL_GOALS:
        return

    # Перевіряємо HT
    ht_home, ht_away = get_ht_score(match_id)
    if ht_home is None:
        print(f"  ⚠️ Немає HT для {home} vs {away}")
        return

    ht_goals = ht_home + ht_away
    if ht_goals < TRIGGER_HT_GOALS:
        return

    alert_key = f"{match_id}_{total_goals}"
    if alert_key in alerted_trigger:
        return

    alerted_trigger.add(alert_key)
    print(f"\n🚨 ТРИГЕР: {tournament_name}: {home} {home_score}-{away_score} {away} | {minute}' | HT:{ht_home}-{ht_away}\n")

    # Збираємо всю статистику
    xg_h, xg_a, sh_h, sh_a, pos_h, pos_a = get_stats(match_id)
    home_max = get_team_max_goals(home_id) if home_id else None
    away_max = get_team_max_goals(away_id) if away_id else None
    h2h_max, h2h_score = get_h2h_max(match_id)

    msg = (
        f"⚽ <b>АЛЕРТ! ТРИГЕР!</b>\n"
        f"🏆 {tournament_name}\n"
        f"<b>{home} {home_score} - {away_score} {away}</b>\n"
        f"🕐 Хвилина: {minute}'\n"
        f"📊 1-й тайм: {ht_home}-{ht_away} ({ht_goals} голів)\n"
        f"📈 Всього голів: {total_goals}\n"
    )
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

    send_telegram(msg)


def main():
    print("🤖 Football Alert Bot v9 запущено!")
    print(f"⚙️ Тригер: {TRIGGER_HT_GOALS}+ у 1-му таймі + {TRIGGER_TOTAL_GOALS}+ загальних до {TRIGGER_MAX_MINUTE}'")
    print(f"⏱️ Перевірка кожні {CHECK_INTERVAL//60} хв | Активний: 10:00-23:00 Київ\n")

    send_telegram(
        f"🤖 <b>Football Alert Bot v9!</b>\n"
        f"Тригер: {TRIGGER_HT_GOALS}+ голів у 1-му таймі\n"
        f"+ {TRIGGER_TOTAL_GOALS}+ загальних до {TRIGGER_MAX_MINUTE}'\n"
        f"Перевірка кожні 3 хв ⏱️\n"
        f"Активний: 10:00-23:00 (Київ)"
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
