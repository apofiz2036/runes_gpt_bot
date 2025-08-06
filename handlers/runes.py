import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from utils.runes import get_random_one_rune, get_random_three_runes, get_random_four_runes, load_rune_data
from utils.database import save_subscriber, save_divination
from utils.gpt import ask_gpt
from handlers.base import main_menu
from utils.logging import setup_logging, send_error_to_admin


# Инициализация логгера
logger = logging.getLogger(__name__)
setup_logging()


async def one_rune_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        """Активирует режим гадания на одной руне."""
        keyboard = [['Главное меню']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        context.user_data.update({
            'mode':'one_rune',
            'prompt_type': 'one_rune'
        })

        await update.message.reply_text(
            "Задайте ваш вопрос для гадания на одной руне:", 
            reply_markup=reply_markup
        )
    except Exception as e:
        error_message = f"Ошибка в one_rune_mode: {e}"
        logger.error(error_message)
        await send_error_to_admin(context.bot, error_message)


async def three_runes_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Активирует режим гадания на трёх рунах."""
    try:
        keyboard = [['Главное меню']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        context.user_data.update({
            'mode': 'three_rune',
            'prompt_type': 'three_runes',
            'selected_runes': get_random_three_runes()
        })
        
        await update.message.reply_text(
            "Задайте ваш вопрос для гадания на трёх рунах",
            reply_markup=reply_markup
        )
    except Exception as e:
        error_message = f"Ошибка в three_runes_mode: {e}"
        logger.error(error_message)
        await send_error_to_admin(context.bot, error_message)


async def four_runes_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Активирует режим гадания на четырёх рунах."""
    try:
        keyboard = [['Главное меню']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        context.user_data.update({
            'mode': 'four_rune',
            'prompt_type': 'four_runes',
            'selected_runes': get_random_four_runes() 
        })

        await update.message.reply_text(
            "Задайте ваш вопрос для гадания на четырёх рунах",
            reply_markup=reply_markup
        )
    except Exception as e:
        error_message = f"Ошибка в four_runes_mode: {e}"
        logger.error(error_message)
        await send_error_to_admin(context.bot, error_message)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает пользовательские сообщения в зависимости от текущего режима."""
    try:
        # Игнорируем нажатие кнопок в меню    
        if update.message.text in ["Одна руна", "Три руны", "Четыре руны", "Как гадать", "Главное меню"]:
            return
        
        current_mode = context.user_data.get('mode')

        # Если режим не установлен возвращаемся в главное меню
        if current_mode not in ['one_rune', 'three_rune', 'four_rune']:
            await main_menu(update, context)
            return

        # Сохраняем подписчика при первом обращении
        if not context.user_data.get('is_subscribed'):
            user = update.message.from_user
            save_subscriber(user.id, user.full_name)
            context.user_data['is_subscribed'] = True

        user_question = update.message.text

        # Обработка режима одной руны
        if current_mode == 'one_rune':
            await _handle_one_rune_mode(update, user_question)

        # Обработка режима трёх рун
        elif current_mode == 'three_rune':
            await _handle_three_runes_mode(update, context, user_question)
        
        # Обработка режима четырёх рун
        elif current_mode == 'four_rune':
            await _handle_four_runes_mode(update, context, user_question)

        await main_menu(update, context)
    except Exception as e:
        error_message = f"Ошибка в handle_message: {e}"
        logger.error(error_message)
        await send_error_to_admin(context.bot, error_message)   


async def _handle_one_rune_mode(update: Update, question: str) -> None:
    """Обрабатывает запрос для режима одной руны."""
    try:
        user_id = update.message.from_user.id
        rune_name, rune_image = get_random_one_rune()

        with open(rune_image, 'rb') as photo:
            await update.message.reply_photo(photo)
        
        gpt_response = await ask_gpt(question, {'name': rune_name}, 'one_rune')

        save_divination(user_id, 'one_rune')

        await update.message.reply_text(gpt_response)
    except Exception as e:
        error_message = f"Ошибка в _handle_one_rune_mode: {e}"
        logger.error(error_message)


async def _handle_three_runes_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, question: str) -> None:
    """Обрабатывает запрос для режима трёх рун."""
    try:
        user_id = update.message.from_user.id
        runes = context.user_data['selected_runes']
        rune_data = load_rune_data()

        if not isinstance(rune_data, dict):
            await update.message.reply_text("Ошибка: данные рун не загружены правильно")
            return
        
        runes_for_prompt = []

        # Отправляем изображения рун и собираем данные для GPT
        for rune in runes:
            try:
                # Проверяем, есть ли руна в данных
                if rune['rune_key'] not in rune_data:
                    await update.message.reply_text(f"Руна {rune['rune_key']} не найдена")
                    continue

                # Определяем вариант руны
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
                
                with open(image_path, 'rb') as photo:
                    await update.message.reply_photo(photo)

                runes_for_prompt.append({
                    'name': name_info
                })
                
            except Exception as e:
                await update.message.reply_text(f"Ошибка при обработке руны: {str(e)}")
                continue

        if runes_for_prompt:
            gpt_response = await ask_gpt(question, runes_for_prompt, 'three_runes')
            save_divination(user_id, 'three_runes')
            await update.message.reply_text(gpt_response)
        else:
            await update.message.reply_text("Не удалось получить данные рун для интерпретации")
    except Exception as e:
        error_message = f"Ошибка в _handle_three_runes_mode: {e}"
        logger.error(error_message)
        await send_error_to_admin(context.bot, error_message)


async def _handle_four_runes_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, question: str) -> None:
    """Обрабатывает запрос для режима четырёх рун."""
    try:
        user_id = update.message.from_user.id
        runes = context.user_data['selected_runes']
        rune_data = load_rune_data()

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
                
                with open(image_path, 'rb') as photo:
                    await update.message.reply_photo(photo)

                runes_for_prompt.append({'name': name_info})
                
            except Exception as e:
                await update.message.reply_text(f"Ошибка при обработке руны: {str(e)}")
                continue
        
        if runes_for_prompt:
            gpt_response = await ask_gpt(question, runes_for_prompt, 'four_runes')
            save_divination(user_id, 'four_runes')
            await update.message.reply_text(gpt_response)
        else:
            await update.message.reply_text("Не удалось получить данные рун для интерпретации")
    except Exception as e:
        error_message = f"Ошибка в _handle_four_runes_mode: {e}"
        logger.error(error_message)
        await send_error_to_admin(context.bot, error_message)
