import os
import requests

def main():
    print("🧠 Тест OpenRouter API с автоматическим переключением моделей...\n")
    
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("❌ Ключ OPENROUTER_API_KEY не найден в Secrets!")
    
    api_key = api_key.strip()
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    # Берем 3 разные бесплатные модели из твоего списка от РАЗНЫХ провайдеров
    models_to_try = [
        "minimax/minimax-m3:free",               # Огромный контекст, другой провайдер
        "nvidia/nemotron-3.5-lightning:free",    # Очень быстрая, другой провайдер
        "inclusionai/ling-3.0-flash-fin:free"    # Специально обучена для финансов!
    ]
    
    # Наш тестовый запрос
    payload = {
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
    
    # Перебираем модели, пока одна не сработает
    for model in models_to_try:
        print(f"📤 Пробуем модель: {model}")
        payload["model"] = model
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            text = data['choices'][0]['message']['content']
            print(f"\n✅ УСПЕХ! Модель {model} сработала идеально!")
            print(f"🤖 Ответ ИИ:\n{text}")
            return  # Всё получилось, выходим из функции
            
        elif response.status_code == 429:
            print(f"⚠️ Модель {model} перегружена (429). Пробуем следующую...\n")
        else:
            print(f"❌ Модель {model} вернула ошибку {response.status_code}. Пробуем следующую...\n")
            
    # Если ни одна не сработала
    raise Exception("Не удалось получить ответ ни от одной бесплатной модели. Попробуйте запустить воркфлоу еще раз через 2-3 минуты.")

if __name__ == "__main__":
    main()
