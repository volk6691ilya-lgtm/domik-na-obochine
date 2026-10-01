import pandas as pd
import mplfinance as mpf
import numpy as np
import logging
import os
import warnings

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

    def generate_signal_chart(self, df, symbol, ta_data, filename="signal_chart.png"):
        try:
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            # Поддержка и новых ключей (sl, tp, entry), и старых для совместимости
            sl_level = ta_data.get("sl") or ta_data.get("support_level (SL)")
            tp_level = ta_data.get("tp") or ta_data.get("resistance_level (TP)")
            entry_level = ta_data.get("entry", ta_data.get("price", "N/A"))

            # Определяем направление для расчёта TP1/TP2/TP3
            is_long = "Бычий" in ta_data.get('trend', '')

            # Рассчитываем TP1, TP2, TP3 (как в signal_generator.py)
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

            # 1. Стоп-лосс (Зеленый) — пунктир
            if sl_level:
                hlines.append(float(sl_level))
                hlines_colors.append('lime')
                hlines_styles.append('--')

            # 2. Точка входа (Синий) — сплошная
            if entry_level and entry_level != "N/A":
                entry_float = float(entry_level)
                if entry_float not in hlines:
                    hlines.append(entry_float)
                    hlines_colors.append('dodgerblue')
                    hlines_styles.append('-')

            # 3. TP1 (Оранжевый) — точки (40% движения)
            if tp1 is not None and tp1 not in hlines:
                hlines.append(tp1)
                hlines_colors.append('orange')
                hlines_styles.append(':')

            # 4. TP2 (Оранжево-красный) — точки (70% движения)
            if tp2 is not None and tp2 not in hlines:
                hlines.append(tp2)
                hlines_colors.append('orangered')
                hlines_styles.append(':')

            # 5. TP3 (Красный) — пунктир (100% движения)
            if tp3 is not None and tp3 not in hlines:
                hlines.append(tp3)
                hlines_colors.append('red')
                hlines_styles.append('--')

            # Настройки стиля графика (похож на TradingView)
            mc = mpf.make_marketcolors(up='g', down='r', edge='i', wick='i', volume='in', inherit=True)
            s = mpf.make_mpf_style(marketcolors=mc, base_mpf_style='charles')

            # Обновленный заголовок с TP1/TP2/TP3
            title = f"{symbol} | Entry: ${entry_level} | SL: ${sl_level} | TP1: ${tp1} | TP2: ${tp2} | TP3: ${tp3}"
            filepath = os.path.join(self.output_dir, filename)

            # ГЕНЕРАЦИЯ ГРАФИКА
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

            logging.info(f"График успешно сохранен: {filepath}")
            return filepath

        except Exception as e:
            logging.error(f"Ошибка при генерации графика: {e}")
            return None


# Блок для локального тестирования
if __name__ == "__main__":
    print("\n--- Тест Chart Visualizer (Генерация графика с Entry, SL, TP1/TP2/TP3) ---")

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

    # Тестовые данные
    mock_ta_data = {
        "price": 98.50,
        "entry": 98.00,
        "sl": 95.00,
        "tp": 105.00,
        "trend": "Бычий 🟢 (Цена > EMA50)",
        "estimated_R:R": "1 : 2.5"
    }

    visualizer = ChartVisualizer()
    filepath = visualizer.generate_signal_chart(df, "TESTUSDT", mock_ta_data, "test_chart.png")

    if filepath:
        print(f"\n✅ УСПЕХ! График сохранен по пути: {os.path.abspath(filepath)}")
        print("👉 На графике 5 линий:")
        print("   🟢 SL (зелёный пунктир)")
        print("   🔵 Entry (синяя сплошная)")
        print("   🟠 TP1 (оранжевый пунктир) — 40%")
        print("   🟠 TP2 (оранжево-красный пунктир) — 70%")
        print("   🔴 TP3 (красный пунктир) — 100%")
    else:
        print("\n❌ Ошибка при создании графика.")

    print("\n--- Тест завершен ---\n")
