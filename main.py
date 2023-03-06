import logging
import os
import telegram
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater
from tronapi import Tron, HttpProvider
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TRX_ADDRESS = os.getenv('MAIN_ADDRESS')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')

full_node = HttpProvider('https://api.trongrid.io')
solidity_node = HttpProvider('https://api.trongrid.io')
event_server = HttpProvider('https://api.trongrid.io')
api = Tron(
    full_node=full_node,
    solidity_node=solidity_node,
    event_server=event_server,
    private_key=PRIVATE_KEY,
    default_address=TRX_ADDRESS
)

bot = telegram.Bot(token=TELEGRAM_TOKEN)


# Обработчик команды /start
def start(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет! Я могу помочь тебе пополнить кошелек Tron (TRX). \r\nЕсли не знаешь с чего начать, запусти команду /info"
    )


# Обработчик команды /info
def info(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="/balance - Проверить текущий баланс кошелька\r\n"
             "/deposit - Пополнить счёт своего кошелька"


    )

# Обработчик команды /balance
def balance(update, context):
    # Получение аккаунта кошелька
    api = Tron(
        full_node=full_node,
        solidity_node=solidity_node,
        event_server=event_server
    )
    account = api.trx.get_account(TRX_ADDRESS)

    # Извлечение текущего баланса
    balance = account['balance']
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"💵Текущий баланс кошелька: {balance / 10**6} TRX"
    )


# Обработчик команды /deposit
def deposit(update, context):
    # Извлечение параметров из сообщения пользователя
    message = update.message.text
    parameters = message.split(' ')

    # Проверка корректности ввода параметров
    if len(parameters) != 3:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Некорректный ввод параметров. \r\nИспользуйте команду /deposit <адрес получателя> <сумма>")
        return

    to_address = parameters[1]
    amount = float(parameters[2])

    # Создание новой транзакции на пополнение кошелька
    result = api.trx.send_trx(
        to=to_address,
        amount=amount,
        options={
            'from': TRX_ADDRESS
        }
    )

    # Распечатка результата отправки транзакции
    print(result)
    # Получение обновленного баланса кошелька
    balance = api.trx.get_balance(TRX_ADDRESS)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"Средства успешно отправлены. Новый баланс кошелька: {balance / 10 ** 6} TRX")


# Обработчик неизвестных команд
def unknown(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Извините, я не понимаю эту команду. Пожалуйста, введите /start для начала работы."
    )


def main():
    # Создание экземпляра Updater и добавление обработчиков команд
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('info', info))
    dispatcher.add_handler(CommandHandler('balance', balance))
    dispatcher.add_handler(CommandHandler('deposit', deposit))
    dispatcher.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()

#pip install python-telegram-bot
#pip install tronapi
#requests