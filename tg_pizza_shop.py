__author__ = 'ArkJzzz (arkjzzz@gmail.com)'

import os
import logging
import redis
import requests
import json
import textwrap
from datetime import datetime

from telegram import InlineKeyboardMarkup
from telegram import ParseMode
from telegram.ext import Filters
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import CallbackQueryHandler
from telegram.ext import MessageHandler
from telegram.ext import PreCheckoutQueryHandler
from dotenv import load_dotenv
from validate_email import validate_email
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException

import cms_helpers
import ext_helpers
import keyboards


logger = logging.getLogger(__file__)

DELIVERY_RADIUS = {
    'SHORT': 0.5,
    'MIDDLE': 5,
    'LONG': 20
}
DELIVERY_PRICE = {
    'SHORT': 0,
    'MIDDLE': 100,
    'LONG': 300
}
REMINDING_TIME = 5
PIZZERIA_NAME = 'НАЗВАНИЕ ЗАВЕДЕНИЯ'

def handle_users_reply(update, context):
    db = ext_helpers.get_database_connection()

    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return

    logger.debug(f'user_reply: {user_reply}')

    if user_reply == '/start':
        user_state = 'START'
    elif 'HANDLE_MENU' in user_reply:
        user_state = 'HANDLE_MENU'
    elif 'HANDLE_DESCRIPTION' in user_reply:
        user_state = 'HANDLE_DESCRIPTION'
    elif 'ADD_TO_CART' in user_reply:
        user_state = 'HANDLE_DESCRIPTION'
    elif 'CLEAR_CART' in user_reply:
        user_state = 'CLEAR_CART'
    elif 'HANDLE_CART' in user_reply:
        user_state = 'HANDLE_CART'
    elif 'HANDLE_REMOVE_ITEM' in user_reply:
        user_state = 'HANDLE_CART'
    elif 'HANDLE_WAITING_PHONE' in user_reply:
        user_state = 'HANDLE_WAITING_PHONE'
    elif 'HANDLE_WAITING_LOCATION' in user_reply:
        user_state = 'HANDLE_WAITING_LOCATION'
    elif 'HANDLE_CHOICE_OF_DELIVERY' in user_reply:
        user_state = 'HANDLE_CHOICE_OF_DELIVERY'
    elif 'HANDLE_DELIVERY' in user_reply:
        user_state = 'HANDLE_DELIVERY'
    elif 'HANDLE_PICK_UP' in user_reply:
        user_state = 'HANDLE_PICK_UP'


    else:
        user_state = db.hget(
            name='pizzeria_users_states',
            key=chat_id,
        ).decode("utf-8")

    logger.debug(f'user_state: {user_state}')
    
    states_functions = {
        'START': start,
        'HANDLE_MENU': show_menu,
        'HANDLE_DESCRIPTION': show_description,
        'HANDLE_CART': show_cart,
        'HANDLE_WAITING_PHONE': waiting_phone,
        'HANDLE_CONFIRM_PHONE': confirm_phone,
        'HANDLE_WAITING_LOCATION': waiting_location,
        'HANDLE_CHOICE_OF_DELIVERY': choice_of_delivery,
        'HANDLE_DELIVERY': delivery,
        'HANDLE_PICK_UP': pick_up,
    }

    state_handler = states_functions[user_state]
    next_state = state_handler(update, context)
    logger.debug('next_state: {}'.format(next_state))
    db.hset(name='pizzeria_users_states', key=chat_id, value=next_state)


def error_handler(update, context):
    message = f'''\
            Exception while handling an update:
            {context.error}
        '''
    logger.error(message)

    context.bot.send_message(
        chat_id=os.getenv('TELEGRAM_ADMIN_CHAT_ID'), 
        text=message,
    )

    


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
    reply_keyboard = keyboards.get_start_keyboard()

    update.message.reply_text(
        text=welcome_message,
        reply_markup=reply_keyboard,
    )

    return 'HANDLE_MENU'


def show_menu(update, context):
    products = cms_helpers.get_products()
    query = update.callback_query
    logger.debug(f'query.data: {query.data}')
    logger.debug(f'user_data: {context.user_data}')

    if 'PAGE' in query.data:
        user_reply, pattern, current_page = query.data.split('|')
        current_page = int(current_page)
    else:
        current_page = 1

    reply_keyboard = keyboards.get_menu_keyboard(products['data'], 
                                                                current_page)
    query.message.reply_text(
        text='Наше меню:',
        parse_mode=ParseMode.MARKDOWN_V2,
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
        message = ext_helpers.format_product_info(product_data)
        reply_keyboard = keyboards.get_product_details_keyboard(product_id)
        context.bot.send_photo(
            chat_id=chat_id,
            photo=image_link,
            caption=message,
            parse_mode=ParseMode.MARKDOWN_V2,
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
        context.bot.answer_callback_query(
            callback_query_id=query.id, 
            text='Товар удален из корзины', 
        )

    cart_items = cms_helpers.get_cart_items(chat_id)
    logger.debug(f'Товары в корзине: {cart_items}')
    formated_cart_items = ext_helpers.format_cart(cart_items)
    reply_keyboard = keyboards.get_cart_show_keyboard(cart_items)

    query.message.reply_text(
        text=formated_cart_items,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_keyboard,
    )
    context.bot.delete_message(
        chat_id=chat_id,
        message_id=query.message.message_id,
    )

    return 'HANDLE_CART'


def waiting_phone(update, context):
    query = update.callback_query
    reply_text = 'Напишите свой номер телефона'
    query.message.reply_text(text=reply_text)

    return 'HANDLE_CONFIRM_PHONE'


def confirm_phone(update, context):
    logger.debug('confirm_phone')
    logger.debug(f'user_data: {context.user_data}')
    user_reply = update.message.text
    logger.debug(f'user_reply: {user_reply}')

    phone = phonenumbers.parse(user_reply, 'RU')

    if phonenumbers.is_valid_number(phone):
        logger.debug('phone valid')
        phone = f'+{phone.country_code}{phone.national_number}'
        context.user_data['phone'] = phone

        reply_keyboard = keyboards.get_confirm_phone_keyboard()
        update.message.reply_text(
            text=f'ваш номер телефона: {phone}',
            reply_markup=reply_keyboard,
        )

    else:
        invalid_phone_message = '''\
                Кажется, номер неправильный.
                Попробуйте снова.
            '''
        invalid_phone_message = textwrap.dedent(invalid_phone_message)
        update.message.reply_text(
            text=invalid_phone_message, 
        )
        
    return 'HANDLE_CONFIRM_PHONE'


def waiting_location(update, context):
    query = update.callback_query
    waiting_location_message = '''\
        Напишите адрес доставки или отправьте геопозицию
        '''
    waiting_location_message = textwrap.dedent(waiting_location_message)
    query.message.reply_text(text=waiting_location_message)

    return 'HANDLE_CHOICE_OF_DELIVERY'


def choice_of_delivery(update, context):
    logger.debug('get_delivery_area')
    logger.debug(f'user_data: {context.user_data}')
    user_location = ext_helpers.extract_coordinates(update.message)
    if not user_location:
        reply_text = '''\
            Не удалось определить адрес доставки.
            Попробуйте еще раз.
            '''
        reply_text = textwrap.dedent(reply_text)
        update.message.reply_text(reply_text)
        return 'HANDLE_CHOICE_OF_DELIVERY'

    context.user_data['location'] = user_location
    nearest_pizzeria = ext_helpers.get_nearest_pizzeria(user_location)
    pizzeria_id, distance_to_pizzeria = nearest_pizzeria
    delivery_area = ext_helpers.get_delivery_area(distance_to_pizzeria, 
                                                            DELIVERY_RADIUS)
    logger.debug(f'delivery_area: {delivery_area}')
    pizzeria = cms_helpers.get_an_entry('pizzeria', pizzeria_id)
    pizzeria_address = pizzeria['data']['address']
    logger.debug(f'pizzeria_address: {pizzeria_address}')
    context.user_data['nearest_pizzeria_id'] = pizzeria_id

    pick_up_message = f'''\
            Вы можете забрать заказ из ближайшей пиццерии по адресу:
            {pizzeria_address}.

            Она в {round(distance_to_pizzeria, 2)} км от Вас.
        '''
    pick_up_message = dedent.textwrap(pick_up_message)
    delivery_message = ext_helpers.get_choice_of_delivery_message(
                                            delivery_area, DELIVERY_PRICE)
    choice_of_delivery_message = f'''\
            {pick_up_message}
            {delivery_message}
        '''
    choice_of_delivery_message = dedent.textwrap(choice_of_delivery_message)
    reply_keyboard = keyboards.get_choice_of_delivery_keyboard(
                                            delivery_area, DELIVERY_PRICE)
    update.message.reply_text(
        text=choice_of_delivery_message,
        reply_markup=reply_keyboard,
    )

    return 'HANDLE_CHOICE_OF_DELIVERY'


def pick_up(update, context):
    logger.debug('pick_up')
    logger.debug(f'user_data: {context.user_data}')

    context.user_data['delivery'] = False
    chat_id = update.callback_query.message.chat_id
    cart_items = cms_helpers.get_cart_items(chat_id)
    prices = ext_helpers.get_labeled_prices(cart_items)

    context.bot.sendInvoice(
        chat_id=chat_id, 
        title='Оплата заказа', 
        description=f'Заказ в пиццерии "{PIZZERIA_NAME}"', 
        payload='Custom-Payload',
        provider_token=os.getenv('PAYMENTS_PROVIDER_TOKEN'), 
        start_parameter='test-payment', 
        currency='RUB', 
        prices=prices,
    )

    return 'HANDLE_MENU'


def delivery(update, context):
    logger.debug('delivery')
    logger.debug(f'user_data: {context.user_data}')

    context.user_data['delivery'] = True
    chat_id = update.callback_query.message.chat_id
    cart_items = cms_helpers.get_cart_items(chat_id)
    user_location = context.user_data['location']
    lat, lon = user_location
    nearest_pizzeria = ext_helpers.get_nearest_pizzeria(user_location)
    pizzeria_id, distance_to_pizzeria = nearest_pizzeria
    delivery_area = ext_helpers.get_delivery_area(
            distance_to_pizzeria,
            DELIVERY_RADIUS,
        )
    delivery_price = DELIVERY_PRICE[delivery_area]
    prices = ext_helpers.get_labeled_prices(cart_items, delivery_price)

    entry_data = {
        'telegram_id': chat_id,
        'phone': context.user_data['phone'],
        'latitude': lat,
        'longitude': lon,
    }
    cms_helpers.create_entry('Customer_Address', entry_data)

    context.bot.sendInvoice(
        chat_id=chat_id, 
        title='Оплата заказа', 
        description=f'Заказ в пиццерии "{PIZZERIA_NAME}"', 
        payload='Custom-Payload',
        provider_token=os.getenv('PAYMENTS_PROVIDER_TOKEN'), 
        start_parameter='test-payment', 
        currency='RUB', 
        prices=prices,
    )

    return 'HANDLE_MENU'


def precheckout_callback(update, context):
    logger.debug('precheckout_callback')

    query = update.pre_checkout_query
    if query.invoice_payload != 'Custom-Payload':
        context.bot.answer_pre_checkout_query(
            pre_checkout_query_id=query.id, 
            ok=False,
            error_message="Оплата не прошла"
        )
    else:
        context.bot.answer_pre_checkout_query(
            pre_checkout_query_id=query.id, 
            ok=True
        )


def successful_payment_callback(update, context):
    logger.debug('successful_payment_callback')

    chat_id = update.message.chat.id
    lat, lon = context.user_data['location']
    pizzeria_id = context.user_data['nearest_pizzeria_id']
    pizzeria = cms_helpers.get_an_entry('pizzeria', pizzeria_id)
    pizzeria_address = pizzeria['data']['address']
    delivery_man = pizzeria['data']['delivery_man']
    cart_items = cms_helpers.get_cart_items(chat_id)
    formated_cart_items = ext_helpers.format_cart(cart_items)
    
    successful_payment_message = 'Спасибо что выбрали нас!'

    if context.user_data['delivery']:
        successful_payment_message += '''
                Курьер доставит ваш заказ в течение часа
            '''
        successful_payment_message = textwrap.dedent(
                                                successful_payment_message)
        
        context.bot.send_message(
            chat_id=delivery_man,
            text=formated_cart_items,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        context.bot.send_location(
            chat_id=delivery_man,
            latitude=lat,
            longitude=lon,
        )
        context.bot.send_message(
            chat_id=delivery_man,
            text=f"Контактный телефон: {context.user_data['phone']}",
        )

    elif not context.user_data['delivery']:
        successful_payment_message += f'''
                Вы можете забрать заказ из ближайшей пиццерии по адресу:
                {pizzeria_address}.'
            '''
        successful_payment_message = textwrap.dedent(
                                                successful_payment_message)

    update.message.reply_text(
        text=successful_payment_message,
        reply_markup=keyboards.get_start_keyboard(),
    )

    context.job_queue.run_once(
        callback=remind_about_order, 
        when=REMINDING_TIME,
        context=update.message.chat.id
    )

    return 'HANDLE_MENU'


def remind_about_order(context):
    reminding_message = '''\
        *Приятного аппетита!*

        [ место для рекламы ]

        _(что делать, если пицца не пришла)_
    '''
    reminding_message = textwrap.dedent(reminding_message)
    reminding_message = ext_helpers.formatting_for_markdown(reminding_message)

    context.bot.send_message(
        chat_id=context.job.context,
        text=reminding_message,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


def stop(update, context):
    update.message.reply_text('Заходите к нам еще!')

    return END


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

    ext_helpers_logger = logging.getLogger('ext_helpers')
    ext_helpers_logger.addHandler(console_handler)
    ext_helpers_logger.setLevel(logging.DEBUG)

    keyboards_logger = logging.getLogger('keyboards')
    keyboards_logger.addHandler(console_handler)
    keyboards_logger.setLevel(logging.DEBUG)

    load_dotenv()
    updater = Updater(
            token=os.getenv('TELEGRAM_TOKEN'),
            use_context=True,
        )
    job_queue = updater.job_queue

    start_handler = CommandHandler('start', handle_users_reply)
    users_reply_handler = CallbackQueryHandler(handle_users_reply, 
                                                        pass_job_queue=True)
    users_typing_handler = MessageHandler(Filters.text, handle_users_reply)
    users_location_handler = MessageHandler(Filters.location, 
                                                        choice_of_delivery)
    precheckout_handler = PreCheckoutQueryHandler(precheckout_callback)
    successful_payment_handler = MessageHandler(Filters.successful_payment, 
                                                successful_payment_callback)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(users_reply_handler)
    dispatcher.add_handler(users_typing_handler)
    dispatcher.add_handler(users_location_handler)
    dispatcher.add_handler(precheckout_handler)
    dispatcher.add_handler(successful_payment_handler)

    dispatcher.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
