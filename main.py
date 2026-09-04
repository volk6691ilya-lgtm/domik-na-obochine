import os
import requests
import json

def main():
    print("🔥 Ember Watch: Запуск системы...")
    
    # 1. Получаем секреты из настроек GitHub
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    if not bot_token or not channel_id:
        raise Exception("❌ Ошибка: Токен бота или ID канала не найдены в Secrets GitHub!")

    # 2. Получаем курс Биткоина с бесплатного API CoinGecko
    print("📡 Сканирование рынка...")
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url, timeout=10)
        data = response.json()
        btc_price = data['bitcoin']['usd']
        btc_change = data['bitcoin']['usd_24h_change']
        market_msg = f"💰 BTC: ${btc_price:,.2f} ({btc_change:+.2f}% за 24ч)"
    except Exception as e:
        market_msg = f"⚠️ Не удалось получить данные рынка: {str(e)}"

    # 3. Формируем сообщение
    final_message = f"🔥 *Ember Watch: Система на связи*\n\n{market_msg}\n\n_Тестовый импульс прошел успешно._"

    # 4. Отправляем в Telegram
    print("📤 Отправка отчета в Telegram...")
    tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": channel_id,
        "text": final_message,
        "parse_mode": "Markdown"
    }
    
    response = requests.post(tg_url, json=payload, timeout=10)
    
    if response.status_code == 200:
        print("✅ Успешно отправлено в Telegram!")
    else:
        print(f"❌ Ошибка Telegram API: {response.text}")

if __name__ == "__main__":
    main()
