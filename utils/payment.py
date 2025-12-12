from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from utils.database import top_up_limits, get_user_info_by_user_id
from utils.yookassa_service import create_payment, check_payment_status
from handlers.base import main_menu
from handlers.runes import handle_message
import asyncio
import logging

logger = logging.getLogger(__name__)

# Хранилище активных платежей
active_payment_checks = {}


async def payment_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Процесс оплаты и режим ввода суммы"""
    context.user_data['mode'] = 'payment'

    keyboard = [['Главное меню']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        """Введите целое число — сумму в рублях для пополнения вашего баланса. 💎

Оплата проходит официально и безопасно через сервис ЮKassa.

Вы получите платёжный чек — всё прозрачно и надёжно.✅

Стоимость одного лимита один рубль

Пример: 150""",
        reply_markup=reply_markup
    )


async def get_link_topayment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Создание платежа и запуск фонового процесса оплаты"""
    user_id = update.effective_user.id

    success, public_id, limits = await get_user_info_by_user_id(user_id)
    if not success:
        await update.message.reply_text("Ошибка: не удалось найти ваши данные.")
        await main_menu(update, context)
        return

    amount = await _validate_amount(update, context, update.message.text.strip())
    if amount is None:
        return
    
    #  Создание платежа
    payment_url, payment_id = await create_payment(user_id, amount, public_id)
    if not payment_url or not payment_id:
        await update.message.reply_text("Ошибка при создании платежа. Попробуйте позже.")
        await main_menu(update, context)
        return
    
    #  Запуск проверки
    context.user_data.pop('mode', None)
    await _start_payment_monitoring(payment_id, user_id, amount, public_id, update)
    
    #  Отправка ссылки на оплату
    await update.message.reply_text(
        f"💳 Ссылка на оплату {amount:.2f} ₽:\n\n"
        f"{payment_url}\n\n"
        f"После успешной оплаты лимиты будут зачислены автоматически."
    )


async def _validate_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> float:
    """Проверка корректности введёной суммы"""
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError("Сумма должна быть больше 0")
        return amount
    except (ValueError, TypeError):
        await update.message.reply_text("Пожалуйста, введите корректную сумму числом.")
        await main_menu(update, context)
        return


async def _start_payment_monitoring(payment_id: str, user_id: int, amount: float, public_id: str, update: Update) -> None:
    """Запуск фоновой проверки статуса платежа"""
    payment_info = {
        'user_id': user_id,
        'amount': amount,
        'public_id': public_id,
        'chat_id': update.effective_chat.id
    }
    asyncio.create_task(_check_payment_periodically(payment_id, payment_info))


async def _check_payment_periodically(payment_id: str, payment_info: dict) -> None:
    """Проверка статуча платежа каждые 30 секунд в течение 10 минут"""
    if payment_id in active_payment_checks:
        logger.info(f"Проверка для платежа {payment_id} уже запущена")
        return    
        
    active_payment_checks[payment_id] = True        
    
    max_checks = 20
    check_count = 0

    try:
        while check_count < max_checks:
            await asyncio.sleep(30)
            check_count += 1

            status = await check_payment_status(payment_id)
            logger.info(f"Платеж {payment_id}: статус {status}, проверка #{check_count}")
    
            if status == 'succeeded':
                await _handle_successful_payment(payment_id, payment_info)
                break
            elif status == 'canceled':
                await _handle_canceled_payment(payment_id, payment_info)
                break
    except Exception as e:
        logger.error(f"Ошибка при проверке платежа {payment_id}: {e}")
    finally:
        active_payment_checks.pop(payment_id, None)

        if check_count >= max_checks:
            logger.info(f"Проверка платежа {payment_id} завершена по таймауту (10 минут)")
            await _handle_payment_timeout(payment_id, payment_info)
    

async def _handle_successful_payment(payment_id: str, payment_info: dict) -> None:
    """Обработка успешной оплаты"""
    try:
        user_id = payment_info['user_id']
        amount = payment_info['amount']
        public_id = payment_info['public_id']

        logger.info(f"Обрабатываем успешный платеж {payment_id} для user_id {user_id}")
        
        success, updated_user_id = await top_up_limits(public_id, amount)
        if success:
            logger.info(f"Лимиты успешно пополнены для пользователя {user_id} на сумму {amount}")
        else:
            logger.error(f"Ошибка пополнения лимитов для пользователя {user_id}")

    except Exception as e:
        logger.error(f"Ошибка обработки успешного платежа handle_successful_payment {payment_id}: {e}")


async def _handle_canceled_payment(payment_id: str, payment_info: dict) -> None:
    """Логгирование отменённого платежа"""
    logger.info(f"Платеж {payment_id} отменен")

        
async def _handle_payment_timeout(payment_id: str, payment_info: dict) -> None:
    """Логгирование истечения времени платежа"""
    logger.info(f"Время оплаты истекло для платежа {payment_id}")   
        

async def handle_payment_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода суммы платежа и отправка в обработчик"""
    try:
        if context.user_data.get('mode') != 'payment':
            await handle_message(update, context)
            return
        
        text = update.message.text.strip()

        menu_commands = ["Главное меню", "Одна руна", "Три руны", "Четыре руны", "Судьба", "Вспаханное поле", "Как гадать", "Мои лимиты", "Пополнить лимиты"]

        if text in menu_commands:
            from main import handle_menu
            await handle_menu(update, context)
            return
        
        await get_link_topayment(update, context)
    except Exception as e:
        error_message = f"Ошибка в handle_payment_input: {e}"
        logger.error(error_message)
        await main_menu(update, context)        
    
        
