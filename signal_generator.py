import os
import requests
import json
import logging
from datetime import datetime, timezone, timedelta
from global_market_health import MarketHealthChecker
from macro_calendar import MacroCalendar
from ta_engine import TAEngine
from pattern_recognition import PatternRecognizer
from visualizer import ChartVisualizer
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 15 самых ликвидных монет
SCAN_COINS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "NEARUSDT", "UNIUSDT", "AAVEUSDT", "FETUSDT", "ARBUSDT"
]

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

def evaluate_signal_quality(ta_data: dict) -> tuple:
    """Оценивает качество сигнала и возвращает (уровень, emoji, описание)"""
    try:
        rr_str = ta_data['estimated_R:R'].split(':')[1].strip().split()[0]
        rr_value = float(rr_str)
    except:
        rr_value = 0.0
    
    volume_confirmed = "Да ✅" in ta_data['volume_confirmed']
    
    if rr_value >= 1.5 and volume_confirmed:
        return ("high", "", "Высоковероятный сигнал")
    elif rr_value >= 1.2 and volume_confirmed:
        return ("medium", "🟡", "Средняя вероятность")
    elif rr_value >= 1.5 and not volume_confirmed:
        return ("medium", "🟡", "Хороший R:R, но объем не подтвержден")
    else:
        return ("low", "", "Низкая вероятность — лучше воздержаться")

def generate_analysis_post(symbol: str, ta_data: dict, pattern_data: dict, 
                          macro_regime: str, macro_warning: str, quality_level: str,
                          quality_emoji: str, quality_desc: str) -> str:
    """Формирует детальный анализ с оценкой качества"""
    direction = " ЛОНГ" if "Бычий" in ta_data['trend'] else "🔴 ШОРТ"
    coin_name = symbol.replace('USDT', '')
    
    try:
        rr_value = ta_data['estimated_R:R'].split(':')[1].strip().split()[0]
    except:
        rr_value = "N/A"
    
    # Рекомендация в зависимости от качества
    if quality_level == "high":
        recommendation = "✅ Сигнал соответствует всем критериям. Можно рассматривать вход."
    elif quality_level == "medium":
        recommendation = "⚠️ Сигнал средний. Рекомендуется уменьшить размер позиции до 2-3% от депозита."
    else:
        recommendation = "🛑 Рынок не дает четких сигналов. Лучше сохранить капитал и дождаться лучших условий."
    
    post = f"""{quality_emoji} **АНАЛИЗ РЫНКА: {coin_name}**

📊 **КАЧЕСТВО СИГНАЛА:** {quality_desc}

📈 **МАКРО-КОНТЕКСТ:**
• Глобальный режим: {macro_regime}
{macro_warning if macro_warning else '• Макро-событий в ближайшие 24 часа не ожидается'}

📉 **ТЕХНИЧЕСКАЯ КАРТИНА (1H таймфрейм):**
• Тренд: {ta_data['trend']}
• Импульс: {ta_data['momentum']}
• MACD: {ta_data['macd']}
• Объем (PVT): {ta_data['volume_confirmed']}
• Паттерн: {', '.join(pattern_data['patterns'])}

🎯 **УРОВНИ:**
• Текущая цена: ${ta_data['price']}
• Поддержка (SL): ${ta_data['support_level (SL)']}
• Сопротивление (TP): ${ta_data['resistance_level (TP)']}
• Соотношение Риск/Прибыль: **1:{rr_value}**

💡 **ОБОСНОВАНИЕ:**
{'Рост подтвержден объемом и бычьим трендом.' if 'Бычий' in ta_data['trend'] and 'Да ✅' in ta_data['volume_confirmed'] else 'Падение подтверждено объемом и медвежьим трендом.' if 'Медвежий' in ta_data['trend'] and 'Да ✅' in ta_data['volume_confirmed'] else 'Движение не подтверждено объемом — повышенный риск манипуляций.'}
{f' Обнаружен паттерн {pattern_data["patterns"][0]}, что усиливает сигнал.' if pattern_data['patterns'] and 'не обнаружено' not in pattern_data['patterns'][0] else ''}

📋 **РЕКОМЕНДАЦИЯ:**
{recommendation}

⚠️ **РИСК-МЕНЕДЖМЕНТ:**
• Не рискуйте более **5%** от депозита на одну сделку
• Обязательно используйте Stop Loss
• Соотношение риск/прибыль должно быть ≥ 1:2 (текущее: 1:{rr_value})

📜 **ДИСКЛЕЙМЕР:**
⚠️ Вся информация носит ИСКЛЮЧИТЕЛЬНО ознакомительный характер и НЕ является индивидуальной инвестиционной рекомендацией. Финансовые рынки сопряжены с высоким риском потери средств (вплоть до 100% депозита). Вы действуете на свой страх и риск (DYOR — Do Your Own Research, проводите собственное исследование). Прошлые результаты не гарантируют будущую прибыль.
"""
    return post

def send_to_telegram(text: str, chart_path: str):
    """Отправляет анализ в Telegram (текст + график)"""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    if not bot_token or not channel_id:
        logging.error("Отсутствуют TELEGRAM_BOT_TOKEN или TELEGRAM_CHANNEL_ID")
        return

    try:
        with open(chart_path, 'rb') as f:
            files = {
                'photo': ('analysis_chart.png', f, 'image/png'),
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
            logging.info("✅ Анализ успешно отправлен в Telegram!")
        else:
            logging.error(f"❌ Ошибка Telegram: {response.text}")
            
    except Exception as e:
        logging.error(f"❌ Ошибка отправки: {e}")

def main():
    logging.info("🌙 Запуск Лунного Дозора: Анализ рынка v2.2 (обязательный пост)")
    
    # 1. Макро-фильтр
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
    
    best_coin = None
    best_score = -1  # Будем искать монету с лучшим R:R
    
    for coin in SCAN_COINS:
        logging.info(f"Анализ {coin}...")
        df = get_historical_data(coin, timeframe="1h", limit=100)
        if df.empty:
            continue
            
        ta_data = ta_engine.analyze(df)
        if "error" in ta_data:
            continue
            
        pattern_data = pattern_recognizer.analyze_patterns(df)
        
        # Оцениваем качество
        quality_level, _, _ = evaluate_signal_quality(ta_data)
        
        # Считаем "очки" для сравнения монет
        try:
            rr_str = ta_data['estimated_R:R'].split(':')[1].strip().split()[0]
            rr_value = float(rr_str)
        except:
            rr_value = 0.0
        
        score = rr_value
        if "Да ✅" in ta_data['volume_confirmed']:
            score += 0.5  # Бонус за подтверждение объемом
        
        if score > best_score:
            best_score = score
            best_coin = {
                "symbol": coin,
                "ta": ta_data,
                "patterns": pattern_data,
                "df": df,
                "quality": quality_level
            }
    
    # 4. ВСЕГДА отправляем анализ лучшей монеты
    if best_coin:
        logging.info(f"✅ Лучшая монета: {best_coin['symbol']} (score: {best_score})")
        
        quality_level, quality_emoji, quality_desc = evaluate_signal_quality(best_coin['ta'])
        
        # Генерируем график
        chart_path = visualizer.generate_signal_chart(
            best_coin['df'], 
            best_coin['symbol'], 
            best_coin['ta'], 
            filename=f"analysis_{best_coin['symbol']}.png"
        )
        
        if chart_path:
            post_text = generate_analysis_post(
                best_coin['symbol'],
                best_coin['ta'],
                best_coin['patterns'],
                regime,
                macro_warning,
                quality_level,
                quality_emoji,
                quality_desc
            )
            send_to_telegram(post_text, chart_path)
        else:
            logging.warning("Не удалось создать график.")
    else:
        logging.error("❌ Не удалось проанализировать ни одну монету.")

if __name__ == "__main__":
    main()
