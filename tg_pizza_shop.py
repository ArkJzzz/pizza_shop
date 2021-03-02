__author__ = 'ArkJzzz (arkjzzz@gmail.com)'

import os
import logging
import textwrap

from dotenv import load_dotenv
from telegram import ParseMode
from telegram.ext import Filters
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import CallbackQueryHandler
from telegram.ext import MessageHandler
from telegram.ext import PreCheckoutQueryHandler
import phonenumbers
import redis

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
        chat_id = update.message.chat_id
        if update.message.location:
            user_reply = update.message.location
        else:
            user_reply = update.message.text
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return

    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.hget(
            name='pizzeria_users_states',
            key=chat_id,
        ).decode("utf-8")

    logger.debug(f'user_reply: {user_reply}')
    logger.debug(f'user_state: {user_state}')
    
    states_functions = {
        'START': start,
        'HANDLE_MENU': show_menu,
        'HANDLE_DESCRIPTION': show_description,
        'HANDLE_CART': show_cart,
        'HANDLE_WAITING_PHONE': waiting_phone,
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
    logger.error(message, exc_info=context.error)

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
    update.message.reply_text(
        text=textwrap.dedent(welcome_message),
        reply_markup=keyboards.get_start_keyboard(),
    )

    return 'HANDLE_MENU'


def show_menu(update, context):
    logger.debug('show_menu')
    logger.debug(f'query.data: {update.callback_query.data}')
    logger.debug(f'user_data: {context.user_data}')

    query = update.callback_query

    if 'DESCRIPTION' in query.data:
        show_description(update, context)
        return 'HANDLE_DESCRIPTION'
    
    elif 'SHOW_CART' in query.data:
        show_cart(update, context)
        return 'HANDLE_CART'

    else:
        if 'PAGE' in query.data:
            pattern, current_page = query.data.split('|')
            current_page = int(current_page)
        else:
            current_page = 1

        products = cms_helpers.get_products()
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

        return 'HANDLE_MENU'


def show_description(update, context):
    logger.debug('show_description')
    logger.debug(f'query.data: {update.callback_query.data}')
    logger.debug(f'user_data: {context.user_data}')

    query = update.callback_query
    chat_id = query.message.chat_id

    if 'DESCRIPTION' in query.data:
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
        return 'HANDLE_DESCRIPTION'

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

    else:
        show_menu(update, context)
        return 'HANDLE_MENU'        


def show_cart(update, context):
    logger.debug('show_cart')
    logger.debug(f'query.data: {update.callback_query.data}')
    logger.debug(f'user_data: {context.user_data}')

    query = update.callback_query
    chat_id = query.message.chat_id

    if 'CHECKOUT' in query.data:
        query.message.reply_text(
            text='Напишите свой номер телефона',
        )
        return 'HANDLE_WAITING_PHONE'

    elif 'GO_MENU' in query.data:
        show_menu(update, context)
        return 'HANDLE_MENU' 

    else:
        if 'REMOVE_ITEM' in query.data:
            user_reply, item_id = query.data.split('|')
            logger.debug(f'Удаление товара с id {item_id}')
            cms_helpers.remove_cart_item(chat_id, item_id)
            context.bot.answer_callback_query(
                callback_query_id=query.id, 
                text='Товар удален из корзины', 
            )
        cart_items = cms_helpers.get_cart_items(chat_id)
        logger.debug(f'Товары в корзине: {cart_items}')
        query.message.reply_text(
            text=ext_helpers.format_cart(cart_items),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboards.get_cart_show_keyboard(cart_items),
        )
        context.bot.delete_message(
            chat_id=chat_id,
            message_id=query.message.message_id,
        )

        return 'HANDLE_CART'


def waiting_phone(update, context):
    logger.debug('waiting_phone')
    logger.debug(f'user_data: {context.user_data}')

    if update.callback_query:
        logger.debug(f'query.data: {update.callback_query.data}')
        query = update.callback_query
        
        if 'PHONE_CONFIRMED' in query.data:
            waiting_location_message = '''\
                Напишите адрес доставки или отправьте геопозицию
                '''
            query.message.reply_text(
                text=textwrap.dedent(waiting_location_message),
            )
            return 'HANDLE_WAITING_LOCATION'
        else:
            query.message.reply_text(
                text='Напишите свой номер телефона',
            )
            return 'HANDLE_WAITING_PHONE'

    elif update.message.text:
        logger.debug(f'user_reply: {update.message.text}')
        user_reply = update.message.text
        phone = phonenumbers.parse(user_reply, 'RU')

        if phonenumbers.is_valid_number(phone):
            logger.debug('phone valid')
            phone = f'+{phone.country_code}{phone.national_number}'
            context.user_data['phone'] = phone
            update.message.reply_text(
                text=f'ваш номер телефона: {phone}',
                reply_markup=keyboards.get_confirm_phone_keyboard(),
            )
        else:
            invalid_phone_message = '''\
                    Кажется, номер неправильный.
                    Попробуйте снова.
                '''
            update.message.reply_text(
                text=textwrap.dedent(invalid_phone_message), 
            )
            
        return 'HANDLE_WAITING_PHONE'
  

def waiting_location(update, context):
    logger.debug('waiting_location')
    logger.debug(f'user_data: {context.user_data}')
    logger.debug(f'user_reply: {update.message.text}')

    user_location = ext_helpers.extract_coordinates(update.message)
    if not user_location:
        reply_text = '''
            Не удалось определить адрес доставки.
            Попробуйте еще раз.
        '''
        update.message.reply_text(
            text=textwrap.dedent(reply_text)
            )
        return 'HANDLE_WAITING_LOCATION'
    else: 
        context.user_data['location'] = user_location
        choice_of_delivery(update, context)
        return 'HANDLE_CHOICE_OF_DELIVERY'


def choice_of_delivery(update, context):
    logger.debug('choice_of_delivery')
    logger.debug(f'user_data: {context.user_data}')

    if update.callback_query:

        if 'PICK_UP' in update.callback_query.data:
            context.user_data['delivery'] = False
            pick_up(update, context)
            return 'HANDLE_PICK_UP'

        elif 'DELIVERY' in update.callback_query.data:
            context.user_data['delivery'] = True
            delivery(update, context)
            return 'HANDLE_DELIVERY'

    else:
        nearest_pizzeria = ext_helpers.get_nearest_pizzeria(
                                            context.user_data['location'])
        pizzeria_id, distance_to_pizzeria = nearest_pizzeria
        context.user_data['nearest_pizzeria_id'] = pizzeria_id
        delivery_area = ext_helpers.get_delivery_area(distance_to_pizzeria, 
                                                            DELIVERY_RADIUS)
        logger.debug(f'delivery_area: {delivery_area}')
        pizzeria = cms_helpers.get_an_entry('pizzeria', pizzeria_id)
        pizzeria_address = pizzeria['data']['address']
        logger.debug(f'pizzeria_address: {pizzeria_address}')

        pick_up_message = f'''
                Вы можете забрать заказ из ближайшей пиццерии по адресу:
                {pizzeria_address}.

                Она в {round(distance_to_pizzeria, 2)} км от Вас.
            '''
        delivery_message = ext_helpers.get_choice_of_delivery_message(
                                            delivery_area, DELIVERY_PRICE)
        choice_of_delivery_message = f'''
                {textwrap.dedent(pick_up_message)} {delivery_message}
            '''
        update.message.reply_text(
            text=textwrap.dedent(choice_of_delivery_message),
            reply_markup=keyboards.get_choice_of_delivery_keyboard(
                                            delivery_area, DELIVERY_PRICE),
        )

        return 'HANDLE_CHOICE_OF_DELIVERY'


def pick_up(update, context):
    logger.debug('pick_up')
    logger.debug(f'user_data: {context.user_data}')

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


def delivery(update, context):
    logger.debug('delivery')
    logger.debug(f'user_data: {context.user_data}')

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

    if context.user_data['delivery']:
        successful_payment_message = '''
                Спасибо что выбрали нас!

                Курьер доставит ваш заказ в течение часа.
            '''

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
        successful_payment_message = f'''
                Спасибо что выбрали нас!

                Вы можете забрать заказ из ближайшей пиццерии по адресу:
                {pizzeria_address}.'
            '''

    update.message.reply_text(
        text=textwrap.dedent(successful_payment_message),
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
                                                        handle_users_reply)
    precheckout_handler = PreCheckoutQueryHandler(precheckout_callback)
    successful_payment_handler = MessageHandler(Filters.successful_payment, 
                                                successful_payment_callback)

    dispatcher = updater.dispatcher
    dispatcher.add_error_handler(error_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(users_reply_handler)
    dispatcher.add_handler(users_typing_handler)
    dispatcher.add_handler(users_location_handler)
    dispatcher.add_handler(precheckout_handler)
    dispatcher.add_handler(successful_payment_handler)  

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
