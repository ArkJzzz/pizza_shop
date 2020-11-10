__author__ = 'ArkJzzz (arkjzzz@gmail.com)'

import logging
import os
import requests
import json

from datetime import datetime
from dotenv import load_dotenv


logger = logging.getLogger('cms_helpers')

BASE_URL = 'https://api.moltin.com/v2'

_moltin_autorization_data = None


def get_moltin_autorization():
    load_dotenv()
    moltin_client_id = os.getenv('ELASTICPATH_CLIENT_ID')
    moltin_client_secret = os.getenv('ELASTICPATH_CLIENT_SECRET')
    url = 'https://api.moltin.com/oauth/access_token'
    data = {
      'client_id': moltin_client_id,
      'client_secret': moltin_client_secret,
      'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    logger.debug(response.json())

    return response.json()


def get_moltin_api_token():
    global _moltin_autorization_data
    if _moltin_autorization_data:
        current_time = datetime.utcnow()
        expires = int(_moltin_autorization_data['expires'])
        expires = datetime.utcfromtimestamp(expires)
        if current_time >= expires:
            _moltin_autorization_data = get_moltin_autorization()
    else:
        _moltin_autorization_data = get_moltin_autorization()

    return f'{_moltin_autorization_data["token_type"]} '\
            f'{_moltin_autorization_data["access_token"]}'


def create_product(product_data):
    url = f'{BASE_URL}/products'
    headers = {
        'Authorization': get_moltin_api_token(),
        'Content-Type': 'application/json',
    }
    payload = {
        'data': { 
            'type': 'product',
            'name': product_data['name'],
            'slug': str(product_data['id']),
            'sku': str(product_data['id']),
            'description': product_data['description'],
            'manage_stock': False,
            'price': [
                {
                    'amount': int(product_data['price'])*100,
                    'currency': 'RUB',
                    'includes_tax': True,
                }
            ],
            'status': 'live',
            'commodity_type': 'physical',
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    logger.debug(response.text)
    response.raise_for_status()

    return response.json()


def get_products():
    url = f'{BASE_URL}/products/'
    headers = {
        'Authorization': get_moltin_api_token(),
        'Content-Type': 'application/json',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_product(product_id):
    url = f'{BASE_URL}/products/{product_id}'
    headers = {
        'Authorization': get_moltin_api_token(),
        'Content-Type': 'application/json',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def create_file(file_path):
    url = f'{BASE_URL}/files'
    headers = {
        'Authorization': get_moltin_api_token(),
    }
    files = {
        'file': (file_path, open(file_path, 'rb')),
        'public': True,
    }

    response = requests.post(url, headers=headers, files=files)
    logger.debug(response.text)
    response.raise_for_status()

    return response.json()


def create_main_image_relationship(product_id, image_id):
    url = f'{BASE_URL}/products/{product_id}/relationships/main-image'
    headers = {
        'Authorization': get_moltin_api_token(),
    }
    payload = {
        'data': { 
            'type': 'main_image',
            'id': image_id,
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    return response.json()

def create_flow(name, description):
    url = f'{BASE_URL}/flows'
    headers = {
        'Authorization': get_moltin_api_token(),
    }
    payload = {
        'data': {
            'type': 'flow',
            'name': name,
            'slug': name.lower(),
            'description': description,
            'enabled': True,
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    logger.debug(response.text)
    response.raise_for_status()

    return response.json()


def create_field(name, description, flow_id):
    url = f'{BASE_URL}/fields'
    headers = {
        'Authorization': get_moltin_api_token(),
    }
    payload = {
        'data': {
            'type': 'field',
            'name': name,
            'slug': name.lower().replace(' ', '_'),
            'field_type': 'string',
            'description': description,
            'required': False,
            'enabled': True,
            'relationships': {
                'flow': {
                    'data': {
                        'type': 'flow',
                        'id': flow_id,
                    },
                },
            },
        },
    }
    response = requests.post(url, headers=headers, json=payload)
    logger.debug(response.text)
    response.raise_for_status()

    return response.json()

def create_entry(flow_name, entry_data):
    slug = flow_name.lower().replace(' ', '_')
    url = f'{BASE_URL}/flows/{slug}/entries'
    headers = {
        'Authorization': get_moltin_api_token(),
    }
    entry_data['type'] = 'entry'
    payload = {'data': entry_data}
    
    response = requests.post(url, headers=headers, json=payload)
    logger.debug(response.text)
    response.raise_for_status()

    return response.json()


def get_all_files():
    url = f'{BASE_URL}/files'
    headers = {
        'Authorization': get_moltin_api_token(),
        'Content-Type': 'application/json',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_image_link(image_id):
    url = f'{BASE_URL}/files/{image_id}'
    headers = {
        'Authorization': get_moltin_api_token(),
        'Content-Type': 'application/json',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    file_data = response.json()

    return file_data['data']['link']['href']


def add_product_to_cart(cart_id, product_id, quantity):
    url = f'{BASE_URL}/carts/{cart_id}/items'
    headers = {
        'Authorization': get_moltin_api_token(),
        'Content-Type': 'application/json',
    }
    payload = {
        'data': { 
            'id': product_id,
            'type': 'cart_item',
            'quantity': int(quantity),
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    return response.json()


def get_cart(cart_id):
    url = f'{BASE_URL}/carts/{cart_id}'
    headers = {
        'Authorization': get_moltin_api_token(),
        'Content-Type': 'application/json',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_cart_items(cart_id):
    url = f'{BASE_URL}/carts/{cart_id}/items'
    headers = {
        'Authorization': get_moltin_api_token(),
        'Content-Type': 'application/json',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def delete_cart(cart_id):
    url = f'{BASE_URL}/carts/{cart_id}'
    headers = {
        'Authorization': get_moltin_api_token(),
    }
    response = requests.delete(url, headers=headers)
    response.raise_for_status()

    return response


def remove_cart_item(cart_id, item_id):
    url = f'{BASE_URL}/carts/{cart_id}/items/{item_id}'
    headers = {
        'Authorization': get_moltin_api_token(),
        'Content-Type': 'application/json',
        }
    response = requests.delete(url, headers=headers)
    response.raise_for_status()

    return response.json()


def create_customer(customer_name, email):
    url = f'{BASE_URL}/customers'
    headers = {
        'Authorization': get_moltin_api_token(),
        'Content-Type': 'application/json',
    }
    payload = {
        'data': { 
            'type': 'customer',
            'name': customer_name,
            'email': email,
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    return response.json()


if __name__ == '__main__':
    logger.error('Этот скрипт не предназначен для запуска напрямую')