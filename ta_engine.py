import pandas as pd
import ta  # Библиотека Technical Analysis
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TAEngine:
    """
    Модуль технического анализа (PRO уровень).
    Использует библиотеку 'ta' (совместима с Python 3.14).
    """

    def __init__(self):
        self.ema_length = 50
        self.rsi_length = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.stoch_rsi_length = 14
        self.stoch_rsi_smooth1 = 3
        self.stoch_rsi_smooth2 = 3

    def analyze(self, df: pd.DataFrame) -> dict:
        """
        Принимает DataFrame со свечами (columns: 'open', 'high', 'low', 'close', 'volume')
        Возвращает словарь с интерпретацией индикаторов.
        """
        try:
            current_price = float(df['close'].iloc[-1])
            prev_price = float(df['close'].iloc[-2])

            # 1. ТРЕНД (EMA 50)
            ema_indicator = ta.trend.EMAIndicator(close=df['close'], window=self.ema_length)
            ema_50 = float(ema_indicator.ema_indicator().iloc[-1])
            trend = "Бычий 🟢 (Цена > EMA50)" if current_price > ema_50 else "Медвежий 🔴 (Цена < EMA50)"

            # 2. ИМПУЛЬС (RSI)
            rsi_indicator = ta.momentum.RSIIndicator(close=df['close'], window=self.rsi_length)
            rsi = float(rsi_indicator.rsi().iloc[-1])

            # 3. STOCHRSI
            stoch_rsi_indicator = ta.momentum.StochRSIIndicator(
                close=df['close'], 
                window=self.stoch_rsi_length,
                smooth1=self.stoch_rsi_smooth1,
                smooth2=self.stoch_rsi_smooth2
            )
            stoch_k = float(stoch_rsi_indicator.stochrsi_k().iloc[-1])
            
            momentum = "Нейтрально"
            if rsi < 35 and stoch_k < 20:
                momentum = "Перепроданность (Потенциальный отскок вверх) 🟢"
            elif rsi > 65 and stoch_k > 80:
                momentum = "Перекупленность (Риск коррекции вниз) 🔴"

            # 4. MACD
            macd_indicator = ta.trend.MACD(
                close=df['close'], 
                window_slow=self.macd_slow, 
                window_fast=self.macd_fast, 
                window_sign=self.macd_signal
            )
            macd_hist = float(macd_indicator.macd_diff().iloc[-1])
            macd_signal_text = "Рост импульса 📈" if macd_hist > 0 else "Падение импульса 📉"

            # 5. PVT (Price Volume Trend) - ИЗ PDF "Совмещение стратегий"
            pvt_indicator = ta.volume.VolumePriceTrendIndicator(
                close=df['close'], 
                 volume=df['volume']
            )

            # Получаем значения PVT для текущей и предыдущей свечи
            pvt_series = pvt_indicator.volume_price_trend()
            pvt = float(pvt_series.iloc[-1])
            pvt_prev = float(pvt_series.iloc[-2])

            # Проверяем дивергенцию (подтверждение объема)
            price_up = current_price > prev_price
            vol_up = pvt > pvt_prev

            if price_up and vol_up:
                volume_confirmed = "Да ✅ (Рост на объемах)"
            elif not price_up and not vol_up:
               volume_confirmed = "Да ✅ (Падение на объемах)"
            else:
                volume_confirmed = "Нет ⚠️ (Дивергенция! Движение не подтверждено объемом)"

            # 6. FRACTALS (Упрощенные уровни для SL/TP)
            # Ищем локальные минимумы и максимумы за последние 10 свечей
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
    
    print("\n📊 РЕЗУЛЬТАТ АНАЛИЗА ПОСЛЕДНЕЙ СВЕЧИ:")
    for key, value in result.items():
        print(f"  • {key.replace('_', ' ').title()}: {value}")
        
    print("\n--- Тест завершен ---\n")
