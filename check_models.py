import os
import requests

def main():
    print("🔍 Диагностика ключа Gemini...")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise Exception("❌ Ключ GEMINI_API_KEY не найден в Secrets!")
    
    # Критически важно: убираем скрытые пробелы и переносы строк
    api_key = api_key.strip()
    
    # Запрашиваем список доступных моделей для этого ключа
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    print("📤 Отправка запроса на проверку ключа...")
    response = requests.get(url, timeout=10)
    
    if response.status_code == 200:
        print("✅ Ключ действителен! Доступные модели:")
        data = response.json()
        found_models = []
        for model in data.get('models', []):
            name = model['name']
            if 'flash' in name or 'pro' in name:
                found_models.append(name)
                print(f"   ➔ {name}")
        
        if not found_models:
            print("⚠️ Модели flash или pro не найдены. Возможно, ограничения проекта.")
    else:
        print(f"❌ ОШИБКА! Код: {response.status_code}")
        print(f"Детали от Google: {response.text}")
        print("\n💡 ЧАСТЫЕ ПРИЧИНЫ:")
        print("1. Ключ скопирован с лишним пробелом или невидимым символом.")
        print("2. Ключ создан не на сайте aistudio.google.com")
        print("3. Нужно создать НОВЫЙ ключ в новом проекте.")

if __name__ == "__main__":
    main()
