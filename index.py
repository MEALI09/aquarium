from flask import Flask, jsonify
import random
from datetime import datetime
import time
from threading import Thread
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Разрешаем кросс-доменные запросы

# Состояние аквариума
aquarium_state = {
    'temp_water': 24.5,
    'temp_air': 22.0,
    'water_leak': False,
    'light_on': False,
    'last_update': datetime.now().isoformat()
}

# История температур (последние 24 часа)
temp_history = {
    'water': [],
    'air': [],
    'labels': []
}

def simulate_temperature():
    """Функция для реалистичной симуляции температуры"""
    while True:
        now = datetime.now()
        hour = now.hour
        
        # Дневные/ночные колебания
        if 6 <= hour < 18:  # День
            water_base = 24.5 + random.uniform(-0.5, 0.5)
            air_base = 22.0 + random.uniform(-0.5, 0.5)
        else:  # Ночь
            water_base = 23.0 + random.uniform(-0.3, 0.3)
            air_base = 21.0 + random.uniform(-0.3, 0.3)

        # Плавное изменение температуры
        aquarium_state['temp_water'] = round(aquarium_state['temp_water'] * 0.9 + water_base * 0.1, 1)
        aquarium_state['temp_air'] = round(aquarium_state['temp_air'] * 0.9 + air_base * 0.1, 1)
        aquarium_state['last_update'] = now.isoformat()

        # Запись в историю каждые 10 минут
        if now.minute % 10 == 0:
            temp_history['water'].append(aquarium_state['temp_water'])
            temp_history['air'].append(aquarium_state['temp_air'])
            temp_history['labels'].append(now.strftime('%H:%M'))
            
            # Ограничение истории 144 точками (24 часа)
            if len(temp_history['water']) > 144:
                temp_history['water'].pop(0)
                temp_history['air'].pop(0)
                temp_history['labels'].pop(0)

        time.sleep(60)  # Обновление каждую минуту

@app.route('/api/status')
def get_status():
    """Возвращает текущее состояние аквариума"""
    return jsonify(aquarium_state)

@app.route('/api/history')
def get_history():
    """Возвращает историю температур"""
    return jsonify(temp_history)

@app.route('/')
def serve_index():
    """Отдает статический HTML-интерфейс"""
    return app.send_static_file('index.html')

if __name__ == '__main__':
    # Запуск симуляции температуры в фоновом режиме
    Thread(target=simulate_temperature, daemon=True).start()
    
    # Запуск Flask-сервера
    app.run(host='0.0.0.0', port=5000, debug=True)
