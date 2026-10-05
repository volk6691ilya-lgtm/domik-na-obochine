import os
import requests
import time
from ai_models_config import ALL_MODELS

def test_model(model_name):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return "❌ Нет API ключа"
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Кратко: что такое RSI в трейдинге?"}],
        "max_tokens": 40
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=25)
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return "✅ РАБОТАЕТ"
            return "⚠️ Пустой ответ"
        elif response.status_code == 429:
            return "⏳ Rate Limit"
        elif response.status_code == 404:
            return "❌ Не найдена (404)"
        elif response.status_code == 402:
            return "💰 Платная"
        else:
            return f"❌ Ошибка {response.status_code}"
    except Exception as e:
        return f"❌ Сбой: {str(e)[:30]}"

def main():
    print("=" * 75)
    print("🧪 ЕДИНЫЙ ТЕСТ ВСЕХ ИИ-МОДЕЛЕЙ СИСТЕМЫ")
    print("=" * 75)
    
    working_models = []
    for i, model in enumerate(ALL_MODELS, 1):
        print(f"[{i:2d}/{len(ALL_MODELS)}] {model}")
        result = test_model(model)
        print(f"      Статус: {result}")
        
        if "✅ РАБОТАЕТ" in result:
            working_models.append(model)
            
        time.sleep(1.5) # Пауза, чтобы не получить бан по IP
        
    print("\n" + "=" * 75)
    print(f"📊 ИТОГ: Работает {len(working_models)} из {len(ALL_MODELS)} моделей")
    
    if working_models:
        print("\n🎯 АКТУАЛЬНЫЙ РАБОЧИЙ СПИСОК (скопируй его в ai_models_config.py):")
        for m in working_models:
            print(f'    "{m}",')
    print("=" * 75)

if __name__ == "__main__":
    main()
