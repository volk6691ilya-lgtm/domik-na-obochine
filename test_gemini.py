import os
import requests

def main():
    print("🧠 Тест Google Gemini API (модель 3.1 Pro Preview)...")
    
    # 1. Получаем и очищаем ключ
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise Exception("❌ Ключ Gemini не найден в Secrets GitHub!")
    
    api_key = api_key.strip()
    
    # 2. ИСПРАВЛЕНИЕ: Используем модель, которую требует Google для новых ключей
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro-preview:generateContent?key={api_key}"
    
    # 3. Создаем запрос
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "Кратко опиши, что такое Биткоин, в одном предложении, как финансовый аналитик."}
                ]
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print("📤 Отправка запроса в Gemini...")
    
    # 4. Отправляем запрос
    response = requests.post(url, json=payload, headers=headers, timeout=15)
    
    # 5. Обрабатываем ответ
    if response.status_code == 200:
        data = response.json()
        text = data['candidates'][0]['content']['parts'][0]['text']
        print(f"✅ УСПЕХ! Ответ от Gemini:\n{text}")
    else:
        print(f"❌ ОШИБКА API! Код: {response.status_code}")
        print(f"Детали: {response.text}")
        raise Exception("Не удалось получить ответ от Gemini")

if __name__ == "__main__":
    main()
