import requests
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MarketHealthChecker:
    """
    Модуль для определения глобального состояния рынка (Светофор)
    на основе корреляции Капитализации и Объемов (из PDF "Совмещение стратегий").
    """

    def __init__(self):
        # Ключ берется из GitHub Secrets. Для локального теста можно прописать вручную, но не коммитьте его!
        self.api_key = os.getenv("CMC_API_KEY") 
        self.url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        self.headers = {
            "Accepts": "application/json",
            "X-CMC_PRO_API_KEY": self.api_key
        }

    def get_market_regime(self):
        """
        Анализирует изменение общей капитализации и объемов за 24 часа.
        Возвращает режим рынка и проценты изменения.
        """
        if not self.api_key:
            logging.warning("CMC_API_KEY не найден. Использую режим по умолчанию.")
            return "⚪ НЕИЗВЕСТНО (Нет API ключа)", 0.0, 0.0

        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()["data"]
            
            # Получаем процентные изменения за 24 часа в USD
            quote = data["quote"]["USD"]
            cap_change = quote["total_market_cap"]["percent_change_24h"]
            vol_change = quote["total_volume_24h"]["percent_change_24h"]

            # Логика из PDF "Определение движения рынка с помощью объёмов"
            if cap_change > 0 and vol_change > 0:
                regime = "🟢 LONG (Рынок здоров, рост подтвержден объемами)"
            elif cap_change > 0 and vol_change < 0:
                regime = "🟡 RETEST (Рост на исходе, возможен откат/смена тренда)"
            elif cap_change < 0 and vol_change > 0:
                regime = "🔴 SHORT (Агрессивные продажи, паника, объем на падении)"
            else: # cap_change < 0 and vol_change < 0
                regime = "⚪ ACCUMULATION (Интерес угасает, возможен флэт или разворот)"

            return regime, round(cap_change, 2), round(vol_change, 2)

        except Exception as e:
            logging.error(f"Ошибка при запросе к CoinMarketCap: {e}")
            return "⚪ ОШИБКА ДАННЫХ", 0.0, 0.0

# Блок для локального тестирования
if __name__ == "__main__":
    print("\n--- Тест Global Market Health (Светофор) ---")
    checker = MarketHealthChecker()
    regime, cap_chg, vol_chg = checker.get_market_regime()
    
    print(f"Режим рынка: {regime}")
    print(f"Изменение капитализации (24ч): {cap_chg}%")
    print(f"Изменение объемов (24ч): {vol_chg}%")
    
    print("\nКак это использовать в боте:")
    if "🟢" in regime:
        print("-> Можно искать лонг-сетапы на альткоинах.")
    elif "🟡" in regime:
        print("-> Осторожно с лонгами, ищем точки для шорта или ждем ретеста.")
    elif "🔴" in regime:
        print("-> Только шорт-сетапы или выход в стейблкоины.")
    else:
        print("-> Рынок неопределен, лучше пропустить сделку.")
    print("--- Тест завершен ---\n")
