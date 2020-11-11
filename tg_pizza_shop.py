__author__ = 'ArkJzzz (arkjzzz@gmail.com)'

import os
import logging
import redis
import requests
import json
import textwrap
from datetime import datetime

from telegram import InlineKeyboardMarkup
from telegram.ext import Filters
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import CallbackQueryHandler
from telegram.ext import MessageHandler
# from telegram_bot_pagination import InlineKeyboardPaginator
from dotenv import load_dotenv
from validate_email import validate_email

import cms_helpers
import keyboards


logger = logging.getLogger(__file__)

_database = None


def get_database_connection():
    global _database
    if _database is None:
        database_password = os.getenv('REDIS_PASSWORD')
        database_host = os.getenv('REDIS_HOST')
        database_port = os.getenv('REDIS_PORT')
        _database = redis.Redis(
                host=database_host,
                port=database_port,
                password=database_password,
            )
    return _database


def handle_users_reply(update, context):
    db = get_database_connection()

    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return

    if user_reply == '/start':
        user_state = 'START'
    elif 'HANDLE_MENU' in user_reply:
        user_state = 'HANDLE_MENU'
    elif 'HANDLE_DESCRIPTION' in user_reply:
        user_state = 'HANDLE_DESCRIPTION'
    elif 'CLEAR_CART' in user_reply:
        user_state = 'CLEAR_CART'
    elif 'HANDLE_CART' in user_reply:
        user_state = 'HANDLE_CART'
    elif 'HANDLE_REMOVE_ITEM' in user_reply:
        user_state = 'HANDLE_CART'
    elif 'HANDLE_CHECKOUT' in user_reply:
        user_state = 'WAITING_EMAIL'
    elif 'HANDLE_CREATE_CUSTOMER' in user_reply:
        user_state = 'WAITING_EMAIL'
    else:
        user_state = db.hget(
            name='fish_shop_users_states',
            key=chat_id,
        ).decode("utf-8")

    logger.debug('user_state: {}'.format(user_state))
    
    states_functions = {
        'START': start,
        'HANDLE_MENU': show_menu,
        'HANDLE_DESCRIPTION': show_description,
        'HANDLE_CART': show_cart,
        'WAITING_EMAIL': checkout,
    }

    state_handler = states_functions[user_state]

    try:
        next_state = state_handler(update, context)
        logger.debug('next_state: {}'.format(next_state))
        db.hset(name='fish_shop_users_states', key=chat_id, value=next_state)
    except Exception as err:
        logger.error('Error: {}'.format(err), exc_info=True)


def error(update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def start(update, context):
    chat_id = update.message.chat_id
    user = update.message.from_user
    logger.info(f'User @{user.username} started the conversation.')
    cart = cms_helpers.get_cart(chat_id)
    logger.debug(f'Корзина: {cart}')

    welcome_message = f'''\
            Здравствуйте, {user.first_name}.
            Рады видеть Вас в нашем магазине!
        '''
    welcome_message = textwrap.dedent(welcome_message)
    reply_keyboard = InlineKeyboardMarkup(keyboards.start_keyboard)

    update.message.reply_text(
        text=welcome_message, 
        reply_markup=reply_keyboard,
    )

    return 'HANDLE_MENU'


def show_menu(update, context):
    products = cms_helpers.get_products()
    query = update.callback_query
    logger.debug(query.data)

    if 'PAGE' in query.data:
        user_reply, pattern, current_page = query.data.split('|')
        current_page = int(current_page)
    else:
        current_page = 1

    reply_keyboard = keyboards.get_menu_keyboard(products['data'], 
                                                                current_page)
    query.message.reply_text(
        text='В нашем магазине Вы можете купить следующие товары:',
        reply_markup=reply_keyboard,
    )
    context.bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
    )

    return 'HANDLE_DESCRIPTION'


def show_description(update, context):
    query = update.callback_query
    logger.debug(query.data)
    chat_id = query.message.chat_id

    if 'HANDLE_DESCRIPTION' in query.data:
        user_reply, product_id = query.data.split('|')
        product_data = cms_helpers.get_product(product_id)
        image_id = (product_data['data']['relationships']
                                                ['main_image']['data']['id'])
        image_link = cms_helpers.get_image_link(image_id)
        message = keyboards.format_product_info(product_data)
        product_details_keyboard = keyboards.get_product_details_keyboard(
                product_id,
            )
        reply_keyboard = InlineKeyboardMarkup(product_details_keyboard)
        context.bot.send_photo(
            chat_id=chat_id,
            photo=image_link,
            caption=message,
            reply_markup=reply_keyboard,
        )
        context.bot.delete_message(
            chat_id=chat_id,
            message_id=query.message.message_id,
        )

    elif 'ADD_TO_CART' in query.data:
        user_reply, product_id = query.data.split('|')
        adding_result = cms_helpers.add_product_to_cart(
                chat_id,
                product_id,
            )
        context.bot.answer_callback_query(
                callback_query_id=query.id, 
                text='Товар добавлен в корзину', 
            )
        logger.debug(f'Результат добавления товара в корзину: {adding_result}')

    return 'HANDLE_DESCRIPTION'


def show_cart(update, context):
    query = update.callback_query
    logger.debug(query.data)
    chat_id = query.message.chat_id

    if 'HANDLE_REMOVE_ITEM' in query.data:
        user_reply, item_id = query.data.split('|')
        logger.debug(f'Удаление товара с id {item_id}')
        cms_helpers.remove_cart_item(chat_id, item_id)

    cart_items = cms_helpers.get_cart_items(chat_id)
    formated_cart_items = keyboards.format_cart(cart_items)
    cart_show_keyboard = keyboards.get_cart_show_keyboard(cart_items)
    cart_show_keyboard = InlineKeyboardMarkup(cart_show_keyboard)
    logger.debug(f'Товары в корзине: {cart_items}')

    query.message.reply_text(
        text=formated_cart_items,
        reply_markup=cart_show_keyboard,
    )
    context.bot.delete_message(
        chat_id=chat_id,
        message_id=query.message.message_id,
    )

    return 'HANDLE_CART'


def checkout(update, context):
    query = update.callback_query
    logger.debug(query.data)
    chat_id = query.message.chat_id
    customer_name = query.from_user.first_name

    if 'HANDLE_CHECKOUT' in query.data:
        waiting_email_message = 'Напишите, пожалуйста, Ваш e-mail адрес'
        query.message.reply_text(
            text=waiting_email_message,
        )
        context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )

        return 'WAITING_EMAIL'

    elif 'HANDLE_CREATE_CUSTOMER' in query.data:
        user_reply, customer_email = query.data.split('|')
        cart_items = cms_helpers.get_cart_items(chat_id)

        try:
            customer = cms_helpers.create_customer(
                    customer_name,
                    customer_email
                )
        except requests.exceptions.HTTPError as HTTPError:
            status_code = HTTPError.response.status_code
            if status_code == 409:
                logger.warning('Такой e-mail уже есть в базе')
                query.message.reply_text(
                    text='Такой e-mail уже есть в базе, попробуйте заново',
                )

            return 'WAITING_EMAIL'

        buy_message = f'''Совершена покупка:
                    {customer["data"]}

                    {keyboards.format_cart(cart_items)}
                    '''
        logger.info(buy_message)
        context.bot.send_message(
            chat_id=os.getenv('TELEGRAM_ADMIN_CHAT_ID'),
            text=buy_message,
        )
        context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )

        create_customer_message = 'Спасибо за покупку!\n'\
                'Мы с Вами свяжемся в ближайшее время '\
                'для уточнения способа оплаты и доставки выбранных товаров'
        reply_keyboard = InlineKeyboardMarkup(keyboards.start_keyboard)
        query.message.reply_text(
            text=create_customer_message,
            reply_markup=reply_keyboard,
        )

        return 'HANDLE_MENU'

    return 'WAITING_EMAIL'


def confirm_email(update, context):
    user_reply = update.message.text
    logger.debug(f'user_reply: {user_reply}')

    if validate_email(user_reply):
        confirmation_keyboard = keyboards.get_confirmation_keyboard(user_reply)
        reply_keyboard = InlineKeyboardMarkup(confirmation_keyboard)
        update.message.reply_text(
            text=f'ваш e-mail: {user_reply}', 
            reply_markup=reply_keyboard,
        )
    else:
        invalid_email_message = '''\
                Кажется, e-mail неправильный.
                Попробуйте снова.
            '''
        invalid_email_message = textwrap.dedent(invalid_email_message)
        update.message.reply_text(
            text=invalid_email_message, 
        )

    return 'WAITING_EMAIL'


def main():
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
            fmt='\n%(asctime)s %(name)s:%(lineno)d - %(message)s',
            datefmt='%Y-%b-%d %H:%M:%S (%Z)',
            style='%',
        )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.setLevel(logging.DEBUG)

    cms_helpers_logger = logging.getLogger('cms_helpers')
    cms_helpers_logger.addHandler(console_handler)
    cms_helpers_logger.setLevel(logging.DEBUG)

    keyboards_logger = logging.getLogger('keyboards')
    keyboards_logger.addHandler(console_handler)
    keyboards_logger.setLevel(logging.DEBUG)

    load_dotenv()
    updater = Updater(
            token=os.getenv('DEV_TELEGRAM_TOKEN'),
            use_context=True,
        )
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, confirm_email))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
