import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ВАЖНО: Имя класса должно быть точно таким же, с большой буквы!
class PatternRecognizer:
    """
    Модуль для поиска графических паттернов и зон ликвидности.
    Использует математический поиск локальных экстремумов (пиков и впадин).
    """

    def __init__(self, lookback=20):
        self.lookback = lookback

    def _get_extrema(self, df):
        """Находит локальные максимумы и минимумы"""
        highs_idx = argrelextrema(df['high'].values, np.greater, order=2)[0]
        lows_idx = argrelextrema(df['low'].values, np.less, order=2)[0]
        
        highs = df.iloc[highs_idx][-self.lookback:]
        lows = df.iloc[lows_idx][-self.lookback:]
        
        return highs, lows

    def analyze_patterns(self, df: pd.DataFrame) -> dict:
        """Анализирует последние свечи на наличие паттернов и зон ликвидности"""
        try:
            current_price = float(df['close'].iloc[-1])
            highs, lows = self._get_extrema(df)
            
            patterns_detected = []
            liquidity_zones = []

            # 1. Поиск Двойного Дна (W-паттерн)
            if len(lows) >= 2:
                last_low = float(lows['low'].iloc[-1])
                prev_low = float(lows['low'].iloc[-2])
                if abs(last_low - prev_low) / prev_low < 0.015:
                    patterns_detected.append("Двойное Дно (Бычий разворот) 🟢")
                    liquidity_zones.append({
                        "type": "Сбор ликвидности (Long Stops)",
                        "price_level": round(last_low * 0.995, 4),
                        "action": "Ожидание ложного пробоя вниз и отскок"
                    })

            # 2. Поиск Двойной Вершины (M-паттерн)
            if len(highs) >= 2:
                last_high = float(highs['high'].iloc[-1])
                prev_high = float(highs['high'].iloc[-2])
                if abs(last_high - prev_high) / prev_high < 0.015:
                    patterns_detected.append("Двойная Вершина (Медвежий разворот) 🔴")
                    liquidity_zones.append({
                        "type": "Сбор ликвидности (Short Stops)",
                        "price_level": round(last_high * 1.005, 4),
                        "action": "Ожидание ложного пробоя вверх и разворот вниз"
                    })

            if not patterns_detected:
                patterns_detected.append("Четких фигур не обнаружено (Флэт или сложный тренд) ⚪")

            return {
                "patterns": patterns_detected,
                "liquidity_zones": liquidity_zones,
                "recent_high": float(highs['high'].iloc[-1]) if len(highs) > 0 else current_price,
                "recent_low": float(lows['low'].iloc[-1]) if len(lows) > 0 else current_price
            }

        except Exception as e:
            logging.error(f"Ошибка в Pattern Recognizer: {e}")
            return {"error": str(e)}
