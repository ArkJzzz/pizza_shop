__author__ = 'ArkJzzz (arkjzzz@gmail.com)'


import json
import logging
import textwrap

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram import KeyboardButton
from telegram import ReplyKeyboardMarkup
from telegram_bot_pagination import InlineKeyboardPaginator

import ext_helpers

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
        data_pattern='PAGE|{page}'
    )

    paginator.add_after(
        InlineKeyboardButton(
            text='🛒 корзина', 
            callback_data='SHOW_CART'
        )
    )

    for product in pages[current_page - 1]:
        paginator.add_before(
            InlineKeyboardButton(
                text=product['name'], 
                callback_data=f'DESCRIPTION|{product["id"]}',
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
                callback_data='GO_MENU',
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
                callback_data='GO_MENU',
            ),
    ]
    if cart_items['data']:
        footer_buttons.append(
            InlineKeyboardButton(
                text='Оформить заказ', 
                callback_data='CHECKOUT', 
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
                    callback_data=f'REMOVE_ITEM|{item_id}',
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
                callback_data=f'PHONE_CONFIRMED',
            )
        ],
        [
            InlineKeyboardButton(
                text='Ввести заново', 
                callback_data='CHECKOUT',
            ),
        ]
    ]

    return InlineKeyboardMarkup(confirmation_keyboard)


def get_choice_of_delivery_keyboard(delivery_area, delivery_price):
    choice_of_delivery_keyboard = [
        [
            InlineKeyboardButton(
                text='Самовывоз', 
                callback_data=f'PICK_UP',
            )
        ]
    ]
    delivery_button = [
        InlineKeyboardButton(
            text='Доставка', 
            callback_data='DELIVERY',
        )
    ]
    if delivery_area in delivery_price.keys():
        choice_of_delivery_keyboard.append(delivery_button)

    return InlineKeyboardMarkup(choice_of_delivery_keyboard)


if __name__ == '__main__':
    logger.error('Этот скрипт не предназначен для запуска напрямую')