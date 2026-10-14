import os
import requests
import json
import logging
import time
from datetime import datetime, timezone, timedelta
import yfinance as yf
import pandas as pd
import numpy as np

from global_market_health import MarketHealthChecker
from macro_calendar import MacroCalendar
from ta_engine import TAEngine
from pattern_recognition import PatternRecognizer
from visualizer import ChartVisualizer
from ai_models_config import get_models_for_task

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive'
}

SCAN_COINS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "NEARUSDT", "UNIUSDT", "AAVEUSDT", "FETUSDT", "ARBUSDT"
]

COINGECKO_IDS = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin", "XRPUSDT": "ripple", "ADAUSDT": "cardano",
    "DOGEUSDT": "dogecoin", "AVAXUSDT": "avalanche-2", "LINKUSDT": "chainlink",
    "DOTUSDT": "polkadot", "NEARUSDT": "near", "UNIUSDT": "uniswap",
    "AAVEUSDT": "aave", "FETUSDT": "fetch-ai", "ARBUSDT": "arbitrum"
}

LAST_SIGNALS_FILE = "last_signals.json"

def load_last_signals():
    try:
        if os.path.exists(LAST_SIGNALS_FILE):
            with open(LAST_SIGNALS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {"signals": []}

def save_last_signals(data):
    try:
        with open(LAST_SIGNALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Ошибка сохранения истории: {e}")

def is_duplicate_signal(symbol, direction):
    history = load_last_signals()
    now = datetime.now().isoformat()
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
    history["signals"] = [s for s in history["signals"] if s["time"] > cutoff]
    
    for signal in history["signals"]:
        if signal["symbol"] == symbol and signal["direction"] == direction:
            return True
    
    history["signals"].append({
        "symbol": symbol,
        "direction": direction,
        "time": now
    })
    save_last_signals(history)
    return False

def get_historical_data_binance(symbol: str) -> pd.DataFrame:
    try:
        time.sleep(1)
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=96"
        response = requests.get(url, headers=BROWSER_HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 40:
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'ct', 'qav', 'not', 'tbba', 'tbqa', 'ignore'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                logging.info(f"✅ {symbol}: Получено {len(df)} свечей (1H) через Binance")
                return df
    except Exception as e:
        logging.warning(f"⚠️ {symbol}: Binance ошибка - {str(e)[:50]}")
    return pd.DataFrame()

def get_historical_data_bybit(symbol: str) -> pd.DataFrame:
    try:
        time.sleep(1)
        url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval=60&limit=96"
        response = requests.get(url, headers=BROWSER_HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0 and 'result' in data:
                klines = data['result'].get('list', [])
                if klines and len(klines) > 40:
                    klines.reverse()
                    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
                    df.set_index('timestamp', inplace=True)
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = df[col].astype(float)
                    logging.info(f"✅ {symbol}: Получено {len(df)} свечей (1H) через Bybit")
                    return df
    except Exception as e:
        logging.warning(f"⚠️ {symbol}: Bybit ошибка - {str(e)[:50]}")
    return pd.DataFrame()

def get_historical_data_coingecko(symbol: str) -> pd.DataFrame:
    coin_id = COINGECKO_IDS.get(symbol)
    if not coin_id:
        return pd.DataFrame()
    try:
        time.sleep(1.5)
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency=usd&days=4"
        response = requests.get(url, headers=BROWSER_HEADERS, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 40:
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                for col in ['open', 'high', 'low', 'close']:
                    df[col] = df[col].astype(float)
                df['volume'] = 0.0
                logging.info(f"✅ {symbol}: Получено через CoinGecko (1H)")
                return df
    except Exception as e:
        logging.warning(f"⚠️ {symbol}: CoinGecko ошибка - {str(e)[:50]}")
    return pd.DataFrame()

def get_historical_data_yahoo(symbol: str) -> pd.DataFrame:
    try:
        logging.info(f"🔄 {symbol}: Биржи заблокированы, используем Yahoo Finance (1H)...")
        yf_symbol = symbol.replace('USDT', '-USD')
        df = yf.download(yf_symbol, period="7d", interval="1h", progress=False)
        
        if not df.empty and len(df) > 40:
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            
            df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
            df = df[['open', 'high', 'low', 'close', 'volume']]
            df = df.tail(96)
            
            logging.info(f"✅ {symbol}: Успешно получено {len(df)} свечей (1H) через Yahoo Finance!")
            return df
    except Exception as e:
        logging.error(f"❌ {symbol}: Yahoo Finance тоже упал - {str(e)[:50]}")
    return pd.DataFrame()

def get_historical_data(symbol: str) -> pd.DataFrame:
    df = get_historical_data_binance(symbol)
    if not df.empty and len(df) >= 40:
        return df
    
    df = get_historical_data_bybit(symbol)
    if not df.empty and len(df) >= 40:
        return df
    
    df = get_historical_data_coingecko(symbol)
    if not df.empty and len(df) >= 40:
        return df
    
    df = get_historical_data_yahoo(symbol)
    if not df.empty and len(df) >= 40:
        return df
    
    logging.error(f"❌ {symbol}: ВСЕ источники данных недоступны!")
    return pd.DataFrame()

def evaluate_signal_quality(ta_data: dict) -> tuple:
    try:
        rr_str = ta_data['estimated_R:R'].split(':')[1].strip().split()[0]
        rr_value = float(rr_str)
        
        if rr_value > 10.0:
            rr_value = 1.0
            logging.warning(f"⚠️ Аномальный R:R ({rr_str}), нормализован до 1.0")
    except:
        rr_value = 0.0
        
    volume_confirmed = "Да ✅" in ta_data['volume_confirmed']
    
    # НОВОЕ: Проверка Williams %R
    wr14 = ta_data.get('wr14', -50)
    wr21 = ta_data.get('wr21', -50)
    wr_oversold = wr14 < -80 and wr21 < -80
    
    # ПОНИЖЕННЫЕ ПОРОГИ для достижения TP3
    if rr_value >= 1.1 and volume_confirmed and wr_oversold:
        return ("high", "🟢", "Высоковероятный сигнал (WR подтверждает)")
    elif rr_value >= 1.1 and volume_confirmed:
        return ("high", "", "Высоковероятный сигнал")
    elif rr_value >= 1.0 and volume_confirmed:
        return ("medium", "", "Средняя вероятность")
    elif rr_value >= 1.1 and wr_oversold:
        return ("medium", "🟡", "Хороший R:R + WR перепроданность")
    elif rr_value >= 1.0 and not volume_confirmed:
        return ("medium", "🟡", "Хороший R:R, но объем не подтвержден")
    else:
        return ("low", "⚪", "Низкая вероятность — лучше воздержаться")

def generate_analysis_post(symbol, ta_data, pattern_data, macro_regime, macro_warning, quality_level, quality_emoji, quality_desc):
    coin_name = symbol.replace('USDT', '')
    
    try:
        rr_value = ta_data['estimated_R:R'].split(':')[1].strip().split()[0]
    except:
        rr_value = "N/A"
    
    is_long = "Бычий" in ta_data['trend']
    direction = "ЛОНГ (покупка)" if is_long else "ШОРТ (продажа)"
    direction_emoji = "🟢" if is_long else "🔴"
    
    entry = ta_data['entry']
    sl = ta_data['sl']
    tp = ta_data['tp']
    
    if is_long:
        tp1 = round(entry + (tp - entry) * 0.4, 4)
        tp2 = round(entry + (tp - entry) * 0.7, 4)
        tp3 = tp
    else:
        tp1 = round(entry - (entry - tp) * 0.4, 4)
        tp2 = round(entry - (entry - tp) * 0.7, 4)
        tp3 = tp
    
    leverage = "3x-5x" if quality_level == "high" else "2x-3x"
    
    pattern_text = ', '.join(pattern_data['patterns'])
    has_bullish_pattern = any('Бычий' in p for p in pattern_data['patterns'])
    
    if 'Бычий' in ta_data['trend'] and 'Да ✅' in ta_data['volume_confirmed']:
        justification = "Рост подтвержден объемом и бычьим трендом."
    elif 'Медвежий' in ta_data['trend'] and 'Да ✅' in ta_data['volume_confirmed']:
        if has_bullish_pattern:
            justification = f"Несмотря на медвежий тренд, обнаружен бычий паттерн ({pattern_text}), что может сигнализировать о развороте."
        else:
            justification = "Падение подтверждено объемом и медвежьим трендом."
    elif has_bullish_pattern:
        justification = f"Обнаружен бычий паттерн ({pattern_text}), но движение не подтверждено объемом — повышенный риск."
    else:
        justification = "Движение не подтверждено объемом — повышенный риск манипуляций."
    
    if quality_level == "high":
        rec = "✅ Сигнал соответствует всем критериям. Можно рассматривать вход."
    elif quality_level == "medium":
        rec = "⚠️ Сигнал средний. Рекомендуется уменьшить размер позиции до 2-3% от депозита."
    else:
        rec = "🛑 Рынок не дает четких сигналов. Лучше сохранить капитал и дождаться лучших условий."
    
    post = f"""{quality_emoji} **ТОРГОВЫЙ СИГНАЛ: {coin_name}**

📊 **КАЧЕСТВО СИГНАЛА:** {quality_desc}

🎯 **ПАРАМЕТРЫ СДЕЛКИ:**
• Направление: {direction_emoji} **{direction}**
• 🔵 **Точка входа (Entry):** ${entry}
• 🟢 **Стоп-лосс (SL):** ${sl} *(если цена упадет ниже — выходим)*
• 🔴 **Цели прибыли (TP):**
  - TP1: ${tp1} *(фиксация 40% прибыли)*
  - TP2: ${tp2} *(фиксация 70% прибыли)*
  - TP3: ${tp3} *(полная цель)*
• **Плечо:** {leverage} *(безопасно для новичков)*
• Соотношение Риск/Прибыль: **1:{rr_value}**

📈 **МАКРО-КОНТЕКСТ:**
• Глобальный режим: {macro_regime}
{macro_warning if macro_warning else '• Макро-событий в ближайшие 24 часа не ожидается'}

📉 **ТЕХНИЧЕСКАЯ КАРТИНА (1H таймфрейм):**
• Тренд: {ta_data['trend']}
• Импульс: {ta_data['momentum']}
• MACD: {ta_data['macd']}
• Объем (PVT): {ta_data['volume_confirmed']}
• Паттерн: {pattern_text}

💡 **ОБОСНОВАНИЕ:**
{justification}

📋 **РЕКОМЕНДАЦИЯ:**
{rec}

⏱️ **СРОК АКТУАЛЬНОСТИ:** 4-8 часов

⚠️ **РИСК-МЕНЕДЖМЕНТ:**
• Не рискуйте более **5%** от депозита на одну сделку
• Обязательно используйте Stop Loss
• Соотношение риск/прибыль должно быть ≥ 1:2 (текущее: 1:{rr_value})

📜 **ДИСКЛЕЙМЕР:**
⚠️ Не является индивидуальной инвестиционной рекомендацией. Финансовые рынки сопряжены с риском потери средств. Проводите собственное исследование (DYOR)."""

    return post

def send_to_telegram(text: str, chart_paths: list, symbol: str):
    """Отправляет сигнал в Telegram: несколько картинок, потом полный текст"""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    if not bot_token or not channel_id:
        logging.error("❌ Отсутствуют TELEGRAM_BOT_TOKEN или TELEGRAM_CHANNEL_ID")
        return

    # Отправляем все картинки по очереди
    for i, chart_path in enumerate(chart_paths):
        try:
            with open(chart_path, 'rb') as f:
                coin_name = symbol.replace('USDT', '')
                
                if i == 0:
                    caption = f"📊 **ТОРГОВЫЙ СИГНАЛ: {coin_name}**\n\n🎯 Точка входа + SL/TP\n\n👇 *Осцилляторы ниже*"
                elif i == 1:
                    caption = f"📈 **MACD** — импульс тренда"
                elif i == 2:
                    caption = f"📉 **RSI + StochRSI** — перекупленность/перепроданность"
                elif i == 3:
                    caption = f" **Williams %R** — подтверждение разворота"
                
                files = {
                    'photo': (f'chart_{i}.png', f, 'image/png'),
                    'chat_id': (None, channel_id),
                    'caption': (None, caption),
                    'parse_mode': (None, 'Markdown')
                }
                
                response = requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                    files=files,
                    timeout=30
                )
                
                if response.status_code == 200:
                    logging.info(f"✅ Картинка {i+1}/{len(chart_paths)} отправлена!")
                else:
                    logging.error(f"❌ Ошибка отправки картинки {i+1}: {response.text}")
                
                time.sleep(1)
                
        except Exception as e:
            logging.error(f"❌ Ошибка отправки картинки {i+1}: {e}")
    
    # Отправляем полный текст
    try:
        max_length = 4000
        parts = []
        
        if len(text) <= max_length:
            parts.append(text)
        else:
            paragraphs = text.split('\n\n')
            current_part = ""
            for para in paragraphs:
                if len(current_part) + len(para) + 2 <= max_length:
                    current_part += para + "\n\n"
                else:
                    if current_part:
                        parts.append(current_part.strip())
                    current_part = para + "\n\n"
            if current_part:
                parts.append(current_part.strip())
        
        for i, part in enumerate(parts):
            if i > 0:
                time.sleep(2)
            
            text_payload = {
                "chat_id": channel_id,
                "text": part,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            response = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json=text_payload,
                timeout=15
            )
            
            if response.status_code == 200:
                logging.info(f"✅ Текст (часть {i+1}/{len(parts)}) отправлен!")
            else:
                logging.error(f"❌ Ошибка отправки текста: {response.text}")
                
    except Exception as e:
        logging.error(f"❌ Ошибка отправки текста: {e}")

def main():
    logging.info("🌙 Запуск Лунного Дозора v3.0 (4 графика + строгая фильтрация)")
    
    health_checker = MarketHealthChecker()
    regime, _, _ = health_checker.get_market_regime()
    logging.info(f"Глобальный режим: {regime}")
    
    macro_calendar = MacroCalendar()
    macro_warning = macro_calendar.get_warning_message()
    
    ta_engine = TAEngine()
    pattern_recognizer = PatternRecognizer(lookback=20)
    visualizer = ChartVisualizer()
    
    best_coin = None
    best_score = -1.0
    
    for coin in SCAN_COINS:
        logging.info(f"🔍 Анализ {coin}...")
        df = get_historical_data(coin)
        if df.empty:
            continue
            
        ta_data = ta_engine.analyze(df)
        if isinstance(ta_data, dict) and "error" in ta_data:
            continue
        if not isinstance(ta_data, dict) or "price" not in ta_data:
            continue

        pattern_data = pattern_recognizer.analyze_patterns(df)
        quality_level, quality_emoji, quality_desc = evaluate_signal_quality(ta_data)
        
        # НОВОЕ: Строгая фильтрация — минимум 3 индикатора должны подтверждать
        confirmation_count = 0
        
        # 1. Тренд (EMA)
        if "Бычий" in ta_data['trend'] or "Медвежий" in ta_data['trend']:
            confirmation_count += 1
        
        # 2. Объем (PVT)
        if "Да ✅" in ta_data['volume_confirmed']:
            confirmation_count += 1
        
        # 3. RSI/StochRSI
        rsi = ta_data.get('rsi', 50)
        stoch_k = ta_data.get('stoch_k', 50)
        if (rsi < 35 and stoch_k < 20) or (rsi > 65 and stoch_k > 80):
            confirmation_count += 1
        
        # 4. Williams %R
        wr14 = ta_data.get('wr14', -50)
        wr21 = ta_data.get('wr21', -50)
        if wr14 < -80 and wr21 < -80:
            confirmation_count += 1
        
        # 5. Bollinger Bands
        boll_status = ta_data.get('boll_status', '')
        if "перепроданность" in boll_status.lower() or "перекупленность" in boll_status.lower():
            confirmation_count += 1
        
        # Если меньше 3 подтверждений — пропускаем
        if confirmation_count < 3:
            logging.info(f"⏸️ {coin}: Только {confirmation_count}/5 индикаторов подтверждают. Пропускаем.")
            continue
        
        try:
            rr_value = float(ta_data['estimated_R:R'].split(':')[1].strip().split()[0])
            if rr_value > 10.0:
                rr_value = 1.0
                logging.warning(f"⚠️ {coin}: Аномальный R:R, нормализован")
        except:
            rr_value = 0.0
        
        score = rr_value + (0.5 if "Да ✅" in ta_data['volume_confirmed'] else 0) + (confirmation_count * 0.2)
        logging.info(f"✅ {coin}: Score {score} (подтверждений: {confirmation_count}/5)")
        
        if score > best_score:
            best_score = score
            best_coin = {
                "symbol": coin, 
                "ta": ta_data, 
                "patterns": pattern_data, 
                "df": df, 
                "ql": quality_level, 
                "qe": quality_emoji, 
                "qd": quality_desc,
                "confirmations": confirmation_count
            }
    
    if best_coin:
        is_long = "Бычий" in best_coin['ta']['trend']
        direction = "ЛОНГ" if is_long else "ШОРТ"
        
        if is_duplicate_signal(best_coin['symbol'], direction):
            logging.info(f"⏸️ Сигнал {best_coin['symbol']} {direction} уже отправлялся. Пропускаем.")
            return
        
        logging.info(f"🏆 Лучшая: {best_coin['symbol']} (подтверждений: {best_coin['confirmations']}/5)")
        
        # НОВОЕ: Генерируем все 4 графика
        chart_paths = visualizer.generate_all_charts(
            best_coin['df'], 
            best_coin['symbol'], 
            best_coin['ta']
        )
        
        if chart_paths:
            post_text = generate_analysis_post(
                best_coin['symbol'], 
                best_coin['ta'], 
                best_coin['patterns'], 
                regime, 
                macro_warning, 
                best_coin['ql'], 
                best_coin['qe'], 
                best_coin['qd']
            )
            send_to_telegram(post_text, chart_paths, best_coin['symbol'])
        else:
            logging.error("❌ Не удалось сгенерировать графики")
    else:
        logging.error("❌ СБОЙ: Не удалось получить данные ни для одной монеты.")

if __name__ == "__main__":
    main()
