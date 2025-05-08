import os
import logging
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters, CallbackQueryHandler,
    ConversationHandler
)
from dotenv import load_dotenv
import json
import requests

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы состояний
SET_TEMP_WATER, SET_TEMP_AIR, SET_WATER_LEAK = range(3)

# Получение конфигурации из переменных окружения
TELEGRAM_TOKEN = os.getenv('Your_Token')
WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://meali09.github.io/aquarium/')
GITHUB_TOKEN = os.getenv('Your_Token')
GITHUB_REPO = os.getenv('GITHUB_REPO', 'meali09/aquarium')
DATA_FILE_PATH = os.getenv('DATA_FILE_PATH', 'data/status.json')

# Параметры аквариума
aquarium_params = {
    'auto_temp_water': 24.5,
    'auto_temp_air': 22.0,
    'auto_water_leak': 0,
    'manual_temp_water': None,
    'manual_temp_air': None,
    'manual_water_leak': None,
    'light_on': False,
    'feeding_time': '12:00',
    'ph_level': 7.0,
    'filter_on': True,
    'water_level': 'normal'
}

# --- Вспомогательные функции ---

def update_github_data():
    """Обновляет данные на GitHub через API"""
    if not all([GITHUB_TOKEN, GITHUB_REPO]):
        logger.warning("GitHub credentials not configured, skipping update")
        return

    current = get_current_values()
    data = {
        'temp_water': current['temp_water'],
        'temp_air': current['temp_air'],
        'water_leak': current['water_leak'],
        'light_on': current['light_on'],
        'feeding_time': current['feeding_time'],
        'ph_level': current['ph_level'],
        'filter_on': current['filter_on'],
        'water_level': current['water_level'],
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        # Получаем текущий файл для получения SHA
        response = requests.get(url, headers=headers)
        sha = response.json().get('sha') if response.status_code == 200 else None

        # Обновляем файл
        payload = {
            "message": "Update aquarium status",
            "content": json.dumps(data, indent=2).encode('base64').decode('utf-8'),
            "sha": sha
        }

        response = requests.put(url, headers=headers, json=payload)
        if response.status_code == 200:
            logger.info("Data successfully updated on GitHub")
        else:
            logger.error(f"Failed to update GitHub data: {response.text}")
    except Exception as e:
        logger.error(f"Error updating GitHub data: {str(e)}")

def update_sensor_values():
    """Обновляет значения сенсоров случайным образом"""
    aquarium_params['auto_temp_water'] = round(24.0 + random.uniform(-0.5, 0.5), 1)
    aquarium_params['auto_temp_air'] = round(22.0 + random.uniform(-1, 1), 1)
    aquarium_params['auto_water_leak'] = 1 if random.random() < 0.01 else 0
    update_github_data()

def get_current_values():
    """Возвращает текущие значения параметров"""
    return {
        'temp_water': aquarium_params['manual_temp_water'] or aquarium_params['auto_temp_water'],
        'temp_air': aquarium_params['manual_temp_air'] or aquarium_params['auto_temp_air'],
        'water_leak': aquarium_params['manual_water_leak'] or aquarium_params['auto_water_leak'],
        'light_on': aquarium_params['light_on'],
        'feeding_time': aquarium_params['feeding_time'],
        'ph_level': aquarium_params['ph_level'],
        'filter_on': aquarium_params['filter_on'],
        'water_level': aquarium_params['water_level']
    }

def get_main_keyboard():
    """Создает основную клавиатуру"""
    keyboard = [
        [InlineKeyboardButton("🌡️ Температура воды", callback_data='temp_water'),
         InlineKeyboardButton("🌡️ Температура воздуха", callback_data='temp_air')],
        [InlineKeyboardButton("⚠️ Протечка воды", callback_data='water_leak')],
        [InlineKeyboardButton("💡 Освещение", callback_data='light')],
        [InlineKeyboardButton("📊 Статус системы", callback_data='status')],
        [InlineKeyboardButton("🔄 Обновить данные", callback_data='refresh')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_light_keyboard():
    """Создает клавиатуру управления освещением"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💡 Включить", callback_data='light_on'),
         InlineKeyboardButton("🔌 Выключить", callback_data='light_off')],
        [InlineKeyboardButton("↩️ Назад", callback_data='back')]
    ])

# --- Обработчики ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text("Добро пожаловать в умный аквариум!", reply_markup=get_main_keyboard())

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отображает текущий статус системы"""
    values = get_current_values()
    text = (
        f"📊 Статус системы:\n"
        f"🌡️ Температура воды: {values['temp_water']}°C\n"
        f"🌡️ Температура воздуха: {values['temp_air']}°C\n"
        f"⚠️ Протечка воды: {'Да' if values['water_leak'] else 'Нет'}\n"
        f"💡 Освещение: {'Вкл' if values['light_on'] else 'Выкл'}\n"
        f"🕒 Кормление: {values['feeding_time']}\n"
        f"🌊 Уровень воды: {values['water_level']}\n"
        f"🧪 pH уровень: {values['ph_level']}\n"
        f"🌀 Фильтр: {'Работает' if values['filter_on'] else 'Отключен'}"
    )
    await update.message.reply_text(text, reply_markup=get_main_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'temp_water':
        await query.edit_message_text("Введите температуру воды (15–35°C):")
        return SET_TEMP_WATER
    elif data == 'temp_air':
        await query.edit_message_text("Введите температуру воздуха (10–35°C):")
        return SET_TEMP_AIR
    elif data == 'water_leak':
        await query.edit_message_text("Введите уровень протечки (0 или 1):")
        return SET_WATER_LEAK
    elif data == 'light':
        await query.edit_message_text("Управление освещением:", reply_markup=get_light_keyboard())
    elif data == 'light_on':
        aquarium_params['light_on'] = True
        update_github_data()
        await query.edit_message_text("Освещение включено", reply_markup=get_light_keyboard())
    elif data == 'light_off':
        aquarium_params['light_on'] = False
        update_github_data()
        await query.edit_message_text("Освещение выключено", reply_markup=get_light_keyboard())
    elif data == 'status':
        await status(update, context)
    elif data == 'refresh':
        update_sensor_values()
        await query.edit_message_text("🔄 Данные обновлены", reply_markup=get_main_keyboard())
    elif data == 'back':
        await query.edit_message_text("Главное меню:", reply_markup=get_main_keyboard())

async def set_temp_water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Устанавливает температуру воды"""
    try:
        temp = float(update.message.text)
        if 15 <= temp <= 35:
            aquarium_params['manual_temp_water'] = temp
            update_github_data()
            await update.message.reply_text(f"Температура воды установлена на {temp}°C", reply_markup=get_main_keyboard())
            return ConversationHandler.END
        else:
            await update.message.reply_text("Температура должна быть от 15 до 35°C:")
            return SET_TEMP_WATER
    except ValueError:
        await update.message.reply_text("Введите число, например 25.0:")
        return SET_TEMP_WATER

async def set_temp_air(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Устанавливает температуру воздуха"""
    try:
        temp = float(update.message.text)
        if 10 <= temp <= 35:
            aquarium_params['manual_temp_air'] = temp
            update_github_data()
            await update.message.reply_text(f"Температура воздуха установлена на {temp}°C", reply_markup=get_main_keyboard())
            return ConversationHandler.END
        else:
            await update.message.reply_text("Температура должна быть от 10 до 35°C:")
            return SET_TEMP_AIR
    except ValueError:
        await update.message.reply_text("Введите число, например 22.5:")
        return SET_TEMP_AIR

async def set_water_leak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Устанавливает статус протечки воды"""
    try:
        leak = int(update.message.text)
        if leak in (0, 1):
            aquarium_params['manual_water_leak'] = leak
            update_github_data()
            await update.message.reply_text(f"Протечка установлена: {'Да' if leak else 'Нет'}", reply_markup=get_main_keyboard())
            return ConversationHandler.END
        else:
            await update.message.reply_text("Введите 0 (нет) или 1 (есть):")
            return SET_WATER_LEAK
    except ValueError:
        await update.message.reply_text("Введите 0 или 1:")
        return SET_WATER_LEAK

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменяет текущую операцию"""
    await update.message.reply_text("Операция отменена.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# --- Запуск приложения ---

def main():
    """Основная функция запуска бота"""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not configured!")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Основные команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))

    # Обработка кнопок
    application.add_handler(CallbackQueryHandler(button_handler))

    # Обработка ввода данных
    conv_handler = ConversationHandler(
        entry_points=[],
        states={
            SET_TEMP_WATER: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_temp_water)],
            SET_TEMP_AIR: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_temp_air)],
            SET_WATER_LEAK: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_water_leak)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
