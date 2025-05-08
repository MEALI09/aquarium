import os
import random
import threading
import asyncio
import logging
import time
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Состояние аквариума
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
    """Функция для автономного изменения температуры"""
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


# Flask API
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


# Telegram Bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🌡 Температура", callback_data='status')],
        [InlineKeyboardButton("💡 Свет", callback_data='light')],
        [InlineKeyboardButton("⚠️ Протечка", callback_data='leak')],
    ]
    await update.message.reply_text(
        "🤖 Управление аквариумом:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'status':
        text = (f"🌡 Вода: {aquarium_state['temp_water']}°C\n"
                f"🌡 Воздух: {aquarium_state['temp_air']}°C\n"
                f"⏱ Обновлено: {aquarium_state['last_update']}")
    elif query.data == 'light':
        text = f"💡 Свет: {'ВКЛ' if aquarium_state['light_on'] else 'ВЫКЛ'}"
    elif query.data == 'leak':
        text = f"⚠️ Протечка: {'ДА' if aquarium_state['water_leak'] else 'НЕТ'}"

    await query.edit_message_text(text)


def run_bot():
    """Запуск бота в отдельном потоке с собственным event loop"""

    def start_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        token = os.getenv('TELEGRAM_TOKEN')
        if not token:
            logger.error("Токен Telegram бота не найден!")
            return

        try:
            application = ApplicationBuilder().token(token).build()
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CallbackQueryHandler(button_handler))

            logger.info("Бот запущен")
            loop.run_until_complete(application.run_polling())
        except Exception as e:
            logger.error(f"Ошибка в боте: {e}", exc_info=True)
        finally:
            loop.close()

    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()


def run_flask():
    """Запуск Flask сервера"""
    app.run(host='0.0.0.0', port=5000, use_reloader=False)


if __name__ == '__main__':
    # Запуск симуляции температуры
    threading.Thread(target=simulate_temperature, daemon=True).start()

    # Запуск Telegram бота
    run_bot()

    # Запуск Flask сервера в основном потоке
    run_flask()
