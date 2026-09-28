import requests
import logging
from typing import Dict, Optional

# Настройка логирования (чтобы видеть ошибки в GitHub Actions)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ExchangeAggregator:
    """
    Модуль для сбора данных с Bybit и Binance.
    Использует только публичные API (без ключей).
    """

    def __init__(self):
        self.bybit_base_url = "https://api.bybit.com/v5/market"
        self.binance_base_url = "https://api.binance.com/api/v3"
        self.timeout = 10 # Таймаут запросов в секундах

    def _get_bybit_price(self, symbol: str) -> Optional[Dict]:
        """Получает цену и объем с Bybit (Spot)"""
        try:
            url = f"{self.bybit_base_url}/tickers"
            params = {"category": "spot", "symbol": symbol}
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get("retCode") == 0 and data.get("result", {}).get("list"):
                ticker = data["result"]["list"][0]
                return {
                    "price": float(ticker["lastPrice"]),
                    "volume_24h": float(ticker["turnover24h"]), # Объем в USDT
                    "source": "Bybit"
                }
        except Exception as e:
            logging.error(f"Ошибка при запросе к Bybit ({symbol}): {e}")
        return None

    def _get_binance_price(self, symbol: str) -> Optional[Dict]:
        """Получает цену и объем с Binance (Spot)"""
        try:
            url = f"{self.binance_base_url}/ticker/24hr"
            params = {"symbol": symbol}
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            return {
                "price": float(data["lastPrice"]),
                "volume_24h": float(data["quoteVolume"]), # Объем в USDT
                "source": "Binance"
            }
        except Exception as e:
            logging.error(f"Ошибка при запросе к Binance ({symbol}): {e}")
        return None

    def get_unified_data(self, symbol: str) -> Optional[Dict]:
        """
        Собирает данные с обеих бирж, сравнивает их и возвращает единый словарь.
        """
        bybit_data = self._get_bybit_price(symbol)
        binance_data = self._get_binance_price(symbol)

        # Если обе биржи недоступны
        if not bybit_data and not binance_data:
            logging.critical(f"Не удалось получить данные для {symbol} ни с одной биржи!")
            return None

        # Если доступна только одна биржа
        if not bybit_data:
            logging.warning(f"Bybit недоступен для {symbol}, используем только Binance.")
            return binance_data
        if not binance_data:
            logging.warning(f"Binance недоступен для {symbol}, используем только Bybit.")
            return bybit_data

        # Если обе доступны - сравниваем (ищем спред)
        price_diff = abs(bybit_data["price"] - binance_data["price"])
        avg_price = (bybit_data["price"] + binance_data["price"]) / 2
        spread_percent = (price_diff / avg_price) * 100

        # Определяем приоритет: Bybit для альтов, Binance для топа (упрощенная логика)
        # Здесь просто возвращаем обе цены и спред
        return {
            "symbol": symbol,
            "bybit_price": bybit_data["price"],
            "binance_price": binance_data["price"],
            "spread_percent": round(spread_percent, 4),
            "bybit_volume": bybit_data["volume_24h"],
            "binance_volume": binance_data["volume_24h"],
            "anomaly_detected": spread_percent > 0.5 # Флаг аномалии
        }

# Блок для локального тестирования
if __name__ == "__main__":
    aggregator = ExchangeAggregator()
    
    # Тестируем на Биткоине и каком-нибудь альткоине
    test_symbols = ["BTCUSDT", "SOLUSDT", "LINKUSDT"]
    
    print("\n--- Тест Multi-Exchange Aggregator ---")
    for symbol in test_symbols:
        print(f"\nАнализ {symbol}:")
        data = aggregator.get_unified_data(symbol)
        if data:
            print(f"  Bybit: ${data['bybit_price']:.2f} (Vol: ${data['bybit_volume']/1_000_000:.2f}M)")
            print(f"  Binance: ${data['binance_price']:.2f} (Vol: ${data['binance_volume']/1_000_000:.2f}M)")
            print(f"  Спред: {data['spread_percent']}%")
            if data['anomaly_detected']:
                print("  ⚠️ ВНИМАНИЕ: Обнаружено расхождение цен > 0.5%!")
        else:
            print("  ❌ Данные не получены.")
    print("\n--- Тест завершен ---")
