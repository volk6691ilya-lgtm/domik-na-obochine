import os
import requests

def main():
    print("🧠 Тест Google Gemini API (через прямой REST запрос)...")
    
    # 1. Получаем ключ
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise Exception("❌ Ключ Gemini не найден в Secrets GitHub!")
    
    # 2. Формируем прямой URL к API Google (версия v1beta, модель flash)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # 3. Создаем правильный JSON-запрос для Gemini
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
        # Извлекаем текст из вложенной структуры ответа Gemini
        text = data['candidates'][0]['content']['parts'][0]['text']
        print(f"✅ УСПЕХ! Ответ от Gemini:\n{text}")
    else:
        print(f"❌ ОШИБКА API! Код: {response.status_code}")
        print(f"Детали: {response.text}")
        raise Exception("Не удалось получить ответ от Gemini")

if __name__ == "__main__":
    main()
