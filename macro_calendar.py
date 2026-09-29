import json
import os
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MacroCalendar:
    """
    Модуль для проверки важных макроэкономических событий (ФРС, CPI, NFP).
    Использует локальный JSON-файл с расписанием (100% надежность).
    """

    def __init__(self):
        self.schedule_file = os.path.join(os.path.dirname(__file__), "macro_events_schedule.json")
        self.schedule = self._load_schedule()

    def _load_schedule(self):
        try:
            with open(self.schedule_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Не удалось загрузить расписание: {e}")
            return {}

    def get_upcoming_events(self, days_ahead=7):
        """
        Ищет важные события в ближайшие N дней.
        """
        today = datetime.now().date()
        end_date = today + timedelta(days=days_ahead)
        upcoming_events = []

        for year_str, year_data in self.schedule.items():
            year = int(year_str)
            if year < today.year or year > end_date.year:
                continue

            for event_type, events in year_data.items():
                for event in events:
                    event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
                    if today <= event_date <= end_date:
                        upcoming_events.append({
                            "date": event["date"],
                            "time": event["time"],
                            "type": event_type,
                            "description": event["description"],
                            "timezone": event.get("timezone", "MSK"),
                            "days_until": (event_date - today).days
                        })

        upcoming_events.sort(key=lambda x: x["date"])
        return upcoming_events

    def get_warning_message(self):
        """
        Генерирует предупреждение для поста, если в ближайшие 24 часа есть важное событие.
        """
        events = self.get_upcoming_events(days_ahead=1)
        if not events:
            return None

        warning = "⚠️ **ВНИМАНИЕ: Макро-события в ближайшие 24 часа!**\n\n"
        for event in events:
            warning += f"• **{event['type']}** ({event['description']}) — {event['date']} в {event['time']} МСК\n"
        
        warning += "\n📉 Возможна высокая волатильность. Технические сигналы могут быть искажены."
        return warning

    def get_weekly_macro_outlook(self):
        """
        Генерирует обзор макро-событий на неделю для инвестиционного поста.
        """
        events = self.get_upcoming_events(days_ahead=7)
        if not events:
            return " На этой неделе важных макро-событий не ожидается. Рынок может двигаться в режиме флэта."

        outlook = "📅 **МАКРО-КАЛЕНДАРЬ НА НЕДЕЛЮ:**\n\n"
        for event in events:
            emoji = "🏦" if event["type"] == "FOMC" else ("📈" if event["type"] == "CPI" else "💼")
            outlook += f"{emoji} **{event['date']}** в {event['time']} МСК — {event['description']}\n"
        
        outlook += "\n⚠️ Будьте готовы к высокой волатильности в эти дни."
        return outlook

# Блок для локального тестирования
if __name__ == "__main__":
    print("\n--- Тест Macro Calendar (Актуальные даты 2026-2027) ---")
    calendar = MacroCalendar()
    
    # Ищем события на ближайшие 90 дней
    events = calendar.get_upcoming_events(days_ahead=90)
    
    if events:
        print(f"Найдено {len(events)} важных событий в ближайшие 90 дней:\n")
        for i, event in enumerate(events, 1):
            print(f"{i}. [{event['type']}] {event['description']}")
            print(f"   Дата: {event['date']} в {event['time']} {event['timezone']} (через {event['days_until']} дн.)\n")
    else:
        print("Важных событий в ближайшие 90 дней не найдено.")
    
    # Тестируем генерацию предупреждения
    print("\n--- Тест предупреждения для поста (24 часа) ---")
    warning = calendar.get_warning_message()
    if warning:
        print(warning)
    else:
        print("Предупреждений нет (в ближайшие 24 часа событий нет).")
    
    # Тестируем недельный обзор
    print("\n--- Тест недельного макро-обзора ---")
    outlook = calendar.get_weekly_macro_outlook()
    print(outlook)
        
    print("\n--- Тест завершен ---\n")
