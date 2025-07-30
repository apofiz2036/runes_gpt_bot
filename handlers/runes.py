from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from utils.runes import get_random_one_rune, get_random_three_runes, load_rune_data
from utils.database import save_subscriber
from utils.gpt import ask_gpt
from handlers.base import main_menu
import os


async def one_rune_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['Главное меню']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.user_data['mode'] = 'one_rune'
    context.user_data['prompt_type'] = 'one_rune'
    await update.message.reply_text("Задайте ваш вопрос для гадания на одной руне:", reply_markup=reply_markup)


async def three_runes_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['Главное меню']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.user_data['mode'] = 'three_rune'
    context.user_data['prompt_type'] = 'three_runes'

    context.user_data['selected_runes'] = get_random_three_runes()
    
    await update.message.reply_text(
        "Задайте ваш вопрос для гадания на трёх рунах",
        reply_markup=reply_markup
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text in ["Одна руна", "Три руны", "Как гадать", "Главное меню"]:
        return
    
    current_mode = context.user_data.get('mode')

    if current_mode not in ['one_rune', 'three_rune']:
        await main_menu(update, context)
        return

    if not context.user_data.get('is_subscribed'):
        user = update.message.from_user
        save_subscriber(user.id)
        context.user_data['is_subscribed'] = True
    
    user_question = update.message.text

    if current_mode == 'one_rune':
        rune_name, rune_image = get_random_one_rune()
        with open(rune_image, 'rb') as photo:
            await update.message.reply_photo(photo)
        gpt_response = await ask_gpt(user_question, {'name': rune_name}, 'one_rune')
    elif current_mode == 'three_rune':
        runes = context.user_data['selected_runes']
        rune_data = load_rune_data()

        for rune in runes:
            if rune['variant'] is None:
                image = rune_data[rune['rune_key']]['image']
            else:
                image = rune_data[rune['rune_key']][rune['variant']]['image']
            
            image_path = os.path.join('images', image)
            with open(image_path, 'rb') as photo:
                await update.message.reply_photo(photo)

        runes_for_prompt = []
        for rune in runes:
            if rune['variant'] is None:
                name = rune_data[rune['rune_key']]['name']
            else:
                name = rune_data[rune['rune_key']][rune['variant']]['name']
            runes_for_prompt.append({'name': name})

        gpt_response = await ask_gpt(user_question, runes_for_prompt, 'three_runes')

    await update.message.reply_text(gpt_response)
    await main_menu(update, context)