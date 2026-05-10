import requests
import time
from datetime import datetime

# ===== НАЛАШТУВАННЯ =====
TELEGRAM_TOKEN = "8440346164:AAFZzfshhUsgN6MWbrfXQE6OXGFTKhJ6eEk"
CHAT_ID = "439583139"
RAPIDAPI_KEY = "b4bd4a4ab1msh31fe8f92668fd14p1b8e80jsnfa2ae02b25cf"
CHECK_INTERVAL = 120

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
alerted_ht = set()
alerted_trigger = set()

HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "flashscore4.p.rapidapi.com",
    "Content-Type": "application/json"
}


def is_allowed_league(tournament_name):
    name_lower = tournament_name.lower()
    return any(league in name_lower for league in ALLOWED_LEAGUES)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=data, timeout=10)
        if r.status_code == 200:
            print("✅ Telegram надіслано")
        else:
            print(f"❌ Telegram помилка: {r.text}")
    except Exception as e:
        print(f"❌ Telegram exception: {e}")


def get_live_matches():
    url = "https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/live"
    params = {"sport_id": "1", "timezone": "Europe/Berlin"}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if r.status_code == 200:
            print("✅ API відповів OK")
            return r.json()
        else:
            print(f"❌ API помилка: {r.status_code} - {r.text[:300]}")
            return None
    except Exception as e:
        print(f"❌ API exception: {e}")
        return None


def get_match_details(match_id):
    url = "https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/details"
    try:
        r = requests.get(url, headers=HEADERS, params={"match_id": match_id}, timeout=10)
        return r.json() if r.status_code == 200 else None
    except:
        return None


def get_match_stats(match_id):
    url = "https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/stats"
    try:
        r = requests.get(url, headers=HEADERS, params={"match_id": match_id}, timeout=10)
        return r.json() if r.status_code == 200 else None
    except:
        return None


def get_h2h(match_id):
    url = "https://flashscore4.p.rapidapi.com/api/flashscore/v2/matches/h2h"
    try:
        r = requests.get(url, headers=HEADERS, params={"match_id": match_id}, timeout=10)
        return r.json() if r.status_code == 200 else None
    except:
        return None


def get_team_results(team_id):
    url = "https://flashscore4.p.rapidapi.com/api/flashscore/v2/teams/results"
    try:
        r = requests.get(url, headers=HEADERS, params={"team_id": team_id, "page": "1"}, timeout=10)
        return r.json() if r.status_code == 200 else None
    except:
        return None


def parse_ht_score(details):
    if not details:
        return None, None
    try:
        if isinstance(details, dict):
            scores = details.get("scores", {})
            ht_home = scores.get("ht_home", scores.get("halftime_home", None))
            ht_away = scores.get("ht_away", scores.get("halftime_away", None))
            if ht_home is not None:
                return int(ht_home), int(ht_away)
    except:
        pass
    return None, None


def parse_stats(stats_data):
    xg_home = xg_away = shots_home = shots_away = poss_home = poss_away = None
    if not stats_data:
        return xg_home, xg_away, shots_home, shots_away, poss_home, poss_away
    items = []
    if isinstance(stats_data, list):
        items = stats_data
    elif isinstance(stats_data, dict):
        items = stats_data.get("stats", stats_data.get("data", []))
    for item in items:
        name = str(item.get("name", item.get("stat_name", ""))).lower()
        home_val = item.get("home", item.get("home_value", ""))
        away_val = item.get("away", item.get("away_value", ""))
        if "expected goals" in name or name == "xg":
            xg_home, xg_away = home_val, away_val
        elif "shot" in name and "target" not in name and shots_home is None:
            shots_home, shots_away = home_val, away_val
        elif "possession" in name:
            poss_home, poss_away = home_val, away_val
    return xg_home, xg_away, shots_home, shots_away, poss_home, poss_away


def get_max_goals_from_results(team_results, last_n=5):
    """Максимальна кількість голів в одному матчі за останні N ігор"""
    try:
        matches = []
        if isinstance(team_results, list):
            matches = team_results
        elif isinstance(team_results, dict):
            matches = team_results.get("matches", team_results.get("results", team_results.get("data", [])))

        max_goals = 0
        count = 0
        for m in matches:
            if count >= last_n:
                break
            scores = m.get("scores", {})
            h = int(scores.get("home", 0) or 0)
            a = int(scores.get("away", 0) or 0)
            total = h + a
            if total > max_goals:
                max_goals = total
            count += 1
        return max_goals if count > 0 else None
    except:
        return None


def get_h2h_max_goals(h2h_data, last_n=5):
    """Максимальна кількість голів в матчі H2H за останні N ігор"""
    try:
        matches = []
        if isinstance(h2h_data, list):
            matches = h2h_data
        elif isinstance(h2h_data, dict):
            matches = h2h_data.get("matches", h2h_data.get("h2h", h2h_data.get("data", [])))

        max_goals = 0
        max_score = ""
        count = 0
        for m in matches:
            if count >= last_n:
                break
            scores = m.get("scores", {})
            h = int(scores.get("home", 0) or 0)
            a = int(scores.get("away", 0) or 0)
            total = h + a
            if total > max_goals:
                max_goals = total
                max_score = f"{h}-{a}"
            count += 1
        return max_goals, max_score if count > 0 else (None, None)
    except:
        return None, None


def check_matches(data):
    if not data:
        return
    total_matches = 0
    filtered_matches = 0
    for tournament_block in data:
        tournament_name = tournament_block.get("name", "")
        matches = tournament_block.get("matches", [])
        total_matches += len(matches)
        if not is_allowed_league(tournament_name):
            continue
        filtered_matches += len(matches)
        for match in matches:
            try:
                process_match(match, tournament_name)
            except Exception as e:
                print(f"⚠️ Помилка: {e}")
    print(f"📊 Перевірено {filtered_matches} матчів з дозволених ліг (всього {total_matches})")


def process_match(match, tournament_name):
    match_id = match.get("match_id", "unknown")
    home_team = match.get("home_team", {})
    away_team = match.get("away_team", {})
    home = home_team.get("name", "Господарі")
    away = away_team.get("name", "Гості")
    home_id = home_team.get("id", None)
    away_id = away_team.get("id", None)

    status = match.get("match_status", {})
    stage = status.get("stage", "")
    minute_raw = status.get("live_time", "0")

    try:
        if minute_raw and minute_raw not in ["Half Time", "Full Time", None]:
            minute = int(str(minute_raw).replace("+", "").split("+")[0])
        else:
            minute = 0
    except:
        minute = 0

    scores = match.get("scores", {})
    home_score = int(scores.get("home", 0) or 0)
    away_score = int(scores.get("away", 0) or 0)
    total_goals = home_score + away_score

    # ===== АЛЕРТ 1: 1-й тайм, 2+ голів =====
    if stage == "1st Half" and total_goals >= TRIGGER_HT_GOALS:
        ht_key = f"{match_id}_ht_{total_goals}"
        if ht_key not in alerted_ht:
            alerted_ht.add(ht_key)
            print(f"  👀 1-й тайм: {tournament_name}: {home} {home_score}-{away_score} {away} | {minute}'")

            stats_data = get_match_stats(match_id)
            xg_h, xg_a, sh_h, sh_a, pos_h, pos_a = parse_stats(stats_data)

            # Форма команд
            home_max = away_max = None
            if home_id:
                home_results = get_team_results(home_id)
                home_max = get_max_goals_from_results(home_results)
            if away_id:
                away_results = get_team_results(away_id)
                away_max = get_max_goals_from_results(away_results)

            # H2H
            h2h_data = get_h2h(match_id)
            h2h_max, h2h_score = get_h2h_max_goals(h2h_data)

            msg = (
                f"👀 <b>СТЕЖИ ЗА МАТЧЕМ!</b>\n"
                f"🏆 {tournament_name}\n"
                f"<b>{home} {home_score} - {away_score} {away}</b>\n"
                f"🕐 Хвилина: {minute}'\n"
                f"⚡ Вже {total_goals} голів у 1-му таймі!\n"
            )
            if xg_h is not None or sh_h is not None:
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

            send_telegram(msg)
        return

    # ===== АЛЕРТ 2: 2-й тайм, 4+ загальних до 75' =====
    if stage != "2nd Half" or minute > TRIGGER_MAX_MINUTE:
        return
    if total_goals < TRIGGER_TOTAL_GOALS:
        return

    print(f"  🔍 2-й тайм: {tournament_name}: {home} {home_score}-{away_score} {away} | {minute}'")

    details = get_match_details(match_id)
    ht_home, ht_away = parse_ht_score(details)

    if ht_home is None:
        print(f"  ⚠️ Не вдалось отримати HT рахунок")
        return

    ht_goals = ht_home + ht_away
    if ht_goals < TRIGGER_HT_GOALS:
        return

    alert_key = f"{match_id}_{total_goals}"
    if alert_key not in alerted_trigger:
        alerted_trigger.add(alert_key)

        stats_data = get_match_stats(match_id)
        xg_h, xg_a, sh_h, sh_a, pos_h, pos_a = parse_stats(stats_data)

        # Форма команд
        home_max = away_max = None
        if home_id:
            home_results = get_team_results(home_id)
            home_max = get_max_goals_from_results(home_results)
        if away_id:
            away_results = get_team_results(away_id)
            away_max = get_max_goals_from_results(away_results)

        # H2H
        h2h_data = get_h2h(match_id)
        h2h_max, h2h_score = get_h2h_max_goals(h2h_data)

        msg = (
            f"⚽ <b>АЛЕРТ! ТРИГЕР!</b>\n"
            f"🏆 {tournament_name}\n"
            f"<b>{home} {home_score} - {away_score} {away}</b>\n"
            f"🕐 Хвилина: {minute}'\n"
            f"📊 1-й тайм: {ht_home}-{ht_away} ({ht_goals} голів)\n"
            f"📈 Всього голів: {total_goals}\n"
            f"{'━'*10}\n"
        )
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

        print(f"\n🚨 АЛЕРТ: {home} {home_score}-{away_score} {away} | {minute}' | HT: {ht_home}-{ht_away}\n")
        send_telegram(msg)


def main():
    print("🤖 Football Alert Bot v8 запущено!")
    print(f"⚙️ Тригери: {TRIGGER_HT_GOALS}+ голів у 1-му таймі, {TRIGGER_TOTAL_GOALS}+ загальних до {TRIGGER_MAX_MINUTE}'")

    send_telegram(
        f"🤖 <b>Football Alert Bot v8!</b>\n"
        f"Алерти:\n"
        f"- 👀 {TRIGGER_HT_GOALS}+ голів у 1-му таймі — стежи!\n"
        f"- ⚽ {TRIGGER_TOTAL_GOALS}+ загальних до {TRIGGER_MAX_MINUTE}' — тригер!\n"
        f"+ Форма та H2H 📊\n"
        f"Активний: 10:00 - 23:00 (Київ)"
    )

    while True:
        now = datetime.now()
        hour = now.hour
        time_str = now.strftime("%H:%M:%S")

        if ACTIVE_HOUR_START <= hour < ACTIVE_HOUR_END:
            print(f"\n⏰ [{time_str}] Перевіряю матчі...")
            data = get_live_matches()
            check_matches(data)
            print(f"💤 Чекаю {CHECK_INTERVAL} секунд...")
            time.sleep(CHECK_INTERVAL)
        else:
            print(f"😴 [{time_str}] Нічний режим, сплю до 10:00 Київ...")
            time.sleep(600)


if __name__ == "__main__":
    main()
