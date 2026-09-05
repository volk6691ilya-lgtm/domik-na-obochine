import os
import requests

def main():
    print("🔍 Получаем список бесплатных моделей от OpenRouter...\n")
    
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("❌ Ключ OPENROUTER_API_KEY не найден в Secrets!")
    
    api_key = api_key.strip()
    
    # Запрашиваем список всех моделей
    url = "https://openrouter.ai/api/v1/models"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    print("📤 Запрос списка моделей...")
    response = requests.get(url, headers=headers, timeout=15)
    
    if response.status_code == 200:
        data = response.json()
        models = data.get('data', [])
        
        print(f"\n✅ Получено {len(models)} моделей. Фильтруем бесплатные...\n")
        print("=" * 70)
        
        free_models = []
        for model in models:
            model_id = model.get('id', '')
            # Ищем модели с пометкой :free в названии
            if ':free' in model_id.lower():
                name = model.get('name', 'Unknown')
                context_length = model.get('context_length', 'N/A')
                free_models.append({
                    'id': model_id,
                    'name': name,
                    'context': context_length
                })
        
        # Сортируем по имени
        free_models.sort(key=lambda x: x['name'])
        
        print(f"Найдено {len(free_models)} бесплатных моделей:\n")
        for i, model in enumerate(free_models[:20], 1):  # Показываем первые 20
            print(f"{i}. {model['name']}")
            print(f"   ID: {model['id']}")
            print(f"   Контекст: {model['context']} токенов\n")
        
        if len(free_models) > 20:
            print(f"... и ещё {len(free_models) - 20} моделей\n")
        
        print("=" * 70)
        print("\n💡 РЕКОМЕНДАЦИИ для финансового анализа:")
        print("   - google/gemini-flash-1.5:free (быстрая, умная)")
        print("   - meta-llama/llama-3-8b-instruct:free (стабильная)")
        print("   - mistralai/mistral-7b-instruct:free (хорошо пишет тексты)")
        
    else:
        print(f"❌ Ошибка! Код: {response.status_code}")
        print(f"Детали: {response.text}")

if __name__ == "__main__":
    main()
