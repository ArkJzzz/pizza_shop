__author__ = 'ArkJzzz (arkjzzz@gmail.com)'


import json
import logging
import textwrap

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram import KeyboardButton
from telegram import ReplyKeyboardMarkup
from telegram_bot_pagination import InlineKeyboardPaginator

logger = logging.getLogger('keyboards')



def get_start_keyboard():
    start_keyboard = [
        [
            InlineKeyboardButton(
                text='Перейти в меню', 
                callback_data='HANDLE_MENU',
            )
        ],
    ]

    return InlineKeyboardMarkup(start_keyboard)


def get_menu_keyboard(products, current_page, items_per_page=7):
    pages = []
    page = []
    for product in products:
        if len(page) == items_per_page:
            pages.append(page)
            page = []
        else: 
            page.append(product)
    pages.append(page)

    paginator = InlineKeyboardPaginator(
        len(pages),
        current_page=current_page,
        data_pattern='HANDLE_MENU|PAGE|{page}'
    )

    paginator.add_after(
        InlineKeyboardButton(
            text='🛒 корзина', 
            callback_data='HANDLE_CART'
        )
    )

    for product in pages[current_page - 1]:
        paginator.add_before(
            InlineKeyboardButton(
                text=product['name'], 
                callback_data=f'HANDLE_DESCRIPTION|{product["id"]}',
            )
        )

    return paginator.markup


def get_product_details_keyboard(product_id):
    product_details_keyboard = [
        [
            InlineKeyboardButton(
                text='Добавить в заказ', 
                callback_data=f'ADD_TO_CART|{product_id}'
            ),
        ],
        [
            InlineKeyboardButton(
                text='В меню', 
                callback_data='HANDLE_MENU',
            )
        ]
    ]

    return InlineKeyboardMarkup(product_details_keyboard)


def get_cart_show_keyboard(cart_items):
    logger.debug(cart_items)
    cart_show_keyboard = []
    footer_buttons = [
        InlineKeyboardButton(
                text='Продолжить покупки', 
                callback_data='HANDLE_MENU',
            ),
    ]
    if cart_items['data']:
        footer_buttons.append(
            InlineKeyboardButton(
                text='Оформить заказ', 
                callback_data='HANDLE_WAITING_PHONE', 
            ),
        )
    for item in cart_items['data']:
        item_name = item['name']
        item_id = item['id']
        product_id = item['product_id']
        cart_show_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f'Удалить из корзины {item_name}',
                    callback_data=f'HANDLE_REMOVE_ITEM|{item_id}',
                )
            ],
        )
    cart_show_keyboard.append(footer_buttons)

    return InlineKeyboardMarkup(cart_show_keyboard)


def get_confirm_phone_keyboard():
    confirmation_keyboard = [
        [
            InlineKeyboardButton(
                text='Да, звонить на этот номер', 
                callback_data=f'HANDLE_WAITING_LOCATION',
            )
        ],
        [
            InlineKeyboardButton(
                text='Ввести заново', 
                callback_data='HANDLE_WAITING_PHONE',
            ),
        ]
    ]

    return InlineKeyboardMarkup(confirmation_keyboard)


def get_choice_of_delivery_keyboard(delivery_area, delivery_price):
    choice_of_delivery_keyboard = [
        [
            InlineKeyboardButton(
                text='Самовывоз', 
                callback_data=f'HANDLE_PICK_UP',
            )
        ]
    ]

    delivery_button = [
        InlineKeyboardButton(
            text='Доставка', 
            callback_data='HANDLE_DELIVERY',
        )
    ]

    if delivery_area in delivery_price.keys():
        choice_of_delivery_keyboard.append(delivery_button)

    return InlineKeyboardMarkup(choice_of_delivery_keyboard)


def get_choice_of_delivery_message(delivery_area, delivery_price):
    if delivery_area in delivery_price.keys():
        delivery_message = f'''\
            А можем и доставить за {delivery_price[delivery_area]} рублей 😊
        '''
        delivery_message = textwrap.dedent(delivery_message)
        return delivery_message
    else:
        far_away_message = ''\
            'Простите, но Ваш адрес вне зоны доставки '\
            'и мы не сможем привезти заказ к Вам 😔'
        return far_away_message


def format_product_info(product_data):
    product_data = product_data['data']
    product_meta = product_data['meta']
    display_price = product_meta['display_price']['with_tax']['formatted']

    formated_info = f'''\
            *{product_data['name']}*
            {product_data['description']}

            _Цена: {display_price}_
        '''
    formated_info = textwrap.dedent(formated_info)
    formated_info = formatting_for_markdown(formated_info)

    return formated_info


def format_cart(cart_items):
    cart_price = cart_items['meta']['display_price']['with_tax']['formatted']
    cart_items_for_print = ''
    
    for item in cart_items['data']:
        item_display_price = item['meta']['display_price']['with_tax']
        cart_item_to_print =  f'''\
                *{item['name']}*
                {item['description']}
                
                _в заказе: {item['quantity']} шт._
                _на сумму {item_display_price['value']['formatted']}_

            '''
        cart_item_to_print = textwrap.dedent(cart_item_to_print)
        cart_items_for_print += cart_item_to_print

    formated_cart = f'{cart_items_for_print}\n'\
                    f'*Сумма заказа: {cart_price}*'

    formated_cart = formatting_for_markdown(formated_cart)

    return formated_cart


def formatting_for_markdown(text):
    escaped_characters = [
        '[', ']', '(', ')', '~', '`', '>', '#', 
        '+', '-', '=', '|', '{', '}', '.', '!',
    ]

    for character in escaped_characters:
        text = text.replace(character, '\\' + character)

    return text


if __name__ == '__main__':
    logger.error('Этот скрипт не предназначен для запуска напрямую')