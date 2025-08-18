import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from utils.runes import (
    get_random_one_rune,
    get_random_three_runes,
    get_random_four_runes,
    get_random_six_runes,
    get_random_twelve_runes,
    load_rune_data
)
from utils.database import save_subscriber, save_divination, deduct_limits, get_user_info_by_user_id
from utils.gpt import ask_gpt
from handlers.base import main_menu
from utils.logging import setup_logging, send_error_to_admin
from utils.prices import load_prices


# Инициализация логгера
logger = logging.getLogger(__name__)
setup_logging()


PROMPT_TYPE_NAMES = {
    'one_rune': 'одной руне',
    'three_runes': 'трёх рунах',
    'four_runes': 'четырёх рунах',
    'fate': "раскладе судьба",
    'field': "Вспаханное поле"
}

SEND_IMAGES = {
    "three_runes": True,
    "four_runes": True,
    "fate": False,
    "field": False
}


async def  _enter_rune_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str, prompt_type: str, rune_selector=None) -> None:
    """Универсальный метод для активации режима гадания."""
    try:
        keyboard = [['Главное меню']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        context.user_data.update({
            'mode': mode,
            'prompt_type': prompt_type
        })

        if rune_selector:
            context.user_data['selected_runes'] = await rune_selector()
        
        readable_name = PROMPT_TYPE_NAMES.get(prompt_type, prompt_type)
        await update.message.reply_text(
            f"Задайте ваш вопрос для гадания на {readable_name}:",
            reply_markup=reply_markup
        )
    except Exception as e:
        error_message = f"Ошибка в _enter_rune_mode ({mode}): {e}"
        logger.error(error_message)
        await send_error_to_admin(context.bot, error_message)


async def one_rune_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Активирует режим гадания на одной руне."""
    await _enter_rune_mode(update, context, 'one_rune', 'one_rune')


async def three_runes_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Активирует режим гадания на трёх рунах."""
    await _enter_rune_mode(update, context, 'three_rune', 'three_runes', get_random_three_runes)


async def four_runes_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Активирует режим гадания на четырёх рунах."""
    await _enter_rune_mode(update, context, 'four_rune', 'four_runes', get_random_four_runes)


async def fate_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Активирует режим гадания на четырёх рунах."""
    await _enter_rune_mode(update, context, 'fate', 'fate', get_random_six_runes)


async def field_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Активирует режим гадания вспаханное поле"""
    await _enter_rune_mode(update, context, 'field', 'field', get_random_twelve_runes)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает пользовательские сообщения в зависимости от текущего режима."""
    try:
        # Игнорируем нажатие кнопок в меню    
        if update.message.text in ["Одна руна", "Три руны", "Четыре руны", "Судьба", "Вспаханное поле", "Как гадать",  "Главное меню"]:
            return
        
        current_mode = context.user_data.get('mode')

        # Если режим не установлен возвращаемся в главное меню
        if current_mode not in ['one_rune', 'three_rune', 'four_rune', 'fate', 'field']:
            await main_menu(update, context)
            return

        # Сохраняем подписчика при первом обращении
        if not context.user_data.get('is_subscribed'):
            user = update.message.from_user
            await save_subscriber(user.id)
            context.user_data['is_subscribed'] = True

        user_question = update.message.text

        handlers = {
            'one_rune': lambda: _handle_one_rune_mode(update, user_question),
            'three_rune': lambda: _handle_multiple_runes_mode(update, context, user_question, 'three_runes'),
            'four_rune': lambda: _handle_multiple_runes_mode(update, context, user_question, 'four_runes'),
            'fate': lambda: _handle_multiple_runes_mode(update, context, user_question, 'fate'),
            'field': lambda: _handle_multiple_runes_mode(update, context, user_question, 'field'),
        }

        if current_mode in handlers:
            await handlers[current_mode]()
        
        await main_menu(update, context)
    except Exception as e:
        error_message = f"Ошибка в handle_message: {e}"
        logger.error(error_message)
        await send_error_to_admin(context.bot, error_message)   


async def _handle_one_rune_mode(update: Update, question: str) -> None:
    """Обрабатывает запрос для режима одной руны."""
    try:
        user_id = update.message.from_user.id
        prices = load_prices()
        price = prices.get("one_rune", 10)
        
        # Проверка лимитов
        success, _, limits = await get_user_info_by_user_id(user_id)
        if not success or limits < price:
            await update.message.reply_text(
                "У вас недостаточно лимитов. "
                "Дождитесь пополнения или напишите админу @Apofiz2036"
            )
            return
        
        # Списываем
        if not await deduct_limits(user_id, price):
            await update.message.reply_text(
                "Не удалось списать лимиты. Попробуйте позже."
            )
            return  

        rune_name, rune_image = await get_random_one_rune()

        with open(rune_image, 'rb') as photo:
            await update.message.reply_photo(photo)
        
        gpt_response = await ask_gpt(question, {'name': rune_name}, 'one_rune')

        await save_divination(user_id, 'one_rune')

        await update.message.reply_text(gpt_response)
    except Exception as e:
        error_message = f"Ошибка в _handle_one_rune_mode: {e}"
        logger.error(error_message)
        await send_error_to_admin(update.get_bot(), error_message)


async def _handle_multiple_runes_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, question: str, prompt_type: str) -> None:
    """Обрабатывает запросы для режима с несколькими рунами (3, 4 и т.д.)."""
    try:
        user_id = update.message.from_user.id
        prices = load_prices()
        price = prices.get(prompt_type, 10)

         # Проверка лимитов
        success, _, limits = await get_user_info_by_user_id(user_id)
        if not success or limits < price:
            await update.message.reply_text(
                "У вас недостаточно лимитов. "
                "Дождитесь пополнения или напишите админу @Apofiz2036"
            )
            return

        # Списываем
        if not await deduct_limits(user_id, price):
            await update.message.reply_text(
                "Не удалось списать лимиты. Попробуйте позже."
            )
            return

        runes = context.user_data['selected_runes']
        rune_data = await load_rune_data()

        if not isinstance(rune_data, dict):
            await update.message.reply_text("Ошибка: данные рун не загружены правильно")
            return
        
        runes_for_prompt = []

        for rune in runes:
            try:
                if rune['rune_key'] not in rune_data:
                    await update.message.reply_text(f"Руна {rune['rune_key']} не найдена")
                    continue

                variant = rune['variant']
                if variant is None:
                    image_info = rune_data[rune['rune_key']].get('image')
                    name_info = rune_data[rune['rune_key']].get('name')
                else:
                    image_info = rune_data[rune['rune_key']].get(variant, {}).get('image')
                    name_info = rune_data[rune['rune_key']].get(variant, {}).get('name')
                
                if not image_info or not name_info:
                    await update.message.reply_text(f"Данные для руны {rune['rune_key']} неполные")
                    continue
                
                image_path = os.path.join('images', image_info)

                if SEND_IMAGES.get(prompt_type, True):
                    with open(image_path, 'rb') as photo:
                        await update.message.reply_photo(photo)
                
                runes_for_prompt.append({'name': name_info})
            except Exception as e:
                await update.message.reply_text(f"Ошибка при обработке руны: {str(e)}")
                continue
            
        if runes_for_prompt:
            gpt_response = await ask_gpt(question, runes_for_prompt, prompt_type)
            await save_divination(user_id, prompt_type)
            await update.message.reply_text(gpt_response)
        else:
            await update.message.reply_text("Не удалось получить данные рун для интерпретации")
    
    except Exception as e:
        error_message = f"Ошибка в _handle_multiple_runes_mode ({prompt_type}): {e}"
        logger.error(error_message)
        await send_error_to_admin(context.bot, error_message)
