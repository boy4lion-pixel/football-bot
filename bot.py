import requests
import time
import json
import os
from datetime import datetime

# ===== НАЛАШТУВАННЯ =====
TELEGRAM_TOKEN = "8440346164:AAFZzfshhUsgN6MWbrfXQE6OXGFTKhJ6eEk"
CHAT_ID = "439583139"
RAPIDAPI_KEY = "b4bd4a4ab1msh31fe8f92668fd14p1b8e80jsnfa2ae02b25cf"
CHECK_INTERVAL = 120  # перевірка кожні 2 хвилини

# ===== ЛІГИ ДЛЯ МОНІТОРИНГУ =====
# FlashScore tournament IDs
LEAGUES = {
    # Топ-5
    "Premier League": "p7oD2Wgf",
    "La Liga": "U1oAP5ib",
    "Serie A": "LrEMWu4s",
    "Bundesliga": "tdAuM98B",
    "Ligue 1": "GJb0MYQB",
    # Єврокубки
    "Champions League": "jNxIrNBo",
    "Europa League": "cDi5YOXE",
    "Conference League": "IT4JQKEN",
    # Інші топ-ліги
    "Eredivisie": "McRHlDl3",
    "Primeira Liga": "kwkOqVMp",
    "Super Lig": "oRFB0HFQ",
    "Belgian Pro League": "jzLK2NpQ",
    "Scottish Premiership": "FvuSPCji",
    "Greek Super League": "W7bLLIWf",
    "UPL": "DFbBiGxA",
}

# ===== ТРИГЕРИ =====
TRIGGER_HT_GOALS = 2       # мінімум голів у 1-му таймі
TRIGGER_TOTAL_GOALS = 5    # мінімум загальних голів
TRIGGER_MAX_MINUTE = 80    # до якої хвилини спрацьовує тригер

# ===== СТАН =====
alerted_matches = set()  # щоб не дублювати сповіщення


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, data=data, timeout=10)
        if r.status_code == 200:
            print(f"✅ Telegram надіслано")
        else:
            print(f"❌ Telegram помилка: {r.text}")
    except Exception as e:
        print(f"❌ Telegram exception: {e}")


def get_live_matches():
    url = "https://flashscore4.p.rapidapi.com/api/flashscore/v2/sport/football/matches/live"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "flashscore4.p.rapidapi.com",
        "Content-Type": "application/json"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"❌ API помилка: {r.status_code} - {r.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ API exception: {e}")
        return None


def parse_score(score_str):
    """Парсить рахунок типу '3 - 2' або '3:2'"""
    try:
        score_str = score_str.replace(" ", "").replace("-", ":")
        parts = score_str.split(":")
        return int(parts[0]), int(parts[1])
    except:
        return 0, 0


def check_matches(data):
    if not data:
        return

    matches = []

    # Пробуємо різні структури відповіді FlashScore API
    if isinstance(data, dict):
        matches = data.get("data", data.get("matches", data.get("events", [])))
    elif isinstance(data, list):
        matches = data

    if not matches:
        print(f"ℹ️ Немає live матчів або невідома структура даних")
        print(f"Ключі відповіді: {list(data.keys()) if isinstance(data, dict) else 'list'}")
        return

    print(f"📊 Знайдено {len(matches)} live матчів")

    for match in matches:
        try:
            process_match(match)
        except Exception as e:
            print(f"⚠️ Помилка обробки матчу: {e}")


def process_match(match):
    # FlashScore може повертати різні структури — пробуємо обидва варіанти
    match_id = match.get("id") or match.get("match_id") or match.get("eventId", "unknown")

    # Назва турніру
    tournament = (
        match.get("tournament", {}).get("name") or
        match.get("league", {}).get("name") or
        match.get("tournamentName") or
        match.get("competition", {}).get("name") or
        ""
    )

    # Перевіряємо чи ліга в нашому списку
    league_match = any(
        league_name.lower() in tournament.lower()
        for league_name in LEAGUES.keys()
    )
    if not league_match:
        return

    # Команди
    home = (
        match.get("homeTeam", {}).get("name") or
        match.get("home_team") or
        match.get("homeName") or
        "Господарі"
    )
    away = (
        match.get("awayTeam", {}).get("name") or
        match.get("away_team") or
        match.get("awayName") or
        "Гості"
    )

    # Хвилина
    minute = (
        match.get("minute") or
        match.get("match_minute") or
        match.get("time", {}).get("current") or
        0
    )
    try:
        minute = int(str(minute).replace("'", "").replace("+", ""))
    except:
        minute = 0

    # Рахунок
    home_score = (
        match.get("homeScore", {}).get("current") or
        match.get("score", {}).get("home") or
        match.get("homeGoals") or
        0
    )
    away_score = (
        match.get("awayScore", {}).get("current") or
        match.get("score", {}).get("away") or
        match.get("awayGoals") or
        0
    )
    try:
        home_score = int(home_score)
        away_score = int(away_score)
    except:
        home_score = away_score = 0

    # Рахунок першого тайму
    ht_home = (
        match.get("homeScore", {}).get("halfTime") or
        match.get("score", {}).get("ht_home") or
        match.get("htScore", "0-0").split("-")[0] if isinstance(match.get("htScore"), str) else 0
    )
    ht_away = (
        match.get("awayScore", {}).get("halfTime") or
        match.get("score", {}).get("ht_away") or
        match.get("htScore", "0-0").split("-")[1] if isinstance(match.get("htScore"), str) else 0
    )
    try:
        ht_home = int(ht_home)
        ht_away = int(ht_away)
    except:
        ht_home = ht_away = 0

    total_goals = home_score + away_score
    ht_goals = ht_home + ht_away

    # Логуємо матч
    print(f"  🔍 {tournament}: {home} {home_score}-{away_score} {away} | {minute}' | HT: {ht_home}-{ht_away}")

    # Тільки другий тайм і до 80 хвилини
    if minute < 46 or minute > TRIGGER_MAX_MINUTE:
        return

    # Перевіряємо тригери
    trigger_ht = ht_goals >= TRIGGER_HT_GOALS
    trigger_total = total_goals >= TRIGGER_TOTAL_GOALS

    if trigger_ht and trigger_total:
        alert_key = f"{match_id}_{total_goals}"
        if alert_key not in alerted_matches:
            alerted_matches.add(alert_key)
            send_alert(tournament, home, away, home_score, away_score, ht_home, ht_away, minute, total_goals, ht_goals)


def send_alert(tournament, home, away, home_score, away_score, ht_home, ht_away, minute, total_goals, ht_goals):
    message = (
        f"⚽ <b>АЛЕРТ!</b>\n"
        f"🏆 {tournament}\n"
        f"<b>{home} {home_score} - {away_score} {away}</b>\n"
        f"🕐 Хвилина: {minute}'\n"
        f"📊 1-й тайм: {ht_home}-{ht_away} ({ht_goals} голів)\n"
        f"📈 Всього голів: {total_goals}\n"
        f"✅ Тригер спрацював!"
    )
    print(f"\n🚨 АЛЕРТ: {home} {home_score}-{away_score} {away} | {minute}' | Голи: {total_goals}\n")
    send_telegram(message)


def main():
    print("🤖 Football Alert Bot запущено!")
    print(f"⚙️ Тригери: {TRIGGER_HT_GOALS}+ голів у 1-му таймі, {TRIGGER_TOTAL_GOALS}+ загальних до {TRIGGER_MAX_MINUTE}'")
    print(f"⏱️ Перевірка кожні {CHECK_INTERVAL} секунд\n")

    send_telegram(
        f"🤖 <b>Football Alert Bot запущено!</b>\n"
        f"Тригери:\n"
        f"• {TRIGGER_HT_GOALS}+ голів у 1-му таймі\n"
        f"• {TRIGGER_TOTAL_GOALS}+ загальних голів до {TRIGGER_MAX_MINUTE}'\n"
        f"Перевірка кожні {CHECK_INTERVAL//60} хвилини"
    )

    while True:
        now = datetime.now().strftime("%H:%M:%S")
        print(f"\n⏰ [{now}] Перевіряю матчі...")

        data = get_live_matches()
        check_matches(data)

        print(f"💤 Чекаю {CHECK_INTERVAL} секунд...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
