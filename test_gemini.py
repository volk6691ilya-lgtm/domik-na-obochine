import os
import google.generativeai as genai

def main():
    print(" Тест Google Gemini API...")
    
    # Получаем ключ из секретов GitHub
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        raise Exception("❌ Ключ Gemini не найден в Secrets GitHub!")
    
    # Настраиваем Gemini
    genai.configure(api_key=api_key)
    
    # Выбираем модель (Gemini 1.5 Flash - быстрая и бесплатная)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Отправляем простой запрос
    print(" Отправка запроса в Gemini...")
    response = model.generate_content("Кратко опиши, что такое Биткоин, в одном предложении.")
    
    print(f"✅ Ответ от Gemini: {response.text}")

if __name__ == "__main__":
    main()
