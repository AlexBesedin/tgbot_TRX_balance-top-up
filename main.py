import logging
import os
import telegram
from web3 import Web3
import requests
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater
from tronapi import Tron, HttpProvider
from dotenv import load_dotenv


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TRX_ADDRESS = os.getenv('MAIN_ADDRESS')
PRIVATE_KEY_TRX = os.getenv('PRIVATE_KEY')
API_KEY_BSC = os.getenv('API_KEY_BSC')
BNB_WALLET = os.getenv('BNB_WALLET')


full_node = HttpProvider('https://api.trongrid.io')
solidity_node = HttpProvider('https://api.trongrid.io')
event_server = HttpProvider('https://api.trongrid.io')
api = Tron(
    full_node=full_node,
    solidity_node=solidity_node,
    event_server=event_server,
    private_key=PRIVATE_KEY_TRX,
    default_address=TRX_ADDRESS
)

bot = telegram.Bot(token=TELEGRAM_TOKEN)


# Обработчик команды /start
def start(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет! Я могу помочь тебе пополнить кошелек Tron (TRX).\r\n"
             "Если не знаешь с чего начать, запусти команду /info"
    )


# Обработчик команды /info
def info(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="/balance - Проверить текущий баланс кошелька\r\n"
             "/deposit - Пополнить счёт своего кошелька"


    )


def get_balance(api_key, address):
    url = f'https://api.bscscan.com/api?module=account&action=balance&address={address}&tag=latest&apikey={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        balance = float(response.json()['result']) / 10**18
        return balance
    else:
        raise ValueError('Не удалось получить баланс')


# Обработчик команды /bnb_balance
def bnb_balance(update, context):
    chat_id = update.message.chat_id
    balance = get_balance(API_KEY_BSC, BNB_WALLET)
    context.bot.send_message(
        chat_id=chat_id,
        text=f'Ваш текущий баланс: {balance:.6f} BNB'
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
                                 text="Некорректный ввод параметров. \r\n"
                                      "Используйте команду /deposit <адрес получателя> <сумма>")
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
    dispatcher.add_handler(CommandHandler('bnb_balance', bnb_balance))
    dispatcher.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()

#pip install python-telegram-bot
#pip install tronapi
#pip request
#pip install python-dotenv
