import os
import requests
import logging
from datetime import datetime, timezone, timedelta
from multi_exchange_aggregator import ExchangeAggregator
from global_market_health import MarketHealthChecker
from macro_calendar import MacroCalendar
from ta_engine import TAEngine
from pattern_recognition import PatternRecognizer
from visualizer import ChartVisualizer
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Монеты для сканирования (выбраны из PDF "Портфели" для разнообразия секторов)
SCAN_COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "FETUSDT", "ARBUSDT"]

def get_historical_data(symbol: str, timeframe: str = "1h", limit: int = 100) -> pd.DataFrame:
    """Получает свечи через агрегатор (Bybit с фоллбэком на Binance)"""
    aggregator = ExchangeAggregator()
    # Примечание: в реальном коде multi_exchange_aggregator должен возвращать OHLCV. 
    # Для простоты здесь мы эмулируем запрос к Binance API, так как он стабильнее для исторических данных без ключей.
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={timeframe}&limit={limit}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
            
        return df
    except Exception as e:
        logging.error(f"Ошибка получения данных для {symbol}: {e}")
        return pd.DataFrame()

def generate_signal_post(symbol: str, ta_data: dict, pattern_data: dict, macro_warning: str, chart_path: str) -> str:
    """Формирует финальный текст сигнала по правилам из PDF (РММ, Текпрофит)"""
    direction = "🟢 ЛОНГ" if "Бычий" in ta_data['trend'] else "🔴 ШОРТ"
    
    post = f"""🚀 **ТОРГОВЫЙ СИГНАЛ: {symbol.replace('USDT', '')}**

📊 **Технический анализ:**
• Тренд: {ta_data['trend']}
• Паттерн: {', '.join(pattern_data['patterns'])}
• Объем (PVT): {ta_data['volume_confirmed']}
• R:R (Риск/Прибыль): {ta_data['estimated_R:R']}

🎯 **Параметры сделки:**
• Точка входа: ~${ta_data['price']}
• 🛑 Stop Loss: ${ta_data['support_level (SL)']}
• 💰 Take Profit: ${ta_data['resistance_level (TP)']}

{macro_warning if macro_warning else '🌍 **Макро-фон:** Спокойный, штормов не ожидается.'}

⚠️ **ПРАВИЛА РИСК-МЕНЕДЖМЕНТА (из PDF):**
1. Не рискуйте более **5%** от депозита на одну сделку.
2. Обязательно используйте Stop Loss.
3. Соотношение риск/прибыль должно быть ≥ 1:2 (текущее: {ta_data['estimated_R:R'].split(':')[1].strip().split()[0]}).

📜 *DYOR: Это не финансовая рекомендация. Проводите собственный анализ.*
"""
    return post

def send_to_telegram(text: str, chart_path: str):
    """Отправляет сигнал в Telegram (текст + график)"""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    if not bot_token or not channel_id:
        logging.error("Отсутствуют TELEGRAM_BOT_TOKEN или TELEGRAM_CHANNEL_ID")
        return

    try:
        # Сначала отправляем картинку с текстом в caption
        with open(chart_path, 'rb') as f:
            files = {
                'photo': ('signal_chart.png', f, 'image/png'),
                'chat_id': (None, channel_id),
                'caption': (None, text),
                'parse_mode': (None, 'Markdown')
            }
            response = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                files=files,
                timeout=30
            )
            
        if response.status_code == 200:
            logging.info("✅ Сигнал успешно отправлен в Telegram!")
        else:
            logging.error(f"❌ Ошибка Telegram: {response.text}")
            
    except Exception as e:
        logging.error(f"❌ Ошибка отправки: {e}")

def main():
    logging.info("🌙 Запуск Лунного Дозора: Генератор Сигналов v2.0")
    
    # 1. Макро-фильтр (Светофор)
    health_checker = MarketHealthChecker()
    regime, cap_chg, vol_chg = health_checker.get_market_regime()
    logging.info(f"Глобальный режим рынка: {regime}")
    
    # 2. Макро-календарь
    macro_calendar = MacroCalendar()
    macro_warning = macro_calendar.get_warning_message()
    
    # 3. Сканирование монет
    ta_engine = TAEngine()
    pattern_recognizer = PatternRecognizer(lookback=20)
    visualizer = ChartVisualizer()
    
    best_signal = None
    best_rr = 0.0
    
    for coin in SCAN_COINS:
        logging.info(f"Анализ {coin}...")
        df = get_historical_data(coin, timeframe="1h", limit=100)
        if df.empty:
            continue
            
        ta_data = ta_engine.analyze(df)
        if "error" in ta_data:
            continue
            
        pattern_data = pattern_recognizer.analyze_patterns(df)
        
        # Извлекаем числовое значение R:R для сравнения
        try:
            rr_str = ta_data['estimated_R:R'].split(':')[1].strip().split()[0]
            rr_value = float(rr_str)
        except:
            rr_value = 0.0
            
        # ФИЛЬТР: Ищем только сделки с R:R >= 1.5 и подтвержденным объемом
        if rr_value >= 1.5 and "Да ✅" in ta_data['volume_confirmed']:
            if rr_value > best_rr:
                best_rr = rr_value
                best_signal = {
                    "symbol": coin,
                    "ta": ta_data,
                    "patterns": pattern_data,
                    "df": df # Сохраняем для графика
                }
                
    # 4. Если нашли хорошую сделку - генерируем и отправляем
    if best_signal:
        logging.info(f"✅ Найдена высоковероятная сделка: {best_signal['symbol']} (R:R {best_rr})")
        
        # Генерируем график
        chart_path = visualizer.generate_signal_chart(
            best_signal['df'], 
            best_signal['symbol'], 
            best_signal['ta'], 
            filename=f"signal_{best_signal['symbol']}.png"
        )
        
        if chart_path:
            post_text = generate_signal_post(
                best_signal['symbol'],
                best_signal['ta'],
                best_signal['patterns'],
                macro_warning,
                chart_path
            )
            send_to_telegram(post_text, chart_path)
        else:
            logging.warning("Не удалось создать график, отправляем только текст.")
            # (Можно добавить отправку только текста, если график не создался)
            
    else:
        logging.info("ℹ️ Высоковероятных сделок (R:R ≥ 1.5 с подтверждением объема) не найдено. Сохраняем капитал.")
        # Опционально: можно отправлять сообщение "Рынок во флэте, ждем настроек"

if __name__ == "__main__":
    main()
