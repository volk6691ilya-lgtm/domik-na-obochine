import pandas as pd
import mplfinance as mpf
import numpy as np
import logging
import os
import warnings

# Подавляем безвредные предупреждения о шрифтах matplotlib
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.font_manager')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ChartVisualizer:
    """
    Модуль для генерации профессиональных графиков с разметкой уровней.
    Использует библиотеку mplfinance (бесплатно, без API ключей).
    """

    def __init__(self, output_dir="charts"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_signal_chart(self, df: pd.DataFrame, symbol: str, ta_data: dict, filename: str = "signal_chart.png"):
        try:
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            support_level = ta_data.get("support_level (SL)")
            resistance_level = ta_data.get("resistance_level (TP)")

            hlines = []
            hlines_colors = []

            # Добавляем уровень поддержки (зеленый)
            if support_level:
                hlines.append(support_level)
                hlines_colors.append('green')

            # Добавляем уровень сопротивления (красный)
            if resistance_level:
                hlines.append(resistance_level)
                hlines_colors.append('red')

            # Настройки стиля графика (похож на TradingView)
            mc = mpf.make_marketcolors(up='g', down='r', edge='i', wick='i', volume='in', inherit=True)
            s = mpf.make_mpf_style(marketcolors=mc, base_mpf_style='charles')

            title = f"{symbol} | Цена: ${ta_data.get('price', 'N/A')} | R:R {ta_data.get('estimated_R:R', 'N/A')}"
            filepath = os.path.join(self.output_dir, filename)

            # ГЕНЕРАЦИЯ ГРАФИКА (Упрощенный и 100% рабочий вариант hlines)
            mpf.plot(
                df,
                type='candle',
                style=s,
                title=title,
                ylabel='Price (USDT)',
                volume=True,
                ylabel_lower='Volume',
                hlines=dict(hlines=hlines, colors=hlines_colors), # <-- Только линии и цвета
                savefig=filepath,
                figratio=(10, 6),
                figscale=1.2
            )

            logging.info(f"График успешно сохранен: {filepath}")
            return filepath

        except Exception as e:
            logging.error(f"Ошибка при генерации графика: {e}")
            return None

# Блок для локального тестирования
if __name__ == "__main__":
    print("\n--- Тест Chart Visualizer (Генерация графика) ---")
    
    np.random.seed(42)
    dates = pd.date_range(end='2026-09-28', periods=50, freq='1h')
    closes = np.cumsum(np.random.randn(50)) + 100
    opens = closes + np.random.randn(50) * 0.5
    highs = np.maximum(opens, closes) + np.random.rand(50) * 1.0
    lows = np.minimum(opens, closes) - np.random.rand(50) * 1.0
    volumes = np.random.randint(1000, 5000, 50)
    
    df = pd.DataFrame({
        'open': opens, 'high': highs, 'low': lows, 'close': closes, 'volume': volumes
    }, index=dates)

    mock_ta_data = {
        "price": 98.50,
        "estimated_R:R": "1 : 2.5",
        "support_level (SL)": 95.00,  
        "resistance_level (TP)": 105.00 
    }

    visualizer = ChartVisualizer()
    filepath = visualizer.generate_signal_chart(df, "TESTUSDT", mock_ta_data, "test_chart.png")
    
    if filepath:
        print(f"\n✅ УСПЕХ! График сохранен по пути: {os.path.abspath(filepath)}")
        print("👉 Открой эту картинку, чтобы увидеть свечи, объемы и цветные линии SL/TP!")
    else:
        print("\n❌ Ошибка при создании графика.")
        
    print("\n--- Тест завершен ---\n")
