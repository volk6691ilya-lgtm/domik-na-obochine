import pandas as pd
import ta
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TAEngine:
    def __init__(self):
        self.ema_length = 50
        self.rsi_length = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.stoch_rsi_length = 14

    def analyze(self, df: pd.DataFrame) -> dict:
        try:
            current_price = float(df['close'].iloc[-1])
            prev_price = float(df['close'].iloc[-2])

            # 1. ТРЕНД (EMA 50)
            try:
                ema_indicator = ta.trend.EMAIndicator(close=df['close'], window=self.ema_length)
                ema_50 = float(ema_indicator.ema_indicator().iloc[-1])
                trend = "Бычий 🟢 (Цена > EMA50)" if current_price > ema_50 else "Медвежий 🔴 (Цена < EMA50)"
            except Exception:
                trend = "Нейтрально ⚪ (EMA недоступен)"

            # 2. ИМПУЛЬС (RSI + StochRSI)
            try:
                rsi_indicator = ta.momentum.RSIIndicator(close=df['close'], window=self.rsi_length)
                rsi = float(rsi_indicator.rsi().iloc[-1])
                
                stoch_rsi_indicator = ta.momentum.StochRSIIndicator(
                    close=df['close'], window=self.stoch_rsi_length, smooth1=3, smooth2=3
                )
                stoch_k = float(stoch_rsi_indicator.stochrsi_k().iloc[-1])
                
                momentum = "Нейтрально"
                if rsi < 35 and stoch_k < 20:
                    momentum = "Перепроданность (Потенциальный отскок вверх) 🟢"
                elif rsi > 65 and stoch_k > 80:
                    momentum = "Перекупленность (Риск коррекции вниз) 🔴"
            except Exception:
                rsi, stoch_k = 50.0, 50.0
                momentum = "Нейтрально ⚪ (RSI недоступен)"

            # 3. MACD
            try:
                macd_indicator = ta.trend.MACD(
                    close=df['close'], window_slow=self.macd_slow, 
                    window_fast=self.macd_fast, window_sign=self.macd_signal
                )
                macd_hist = float(macd_indicator.macd_diff().iloc[-1])
                macd_signal_text = "Рост импульса 📈" if macd_hist > 0 else "Падение импульса 📉"
            except Exception:
                macd_signal_text = "Нейтрально ⚪ (MACD недоступен)"

            # 4. PVT (Price Volume Trend) - ЧИСТЫЙ РАСЧЕТ ЧЕРЕЗ PANDAS (100% стабильность)
            try:
                # Формула PVT: (Текущая цена - Предыдущая цена) / Предыдущая цена * Объем
                price_change = df['close'].pct_change()
                pvt_series = (price_change * df['volume']).cumsum()
                
                pvt = float(pvt_series.iloc[-1])
                pvt_prev = float(pvt_series.iloc[-2])
                
                price_up = current_price > prev_price
                vol_up = pvt > pvt_prev
                
                if price_up and vol_up:
                    volume_confirmed = "Да ✅ (Рост на объемах)"
                elif not price_up and not vol_up:
                    volume_confirmed = "Да ✅ (Падение на объемах)"
                else:
                    volume_confirmed = "Нет ⚠️ (Дивергенция! Движение не подтверждено объемом)"
            except Exception:
                volume_confirmed = "Недоступно ⚠️ (PVT не рассчитан)"

            # 5. FRACTALS (Уровни для SL/TP)
            recent_lows = float(df['low'].iloc[-10:].min())
            recent_highs = float(df['high'].iloc[-10:].max())
            
            risk = current_price - recent_lows
            reward = recent_highs - current_price
            rr_ratio = round(reward / risk, 2) if risk > 0 else 0.0
            rr_status = "Выгодный (≥ 1:2) ✅" if rr_ratio >= 2.0 else "Стандартный (< 1:2) ⚠️"

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
            logging.error(f"Критическая ошибка в TA Engine: {e}")
            return {"error": str(e)}
