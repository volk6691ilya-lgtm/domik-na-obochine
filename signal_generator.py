import os
import requests
import json
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

# 15 самых ликвидных монет из всех портфелей PDF
SCAN_COINS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "NEARUSDT", "UNIUSDT", "AAVEUSDT", "FETUSDT", "ARBUSDT"
]

# Файл для хранения последних сигналов (защита от дубликатов)
LAST_SIGNALS_FILE = "last_signals.json"

def load_last_signals():
    """Загружает историю последних сигналов"""
    try:
        if os.path.exists(LAST_SIGNALS_FILE):
            with open(LAST_SIGNALS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {"signals": []}

def save_last_signals(data):
    """Сохраняет историю сигналов"""
    try:
        with open(LAST_SIGNALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Ошибка сохранения истории: {e}")

def is_duplicate_signal(symbol, direction):
    """Проверяет, не отправляли ли мы уже такой сигнал"""
    history = load_last_signals()
    now = datetime.now().isoformat()
    
    # Удаляем старые сигналы (старше 24 часов)
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
    history["signals"] = [s for s in history["signals"] if s["time"] > cutoff]
    
    # Проверяем дубликат
    for signal in history["signals"]:
        if signal["symbol"] == symbol and signal["direction"] == direction:
            return True
    
    # Добавляем новый сигнал
    history["signals"].append({
        "symbol": symbol,
        "direction": direction,
        "time": now
    })
    
    save_last_signals(history)
    return False

def get_historical_data(symbol: str, timeframe: str = "1h", limit: int = 100) -> pd.DataFrame:
    """Получает свечи через Binance API"""
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

def generate_detailed_signal(symbol: str, ta_data: dict, pattern_data: dict, macro_regime: str, macro_warning: str, chart_path: str) -> str:
    """Формирует детальный торговый план с дисклеймером"""
    direction = "🟢 ЛОНГ" if "Бычий" in ta_data['trend'] else "🔴 ШОРТ"
    coin_name = symbol.replace('USDT', '')
    
    # Извлекаем R:R
    try:
        rr_value = ta_data['estimated_R:R'].split(':')[1].strip().split()[0]
    except:
        rr_value = "N/A"
    
    post = f""" **ТОРГОВЫЙ ПЛАН: {coin_name}**

📊 **МАКРО-КОНТЕКСТ:**
• Глобальный режим: {macro_regime}
{macro_warning if macro_warning else '• Макро-событий в ближайшие 24 часа не ожидается'}

📈 **ТЕХНИЧЕСКАЯ КАРТИНА:**
• Тренд: {ta_data['trend']}
• Импульс: {ta_data['momentum']}
• MACD: {ta_data['macd']}
• Объем (PVT): {ta_data['volume_confirmed']}
• Паттерн: {', '.join(pattern_data['patterns'])}

🎯 **ПАРАМЕТРЫ СДЕЛКИ:**
• Направление: {direction}
• Точка входа: ~${ta_data['price']}
• 🛑 Stop Loss: ${ta_data['support_level (SL)']}
• 💰 Take Profit: ${ta_data['resistance_level (TP)']}
• Соотношение Риск/Прибыль: **1:{rr_value}**

💡 **ОБОСНОВАНИЕ:**
{'Рост подтвержден объемом и бычьим трендом. ' if 'Бычий' in ta_data['trend'] and 'Да ✅' in ta_data['volume_confirmed'] else 'Падение подтверждено объемом и медвежьим трендом. ' if 'Медвежий' in ta_data['trend'] and 'Да ✅' in ta_data['volume_confirmed'] else 'Движение не подтверждено объемом — повышенный риск. '}
{f'Обнаружен паттерн {pattern_data["patterns"][0]}, что усиливает сигнал.' if pattern_data['patterns'] and 'не обнаружено' not in pattern_data['patterns'][0] else ''}

⚠️ **РИСК-МЕНЕДЖМЕНТ:**
• Не рискуйте более **5%** от депозита на одну сделку
• Обязательно используйте Stop Loss
• Соотношение риск/прибыль должно быть ≥ 1:2 (текущее: 1:{rr_value})

📜 **ДИСКЛЕЙМЕР:**
⚠️ Вся информация носит ИСКЛЮЧИТЕЛЬНО ознакомительный характер и НЕ является индивидуальной инвестиционной рекомендацией. Финансовые рынки сопряжены с высоким риском потери средств (вплоть до 100% депозита). Вы действуете на свой страх и риск (DYOR — Do Your Own Research, проводите собственное исследование). Прошлые результаты не гарантируют будущую прибыль.
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
        # Отправляем картинку с текстом в caption
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
    logging.info("🌙 Запуск Лунного Дозора: Генератор Сигналов v2.1 (15 монет)")
    
    # 1. Макро-фильтр (Светофор)
    health_checker = MarketHealthChecker()
    regime, cap_chg, vol_chg = health_checker.get_market_regime()
    logging.info(f"Глобальный режим рынка: {regime}")
    
    # 2. Макро-календарь
    macro_calendar = MacroCalendar()
    macro_warning = macro_calendar.get_warning_message()
    
    # 3. Сканирование 15 монет
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
        
        # Извлекаем числовое значение R:R
        try:
            rr_str = ta_data['estimated_R:R'].split(':')[1].strip().split()[0]
            rr_value = float(rr_str)
        except:
            rr_value = 0.0
            
        # ФИЛЬТР: R:R >= 1.5 и подтвержденный объем
        if rr_value >= 1.5 and "Да ✅" in ta_data['volume_confirmed']:
            if rr_value > best_rr:
                best_rr = rr_value
                best_signal = {
                    "symbol": coin,
                    "ta": ta_data,
                    "patterns": pattern_data,
                    "df": df
                }
                
    # 4. Если нашли хорошую сделку - проверяем на дубликат и отправляем
    if best_signal:
        direction = "ЛОНГ" if "Бычий" in best_signal['ta']['trend'] else "ШОРТ"
        
        if is_duplicate_signal(best_signal['symbol'], direction):
            logging.info(f"️ Сигнал {best_signal['symbol']} {direction} уже отправлялся в последние 24 часа. Пропускаем.")
            return
        
        logging.info(f"✅ Найдена высоковероятная сделка: {best_signal['symbol']} (R:R {best_rr})")
        
        # Генерируем график
        chart_path = visualizer.generate_signal_chart(
            best_signal['df'], 
            best_signal['symbol'], 
            best_signal['ta'], 
            filename=f"signal_{best_signal['symbol']}.png"
        )
        
        if chart_path:
            post_text = generate_detailed_signal(
                best_signal['symbol'],
                best_signal['ta'],
                best_signal['patterns'],
                regime,
                macro_warning,
                chart_path
            )
            send_to_telegram(post_text, chart_path)
        else:
            logging.warning("Не удалось создать график, отправляем только текст.")
            
    else:
        logging.info("ℹ️ Высоковероятных сделок (R:R ≥ 1.5 с подтверждением объема) не найдено. Сохраняем капитал.")

if __name__ == "__main__":
    main()
