from yookassa import Configuration, Payment
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
import asyncio
import logging


logger = logging.getLogger(__name__)


Configuration.configure(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, sandbox=True)


async def create_payment(user_id: int, amount: float, public_id: str) -> tuple[str | None, str | None]:
    """Создание платежа в Юкассе и возвращение ссылки и ID платежа"""
    try:
        payment_data = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/dreams_gpt_bot"                          
            },
            "capture": True,
            "description": f"Пополнение лимитов для пользователя {public_id}",
            "metadata": {
                "user_id": user_id,
                "public_id": public_id,
                "bot_name": "runes_bot"
            }
        }

        payment = await asyncio.to_thread(Payment.create, payment_data)
        return payment.confirmation.confirmation_url, payment.id
    
    except Exception as e:
        logger.error(f"Ошибка создания платежа для user_id {user_id}: {e}")
        return None, None


async def check_payment_status(payment_id):
    """Проверка статуса платежа в Юкассе"""
    try:
        payment = await asyncio.to_thread(Payment.find_one, payment_id)
        return payment.status
    except Exception as e:
        logger.error(f"Ошибка проверки статуса платежа {payment_id}: {e}")
        return None
