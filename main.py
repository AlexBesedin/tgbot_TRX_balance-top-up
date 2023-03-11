import logging
import time
import os
import telegram
import requests
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater
from tronapi import Tron, HttpProvider
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware


logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, '
               '%(message)s, %(funcName)s, %(lineno)d'
    )
logger = logging.getLogger()

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TRX_ADDRESS = os.getenv('MAIN_ADDRESS')
PRIVATE_KEY_TRX = os.getenv('PRIVATE_KEY')
API_KEY_BSC = os.getenv('API_KEY_BSC')
BNB_WALLET = os.getenv('BNB_WALLET')
PRIVATE_KEY_BNB = os.getenv('PRIVATE_KEY_BNB')


bsc_node = HttpProvider('https://bsc-dataseed.binance.org')

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
        text="Привет! Я могу помочь тебе пополнить твои TRX и BNB кошельки.\r\n"
             "Если не знаешь с чего начать, запусти команду /info"
    )


# Обработчик команды /info
def info(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="/bnb_balance - Текущий баланс BNB кошелька\r\n"
             "/trx_balance - Текущий баланс TRX кошелька\r\n"
             "/bnb - Пополнить счёт своего BNB кошелька\r\n"
             "/trx - Пополнить счёт своего TRX кошелька\r\n"
    )


def send_bnb(private_key, to_address, value):
    # Установка соединения с BSC_NODE_ENDPOINT
    w3 = Web3(Web3.HTTPProvider(bsc_node))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    # Получение Nonce
    from_address = w3.eth.account.from_key(private_key).address
    nonce = w3.eth.getTransactionCount(from_address)
    # Подготовка данных для отправки транзакции
    amount = Web3.toWei(value, 'ether')

    tx_data = {
        'to': to_address,
        'value': amount,
        'gas': 200000,
        'gasPrice': w3.toWei('5', 'gwei'),
        'nonce': nonce
    }
    signed_txn = w3.eth.account.sign_transaction(tx_data, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return tx_hash.hex()


# Обработчик команды /bnb
def bnb(update, context):
    chat_id = update.message.chat_id
    message = update.message.text
    parameters = message.split(' ')
    if len(parameters) != 3:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Некорректный ввод параметров. \r\n"
                                      "Используйте команду /bnb <адрес получателя> <сумма>")
        return

    to_address = parameters[1]
    value = float(parameters[2])
    result = send_bnb(PRIVATE_KEY_BNB, to_address, value)
    print(result)
    time.sleep(5)
    balance = get_balance_bnb(API_KEY_BSC, BNB_WALLET)
    context.bot.send_message(
        chat_id=chat_id,
        text=f'Средства успешно отправлены.\r\n'
             f'Новый баланс кошелька:  {balance:.6f} BNB'
    )


def get_balance_bnb(api_key, address):
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
    balance = get_balance_bnb(API_KEY_BSC, BNB_WALLET)
    context.bot.send_message(
        chat_id=chat_id,
        text=f'Текущий баланс кошелька: {balance:.6f} BNB'
    )


# Обработчик команды /trx_balance
def trx_balance(update, context):
    account = api.trx.get_account(TRX_ADDRESS) # Получение аккаунта кошелька
    balance = account['balance'] # Извлечение текущего баланса
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Текущий баланс кошелька: {balance / 10**6} TRX"
    )


# Обработчик команды /trx
def trx(update, context):
    message = update.message.text
    parameters = message.split(' ')
    if len(parameters) != 3:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Некорректный ввод параметров. \r\n"
                                      "Используйте команду /trx <адрес получателя> <сумма>")
        return

    to_address = parameters[1]
    amount = float(parameters[2])
    result = api.trx.send_trx(
        to=to_address,
        amount=amount,
        options={
            'from': TRX_ADDRESS
        }
    )
    print(result)
    balance = api.trx.get_balance(TRX_ADDRESS)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"Средства успешно отправлены.\r\n "
                                  f"Новый баланс кошелька: {balance / 10 ** 6} TRX")


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
    dispatcher.add_handler(CommandHandler('trx_balance', trx_balance))
    dispatcher.add_handler(CommandHandler('trx', trx))
    dispatcher.add_handler(CommandHandler('bnb_balance', bnb_balance))
    dispatcher.add_handler(CommandHandler('bnb', bnb))
    dispatcher.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()

#pip install python-telegram-bot
#pip install tronapi
#pip request
#pip install python-dotenv
#pip install web3
#BSC_NODE_ENDPOINT =https://docs.bnbchain.org/docs/rpc/