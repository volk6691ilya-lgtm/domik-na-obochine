import pandas as pd
import mplfinance as mpf
import numpy as np
import logging
import os
import warnings
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.font_manager')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ChartVisualizer:
    """
    Модуль для генерации профессиональных графиков с разметкой уровней.
    Генерирует 4 картинки: основная + MACD + RSI/StochRSI + Williams %R
    """

    def __init__(self, output_dir="charts"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_signal_chart(self, df, symbol, ta_data, filename="signal_chart.png"):
        """Основной график с Bollinger Bands и уровнями"""
        try:
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            sl_level = ta_data.get("sl") or ta_data.get("support_level (SL)")
            tp_level = ta_data.get("tp") or ta_data.get("resistance_level (TP)")
            entry_level = ta_data.get("entry", ta_data.get("price", "N/A"))

            is_long = "Бычий" in ta_data.get('trend', '')

            tp1 = None
            tp2 = None
            tp3 = None

            if entry_level != "N/A" and tp_level:
                entry_float = float(entry_level)
                tp_float = float(tp_level)

                if is_long:
                    tp1 = round(entry_float + (tp_float - entry_float) * 0.4, 4)
                    tp2 = round(entry_float + (tp_float - entry_float) * 0.7, 4)
                    tp3 = tp_float
                else:
                    tp1 = round(entry_float - (entry_float - tp_float) * 0.4, 4)
                    tp2 = round(entry_float - (entry_float - tp_float) * 0.7, 4)
                    tp3 = tp_float

            hlines = []
            hlines_colors = []
            hlines_styles = []

            if sl_level:
                hlines.append(float(sl_level))
                hlines_colors.append('lime')
                hlines_styles.append('--')

            if entry_level and entry_level != "N/A":
                entry_float = float(entry_level)
                if entry_float not in hlines:
                    hlines.append(entry_float)
                    hlines_colors.append('dodgerblue')
                    hlines_styles.append('-')

            if tp1 is not None and tp1 not in hlines:
                hlines.append(tp1)
                hlines_colors.append('orange')
                hlines_styles.append(':')

            if tp2 is not None and tp2 not in hlines:
                hlines.append(tp2)
                hlines_colors.append('orangered')
                hlines_styles.append(':')

            if tp3 is not None and tp3 not in hlines:
                hlines.append(tp3)
                hlines_colors.append('red')
                hlines_styles.append('--')

            # Добавляем Bollinger Bands
            if 'boll_upper' in ta_data and 'boll_middle' in ta_data and 'boll_lower' in ta_data:
                hlines.extend([ta_data['boll_upper'], ta_data['boll_middle'], ta_data['boll_lower']])
                hlines_colors.extend(['gray', 'gray', 'gray'])
                hlines_styles.extend(['-.', '-.', '-.'])

            mc = mpf.make_marketcolors(up='g', down='r', edge='i', wick='i', volume='in', inherit=True)
            s = mpf.make_mpf_style(marketcolors=mc, base_mpf_style='charles')

            title = f"{symbol} | Entry: ${entry_level} | SL: ${sl_level} | TP1: ${tp1} | TP2: ${tp2} | TP3: ${tp3}"
            filepath = os.path.join(self.output_dir, filename)

            mpf.plot(
                df,
                type='candle',
                style=s,
                title=title,
                ylabel='Price (USDT)',
                volume=True,
                ylabel_lower='Volume',
                hlines=dict(hlines=hlines, colors=hlines_colors, linestyle=hlines_styles),
                savefig=filepath,
                figratio=(10, 6),
                figscale=1.2
            )

            logging.info(f"Основной график успешно сохранен: {filepath}")
            return filepath

        except Exception as e:
            logging.error(f"Ошибка при генерации основного графика: {e}")
            return None

    def generate_macd_chart(self, df, symbol, ta_data, filename="macd_chart.png"):
        """График MACD с гистограммой"""
        try:
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            import ta
            macd_indicator = ta.trend.MACD(
                close=df['close'], window_slow=26, window_fast=12, window_sign=9
            )
            macd_line = macd_indicator.macd()
            signal_line = macd_indicator.macd_signal()
            histogram = macd_indicator.macd_diff()

            fig, ax = plt.subplots(figsize=(10, 4))
            
            ax.plot(df.index, macd_line, label='MACD Line', color='blue', linewidth=1.5)
            ax.plot(df.index, signal_line, label='Signal Line', color='orange', linewidth=1.5)
            
            colors = ['green' if val >= 0 else 'red' for val in histogram]
            ax.bar(df.index, histogram, color=colors, alpha=0.5, width=0.02)
            
            ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
            
            ax.set_title(f'{symbol} - MACD (12, 26, 9)', fontsize=12, fontweight='bold')
            ax.set_ylabel('MACD Value')
            ax.legend(loc='upper left')
            ax.grid(True, alpha=0.3)
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            filepath = os.path.join(self.output_dir, filename)
            plt.savefig(filepath, dpi=100, bbox_inches='tight')
            plt.close()
            
            logging.info(f"MACD график успешно сохранен: {filepath}")
            return filepath

        except Exception as e:
            logging.error(f"Ошибка при генерации MACD графика: {e}")
            return None

    def generate_rsi_chart(self, df, symbol, ta_data, filename="rsi_chart.png"):
        """График RSI + StochRSI"""
        try:
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            import ta
            rsi_indicator = ta.momentum.RSIIndicator(close=df['close'], window=14)
            rsi = rsi_indicator.rsi()
            
            stoch_rsi_indicator = ta.momentum.StochRSIIndicator(
                close=df['close'], window=14, smooth1=3, smooth2=3
            )
            stoch_k = stoch_rsi_indicator.stochrsi_k()
            stoch_d = stoch_rsi_indicator.stochrsi_d()

            fig, ax = plt.subplots(figsize=(10, 4))
            
            ax.plot(df.index, rsi, label='RSI (14)', color='blue', linewidth=1.5)
            ax.plot(df.index, stoch_k, label='StochRSI K', color='green', linewidth=1.2, alpha=0.7)
            ax.plot(df.index, stoch_d, label='StochRSI D', color='red', linewidth=1.2, alpha=0.7)
            
            ax.axhline(y=70, color='red', linestyle='--', linewidth=0.8, label='Overbought (70)')
            ax.axhline(y=30, color='green', linestyle='--', linewidth=0.8, label='Oversold (30)')
            ax.axhline(y=50, color='gray', linestyle='-', linewidth=0.5)
            
            ax.set_title(f'{symbol} - RSI & StochRSI', fontsize=12, fontweight='bold')
            ax.set_ylabel('Value')
            ax.set_ylim(0, 100)
            ax.legend(loc='upper left', fontsize=8)
            ax.grid(True, alpha=0.3)
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            filepath = os.path.join(self.output_dir, filename)
            plt.savefig(filepath, dpi=100, bbox_inches='tight')
            plt.close()
            
            logging.info(f"RSI график успешно сохранен: {filepath}")
            return filepath

        except Exception as e:
            logging.error(f"Ошибка при генерации RSI графика: {e}")
            return None

    def generate_wr_chart(self, df, symbol, ta_data, filename="wr_chart.png"):
        """График Williams %R (WR14 и WR21)"""
        try:
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            import ta
            wr14_indicator = ta.momentum.WilliamsRIndicator(
                high=df['high'], low=df['low'], close=df['close'], lbp=14
            )
            wr14 = wr14_indicator.williams_r()
            
            wr21_indicator = ta.momentum.WilliamsRIndicator(
                high=df['high'], low=df['low'], close=df['close'], lbp=21
            )
            wr21 = wr21_indicator.williams_r()

            fig, ax = plt.subplots(figsize=(10, 4))
            
            ax.plot(df.index, wr14, label='WR14', color='blue', linewidth=1.5)
            ax.plot(df.index, wr21, label='WR21', color='orange', linewidth=1.5)
            
            ax.axhline(y=-20, color='red', linestyle='--', linewidth=0.8, label='Overbought (-20)')
            ax.axhline(y=-80, color='green', linestyle='--', linewidth=0.8, label='Oversold (-80)')
            ax.axhline(y=-50, color='gray', linestyle='-', linewidth=0.5)
            
            ax.set_title(f'{symbol} - Williams %R', fontsize=12, fontweight='bold')
            ax.set_ylabel('Value')
            ax.set_ylim(-100, 0)
            ax.legend(loc='upper left', fontsize=8)
            ax.grid(True, alpha=0.3)
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            filepath = os.path.join(self.output_dir, filename)
            plt.savefig(filepath, dpi=100, bbox_inches='tight')
            plt.close()
            
            logging.info(f"Williams %R график успешно сохранен: {filepath}")
            return filepath

        except Exception as e:
            logging.error(f"Ошибка при генерации Williams %R графика: {e}")
            return None

    def generate_all_charts(self, df, symbol, ta_data):
        """Генерирует все 4 графика и возвращает список путей"""
        charts = []
        
        main_chart = self.generate_signal_chart(df, symbol, ta_data, f"signal_{symbol}_main.png")
        if main_chart:
            charts.append(main_chart)
        
        macd_chart = self.generate_macd_chart(df, symbol, ta_data, f"signal_{symbol}_macd.png")
        if macd_chart:
            charts.append(macd_chart)
        
        rsi_chart = self.generate_rsi_chart(df, symbol, ta_data, f"signal_{symbol}_rsi.png")
        if rsi_chart:
            charts.append(rsi_chart)
        
        wr_chart = self.generate_wr_chart(df, symbol, ta_data, f"signal_{symbol}_wr.png")
        if wr_chart:
            charts.append(wr_chart)
        
        return charts

if __name__ == "__main__":
    print("\n--- Тест Chart Visualizer (Генерация 4 графиков) ---")

    np.random.seed(42)
    dates = pd.date_range(end='2026-10-14', periods=96, freq='1h')
    closes = np.cumsum(np.random.randn(96)) + 100
    opens = closes + np.random.randn(96) * 0.5
    highs = np.maximum(opens, closes) + np.random.rand(96) * 1.0
    lows = np.minimum(opens, closes) - np.random.rand(96) * 1.0
    volumes = np.random.randint(1000, 5000, 96)

    df = pd.DataFrame({
        'open': opens, 'high': highs, 'low': lows, 'close': closes, 'volume': volumes
    }, index=dates)

    mock_ta_data = {
        "price": 98.50,
        "entry": 98.00,
        "sl": 95.00,
        "tp": 105.00,
        "trend": "Бычий 🟢 (Цена > EMA50)",
        "estimated_R:R": "1 : 2.5",
        "boll_upper": 102.00,
        "boll_middle": 98.00,
        "boll_lower": 94.00
    }

    visualizer = ChartVisualizer()
    
    print("Генерация всех графиков...")
    charts = visualizer.generate_all_charts(df, "TESTUSDT", mock_ta_data)
    
    if charts:
        print(f"\n✅ УСПЕХ! Сгенерировано {len(charts)} графиков:")
        for chart in charts:
            print(f"    {os.path.abspath(chart)}")
    else:
        print("\n❌ Ошибка при создании графиков.")

    print("\n--- Тест завершен ---\n")
