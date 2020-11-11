__author__ = 'ArkJzzz (arkjzzz@gmail.com)'


import json
import logging
import textwrap

from telegram import InlineKeyboardButton
from telegram_bot_pagination import InlineKeyboardPaginator

logger = logging.getLogger('keyboards')


start_keyboard = [
    [
        InlineKeyboardButton(
            text='Загляните в наше меню', 
            callback_data='HANDLE_MENU',
        )
    ],
]


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

    return product_details_keyboard


def get_cart_show_keyboard(cart_items):
    cart_show_keyboard = []
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
    cart_show_keyboard.append(
        [
            InlineKeyboardButton(
                text='Продолжить покупки', 
                callback_data='HANDLE_MENU',
            ),
            InlineKeyboardButton(
                text='Оформить заказ', 
                callback_data='HANDLE_CHECKOUT',
            ),
        ],
    )

    return cart_show_keyboard


def get_confirmation_keyboard(email):
    confirmation_keyboard = [
        [
            InlineKeyboardButton(
                text='Все верно', 
                callback_data=f'HANDLE_CREATE_CUSTOMER|{email}',
            )
        ],
        [
            InlineKeyboardButton(
                text='Ввести заново', 
                callback_data='HANDLE_CHECKOUT',
            ),
        ]
    ]

    return confirmation_keyboard


def format_product_info(product_data):
    product_data = product_data['data']
    product_meta = product_data['meta']
    display_price = product_meta['display_price']['with_tax']['formatted']

    formated_info = f'''\
            {product_data['name']}
            {product_data['description']}

            Цена: {display_price}
        '''
    formated_info = textwrap.dedent(formated_info)

    return formated_info


def format_cart(cart_items):
    cart_price = cart_items['meta']['display_price']['with_tax']['formatted']
    cart_items_for_print = ''
    
    for item in cart_items['data']:
        item_display_price = item['meta']['display_price']['with_tax']
        cart_item_to_print =  f'''\
                {item['name']}
                {item["description"]}
                цена: {item_display_price["unit"]["formatted"]}
                
                в заказе: {item["quantity"]}
                на сумму {item_display_price["value"]["formatted"]}

            '''
        cart_item_to_print = textwrap.dedent(cart_item_to_print)
        cart_items_for_print += cart_item_to_print

    formated_cart = f'{cart_items_for_print}\n'\
                    f'Сумма заказа: {cart_price}'

    return formated_cart


if __name__ == '__main__':
    logger.error('Этот скрипт не предназначен для запуска напрямую')