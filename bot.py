import requests
import time
from datetime import datetime

# ===== НАЛАШТУВАННЯ =====
TELEGRAM_TOKEN = "8440346164:AAFZzfshhUsgN6MWbrfXQE6OXGFTKhJ6eEk"
CHAT_ID = "439583139"
RAPIDAPI_KEY = "b4bd4a4ab1msh31fe8f92668fd14p1b8e80jsnfa2ae02b25cf"
CHECK_INTERVAL = 120  # перевірка кожні 2 хвилини

# ===== ТРИГЕРИ =====
TRIGGER_HT_GOALS = 2       # мінімум голів у 1-му таймі
TRIGGER_TOTAL_GOALS = 5    # мінімум загальних голів
TRIGGER_MAX_MINUTE = 80    # до якої хвилини спрацьовує тригер

# ===== АКТИВНИЙ ЧАС =====
ACTIVE_HOUR_START = 7
ACTIVE_HOUR_END = 20

# ===== СТАН =====
alerted_matches = set()


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
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "flashscore4.p.rapidapi.com",
        "Content-Type": "application/json"
    }
    params = {"sport_id": "1", "timezone": "Europe/Kiev"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code == 200:
            print("✅ API відповів OK")
            return r.json()
        else:
            print(f"❌ API помилка: {r.status_code} - {r.text[:300]}")
            return None
    except Exception as e:
        print(f"❌ API exception: {e}")
        return None


def check_matches(data):
    if not data:
        return

    # Структура: список турнірів, кожен має matches: []
    total_matches = 0
    for tournament_block in data:
        tournament_name = tournament_block.get("name", "")
        matches = tournament_block.get("matches", [])
        total_matches += len(matches)

        for match in matches:
            try:
                process_match(match, tournament_name)
            except Exception as e:
                print(f"⚠️ Помилка: {e}")

    print(f"📊 Перевірено {total_matches} матчів у {len(data)} турнірах")


def process_match(match, tournament_name):
    match_id = match.get("match_id", "unknown")

    # Команди
    home = match.get("home_name", "Господарі")
    away = match.get("away_name", "Гості")

    # Статус матчу
    status = match.get("match_status", {})
    stage = status.get("stage", "")
    minute = status.get("current_minutes", 0)
    try:
        minute = int(str(minute).replace("'", "").replace("+", "").split("+")[0])
    except:
        minute = 0

    # Тільки 2-й тайм і до TRIGGER_MAX_MINUTE хвилини
    if stage != "2nd Half" or minute > TRIGGER_MAX_MINUTE:
        return

    # Рахунок
    scores = match.get("scores", {})
    home_score = int(scores.get("home_score", 0) or 0)
    away_score = int(scores.get("away_score", 0) or 0)
    ht_home = int(scores.get("ht_home_score", 0) or 0)
    ht_away = int(scores.get("ht_away_score", 0) or 0)

    total_goals = home_score + away_score
    ht_goals = ht_home + ht_away

    print(f"  🔍 {tournament_name}: {home} {home_score}-{away_score} {away} | {minute}' | HT: {ht_home}-{ht_away}")

    # Перевіряємо тригери
    if ht_goals >= TRIGGER_HT_GOALS and total_goals >= TRIGGER_TOTAL_GOALS:
        alert_key = f"{match_id}_{total_goals}"
        if alert_key not in alerted_matches:
            alerted_matches.add(alert_key)
            message = (
                f"⚽ <b>АЛЕРТ!</b>\n"
                f"🏆 {tournament_name}\n"
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
    print(f"⏱️ Активний час: 10:00 - 23:00 (Київ)\n")

    send_telegram(
        f"🤖 <b>Football Alert Bot запущено!</b>\n"
        f"Тригери:\n"
        f"- {TRIGGER_HT_GOALS}+ голів у 1-му таймі\n"
        f"- {TRIGGER_TOTAL_GOALS}+ загальних голів до {TRIGGER_MAX_MINUTE}'\n"
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
