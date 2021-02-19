#!/usr/bin/python3
__author__ = 'ArkJzzz (arkjzzz@gmail.com)'


import logging
import json
import os
import requests

from dotenv import load_dotenv

import cms_helpers
from download_picture import download_picture


logger = logging.getLogger('init_pizzeria')

MENU_FILE = 'static/menu.json'
ADDRESSES_FILE = 'static/addresses.json'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def clear_catalogue():
    products = cms_helpers.get_products()
    for product in products['data']:
        result = cms_helpers.delete_product(product["id"])
        logger.debug(result)


def send_product_to_store(item):
    product = cms_helpers.create_product(item)
    
    item_image_file = download_picture(
        url=item['product_image']['url'], 
        directory=os.path.join(BASE_DIR, 'images'), 
        filename='product_img',
    )
    product_image = cms_helpers.create_file(item_image_file, 
                                                        'product_img.jpeg')
    os.remove(item_image_file)
    
    product_id = product['data']['id']
    product_image_id = product_image['data']['id']
    cms_helpers.create_main_image_relationship(product_id, product_image_id)


def main():

    formatter = logging.Formatter(
            fmt='\n%(asctime)s %(name)s:%(lineno)d - %(message)s',
            datefmt='%Y-%b-%d %H:%M:%S (%Z)',
            style='%',
        )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(f'{__file__}.log')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)

    cms_helpers_logger = logging.getLogger('cms_helpers')
    cms_helpers_logger.addHandler(console_handler)
    cms_helpers_logger.setLevel(logging.DEBUG)

    download_picture_logger = logging.getLogger('download_picture')
    download_picture_logger.addHandler(console_handler)
    download_picture_logger.setLevel(logging.DEBUG)

    load_dotenv()
    delivery_man = os.getenv('TELEGRAM_ADMIN_CHAT_ID')

    clear_catalogue()


    try: 
        with open(MENU_FILE, 'r') as menu_file:
            pizzeria_menu = json.load(menu_file)
        for item in pizzeria_menu:
            send_product_to_the_store(item)

        pizzeria_flow = cms_helpers.create_flow(
                    name='Pizzeria',
                    description='Pizzeria'
                )
        pizzeria_flow_id = pizzeria_flow['data']['id']
        logger.debug(pizzeria_flow_id)

        pizzeria_flow_fields = (
                'Address',
                'Alias',
                'Longitude',
                'Latitude',
                'Delivery_man',
            )
        for field in pizzeria_flow_fields:
            cms_helpers.create_field(
                name=field, 
                description=f'Pizzeria {field}',
                flow_id=pizzeria_flow_id,
            )

        with open(ADDRESSES_FILE, 'r') as addresses_file:
            pizzeries = json.load(addresses_file)
        for pizzeria in pizzeries:
            entry_data = {
                'alias': pizzeria['alias'],
                'address': pizzeria['address']['full'],
                'latitude': pizzeria['coordinates']['lat'],
                'longitude': pizzeria['coordinates']['lon'],
                'delivery_man': delivery_man,
            }
            cms_helpers.create_entry('Pizzeria', entry_data)

        customer_address_flow = cms_helpers.create_flow(
                name='Customer Address',
                description='Customer Address',
            )
        customer_address_flow_id = customer_address_flow['data']['id']
        logger.debug(customer_address_flow_id)

        customer_address_flow_fields = (
                'telegram_id',
                'phone',
                'latitude',
                'longitude',
            )
        for field in customer_address_flow_fields:
            cms_helpers.create_field(
                name=field,
                description=f'Customer Address {field}',
                flow_id=customer_address_flow_id,
            )

    except:
        logger.exception('')


if __name__ == '__main__':
    main()
