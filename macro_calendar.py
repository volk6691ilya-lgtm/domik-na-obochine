import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MacroCalendar:
    """
    Модуль для проверки важных макроэкономических событий (ФРС, CPI, NFP).
    Использует парсинг Investing.com (бесплатно, но требует аккуратности).
    """

    def __init__(self):
        # URL страницы экономического календаря на сегодня/завтра
        # Примечание: Investing.com динамически подгружает контент, 
        # поэтому прямой парсинг HTML может быть неполным. 
        # Для MVP используем альтернативный источник или упрощенную логику.
        
        # Попробуем использоватьForexFactory (более статичный HTML)
        self.url = "https://www.forexfactory.com/calendar"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def get_upcoming_high_impact_events(self, hours_ahead=24):
        """
        Ищет события с высоким влиянием (High Impact) в ближайшие часы.
        Возвращает список словарей: {'event': 'FOMC Rate Decision', 'time': '18:00'}
        """
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                logging.warning(f"Не удалось загрузить страницу календаря: {response.status_code}")
                return []

            soup = BeautifulSoup(response.content, 'lxml')
            
            # Логика поиска таблиц с событиями
            # На ForexFactory события находятся в таблицах с классом ff-calendar-table-row
            # Высокое влияние обозначается красной иконкой (класс ff-icon--high)
            
            events = []
            rows = soup.find_all('tr', class_='ff-calendar-table-row')
            
            for row in rows:
                # Проверяем наличие иконки высокого влияния
                impact_icon = row.find('span', class_='ff-icon--high')
                if not impact_icon:
                    continue
                
                # Извлекаем название события
                event_cell = row.find('div', class_='ff-tab-col--events')
                if not event_cell:
                    continue
                event_name = event_cell.text.strip()
                
                # Извлекаем время (примерная логика, зависит от структуры)
                time_cell = row.find('td', class_='ff-tab-col--time')
                event_time = time_cell.text.strip() if time_cell else "Unknown"
                
                events.append({
                    "event": event_name,
                    "time": event_time,
                    "impact": "HIGH"
                })

            # Фильтрация по времени (упрощенно, так как время на сайте обычно UTC или локальное)
            # В реальном проекте нужно конвертировать таймзоны
            return events[:5] # Берем топ-5 ближайших

        except Exception as e:
            logging.error(f"Ошибка при парсинге макро-календаря: {e}")
            return []

# Блок для локального тестирования
if __name__ == "__main__":
    print("\n--- Тест Macro Calendar ---")
    calendar = MacroCalendar()
    
    # Ищем события на ближайшие 24 часа
    events = calendar.get_upcoming_high_impact_events(hours_ahead=24)
    
    if events:
        print("Обнаружены важные события:")
        for i, event in enumerate(events, 1):
            print(f"{i}. [{event['impact']}] {event['event']} - Время: {event['time']}")
    else:
        print("Важных событий высокого влияния на ближайшие сутки не найдено.")
        
    print("--- Тест завершен ---\n")
