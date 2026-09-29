import pandas as pd
import ta  # Вместо pandas_ta
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TAEngine:
    """
    Модуль технического анализа (PRO уровень).
    Рассчитывает индикаторы на основе данных свечей (OHLCV) 
    с учетом правил из PDF "Алгоритм успешной сделки" и "Совмещение стратегий".
    Использует библиотеку 'ta' (совместима с Python 3.14).
    """

    def __init__(self):
        # Настройки индикаторов по рекомендациям трейдеров
        self.ema_length = 50
        self.rsi_length = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.stoch_rsi_length = 14
        self.bb_length = 20
        self.bb_std = 2

    def analyze(self, df: pd.DataFrame) -> dict:
        """
        Принимает DataFrame со свечами (должен содержать columns: 'open', 'high', 'low', 'close', 'volume')
        Возвращает словарь с интерпретацией индикаторов для последней закрытой свечи.
        """
        try:
            current_price = float(df['close'].iloc[-1])
            prev_price = float(df['close'].iloc[-2])

            # 1. ТРЕНД (EMA 50)
            ema_50 = float(df.ta.ema(length=self.ema_length).iloc[-1])
            trend = "Бычий 🟢 (Цена > EMA50)" if current_price > ema_50 else "Медвежий 🔴 (Цена < EMA50)"

            # 2. ИМПУЛЬС (RSI + StochRSI)
            rsi = float(df.ta.rsi(length=self.rsi_length).iloc[-1])
            stoch_rsi = df.ta.stochrsi(length=self.stoch_rsi_length)
            stoch_k = float(stoch_rsi['stochrsi_k'].iloc[-1])
            stoch_d = float(stoch_rsi['stochrsi_d'].iloc[-1])
            
            momentum = "Нейтрально"
            if rsi < 35 and stoch_k < 20:
                momentum = "Перепроданность (Потенциальный отскок вверх) 🟢"
            elif rsi > 65 and stoch_k > 80:
                momentum = "Перекупленность (Риск коррекции вниз) 🔴"

            # 3. MACD (Подтверждение импульса)
            macd = df.ta.macd(close=df['close'], window_slow=self.macd_slow, window_fast=self.macd_fast, window_sign=self.macd_signal)
            macd_hist = float(macd['macd_diff'].iloc[-1])
            macd_signal_text = "Рост импульса " if macd_hist > 0 else "Падение импульса 📉"

            # 4. PVT (Price Volume Trend) - ИЗ PDF "Совмещение стратегий"
            pvt = float(df.ta.pvt().iloc[-1])
            pvt_prev = float(df.ta.pvt().iloc[-2])
            
            price_up = current_price > prev_price
            vol_up = pvt > pvt_prev
            
            if price_up and vol_up:
                volume_confirmed = "Да ✅ (Рост на объемах)"
            elif not price_up and not vol_up:
                volume_confirmed = "Да ✅ (Падение на объемах)"
            else:
                volume_confirmed = "Нет ⚠️ (Дивергенция! Движение не подтверждено объемом)"

            # 5. FRACTALS (Уровни для Стоп-Лосса и Тейк-Профита)
            recent_lows = float(df['low'].iloc[-10:].min())
            recent_highs = float(df['high'].iloc[-10:].max())
            
            risk = current_price - recent_lows
            reward = recent_highs - current_price
            rr_ratio = round(reward / risk, 2) if risk > 0 else 0.0
            rr_status = "Выгодный (≥ 1:2) ✅" if rr_ratio >= 2.0 else "Невыгодный (< 1:2) ⚠️"

            return {
                "price": round(current_price, 4),
                "trend": trend,
                "momentum": momentum,
                "macd": macd_signal_text,
                "volume_confirmed": volume_confirmed,
                "support_level (SL)": round(recent_lows, 4),
                "resistance_level (TP)": round(recent_highs, 4),
                "estimated_R:R": f"1 : {rr_ratio} ({rr_status})",
                "rsi": round(rsi, 2),
                "stoch_k": round(stoch_k, 2)
            }

        except Exception as e:
            logging.error(f"Ошибка в TA Engine: {e}")
            return {"error": str(e)}

# Блок для локального тестирования
if __name__ == "__main__":
    print("\n--- Тест TA Engine (Технический анализ PRO + правила из PDF) ---")
    
    # Генерируем тестовые данные (100 свечей)
    np.random.seed(42)
    dates = pd.date_range(end='2026-09-28', periods=100, freq='15min')
    closes = np.cumsum(np.random.randn(100)) + 100
    opens = closes + np.random.randn(100) * 0.5
    highs = np.maximum(opens, closes) + np.random.rand(100) * 1.5
    lows = np.minimum(opens, closes) - np.random.rand(100) * 1.5
    volumes = np.random.randint(1000, 5000, 100)
    
    df = pd.DataFrame({
        'open': opens, 'high': highs, 'low': lows, 'close': closes, 'volume': volumes
    }, index=dates)

    engine = TAEngine()
    result = engine.analyze(df)
    
    print("\n РЕЗУЛЬТАТ АНАЛИЗА ПОСЛЕДНЕЙ СВЕЧИ:")
    for key, value in result.items():
        print(f"  • {key.replace('_', ' ').title()}: {value}")
        
    print("\n--- Тест завершен ---\n")
