import os
import requests

def main():
    print("🧠 Тест OpenRouter API (Бесплатный и стабильный)...")
    
    # 1. Получаем новый ключ
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("❌ Ключ OPENROUTER_API_KEY не найден в Secrets!")
    
    api_key = api_key.strip()
    
    # 2. URL OpenRouter API
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    # 3. Выбираем мощную бесплатную модель (Gemini 2.0 Flash через OpenRouter)
    # Суффикс :free гарантирует, что мы используем бесплатный тариф
    model = "google/gemini-2.0-flash-exp:free"
    
    # 4. Формируем запрос в формате OpenAI (стандарт для OpenRouter)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "Кратко опиши, что такое Биткоин, в одном предложении, как финансовый аналитик."
            }
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/volk6691ilya-lgtm/ember-watch",
        "X-Title": "Ember Watch System"
    }
    
    print(f"📤 Отправка запроса в модель: {model}")
    
    # 5. Отправляем запрос
    response = requests.post(url, json=payload, headers=headers, timeout=15)
    
    # 6. Обрабатываем ответ
    if response.status_code == 200:
        data = response.json()
        text = data['choices'][0]['message']['content']
        print(f"✅ УСПЕХ! Ответ от ИИ:\n{text}")
    else:
        print(f"❌ ОШИБКА API! Код: {response.status_code}")
        print(f"Детали: {response.text}")
        raise Exception("Не удалось получить ответ от ИИ")

if __name__ == "__main__":
    main()
