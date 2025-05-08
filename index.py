from flask import Flask, jsonify
import random
from datetime import datetime
import time
from threading import Thread
from flask_cors import CORS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
import asyncio
import logging
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)
CORS(app)

# Общее состояние аквариума
aquarium_state = {
    'temp_water': 24.5,
    'temp_air': 22.0,
    'water_leak': False,
    'light_on': False,
    'last_update': datetime.now().isoformat()
}

# История температур
temp_history = {
    'water': [],
    'air': [],
    'labels': []
}

def simulate_temperature():
    """Функция симуляции температуры (запускается в отдельном потоке)"""
    while True:
        now = datetime.now()
        hour = now.hour
        
        if 6 <= hour < 18:  # День
            water_base = 24.5 + random.uniform(-0.5, 0.5)
            air_base = 22.0 + random.uniform(-0.5, 0.5)
        else:  # Ночь
            water_base = 23.0 + random.uniform(-0.3, 0.3)
            air_base = 21.0 + random.uniform(-0.3, 0.3)

        aquarium_state['temp_water'] = round(aquarium_state['temp_water'] * 0.9 + water_base * 0.1, 1)
        aquarium_state['temp_air'] = round(aquarium_state['temp_air'] * 0.9 + air_base * 0.1, 1)
        aquarium_state['last_update'] = now.isoformat()

        if now.minute % 10 == 0:
            temp_history['water'].append(aquarium_state['temp_water'])
            temp_history['air'].append(aquarium_state['temp_air'])
            temp_history['labels'].append(now.strftime('%H:%M'))
            
            if len(temp_history['water']) > 144:
                temp_history['water'].pop(0)
                temp_history['air'].pop(0)
                temp_history['labels'].pop(0)

        time.sleep(60)

# ===== Flask API =====
@app.route('/api/status')
def get_status():
    return jsonify(aquarium_state)

@app.route('/api/history')
def get_history():
    return jsonify(temp_history)

@app.route('/api/light/toggle', methods=['POST'])
def toggle_light():
    aquarium_state['light_on'] = not aquarium_state['light_on']
    aquarium_state['last_update'] = datetime.now().isoformat()
    return jsonify({'status': 'success'})

@app.route('/api/leak/toggle', methods=['POST'])
def toggle_leak():
    aquarium_state['water_leak'] = not aquarium_state['water_leak']
    aquarium_state['last_update'] = datetime.now().isoformat()
    return jsonify({'status': 'success'})

# ===== Telegram Bot =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🌡 Температура", callback_data='temp')],
        [InlineKeyboardButton("💡 Свет", callback_data='light')],
        [InlineKeyboardButton("⚠️ Протечка", callback_data='leak')]
    ]
    await update.message.reply_text(
        "Управление аквариумом:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'temp':
        msg = f"🌡 Вода: {aquarium_state['temp_water']}°C\n🌡 Воздух: {aquarium_state['temp_air']}°C"
    elif query.data == 'light':
        msg = "💡 Свет: " + ("ВКЛ" if aquarium_state['light_on'] else "ВЫКЛ")
    elif query.data == 'leak':
        msg = "⚠️ Протечка: " + ("ЕСТЬ" if aquarium_state['water_leak'] else "НЕТ")
    
    await query.edit_message_text(msg)

def run_bot():
    """Запуск бота в отдельном потоке"""
    token = os.getenv('TELEGRAM_TOKEN')
    application = ApplicationBuilder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    application.run_polling()

# ===== Главный запуск =====
if __name__ == '__main__':
    # Запуск симуляции температуры
    Thread(target=simulate_temperature, daemon=True).start()
    
    # Запуск Telegram бота
    Thread(target=run_bot, daemon=True).start()
    
    # Запуск Flask сервера
    app.run(host='0.0.0.0', port=5000)
