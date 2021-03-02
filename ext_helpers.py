#!/usr/bin/python3
__author__ = 'ArkJzzz (arkjzzz@gmail.com)'


import os
import logging
import redis
import requests
import json
import textwrap

from telegram import LabeledPrice
from geopy import distance

import cms_helpers
import keyboards


logger = logging.getLogger('ext_helpers')

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


def fetch_coordinates_from_address(place):
    base_url = 'https://geocode-maps.yandex.ru/1.x'
    params = {
        'geocode': place, 
        'apikey': os.getenv('YANDEX_GEOCODER_API_KEY'), 
        'sco': 'longlat', 
        'format': 'json',
    }
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    response = response.json()
    places_found = response['response']['GeoObjectCollection']['featureMember']
    if places_found:
        most_relevant = places_found[0]
        return most_relevant['GeoObject']['Point']['pos']


def extract_coordinates(message):
    logger.debug('extract_coordinates')
    
    if message.location:
        logger.debug(f'message.location: {message.location}')
        lon = message.location.longitude
        lat = message.location.latitude
        logger.debug(f'location: lat {lat}, lon {lon}')
        return (lat, lon)

    elif message.text:
        logger.debug(f'message.text: {message.text}')
        location = fetch_coordinates_from_address(message.text)
        if location:
            lon, lat = location.split(' ')
            logger.debug(f'location: lat {lat}, lon {lon}')
            return (lat, lon)


def get_nearest_pizzeria(user_location):
    pizzerias = cms_helpers.get_all_entries('pizzeria')
    distance_to_pizzerias = []
    for pizzeria in pizzerias['data']:
        pizzeria_location = (pizzeria['latitude'], pizzeria['longitude'])
        distance_to_pizzeria = distance.distance(
                user_location, 
                pizzeria_location,
            ).km
        distance_to_pizzerias.append((pizzeria['id'], distance_to_pizzeria))

    def get_distance(distance_to_pizzeria):
        return distance_to_pizzeria[1]

    return min(distance_to_pizzerias, key=get_distance)


def get_delivery_area(distance_to_pizzeria, delivery_radius):
    if distance_to_pizzeria < delivery_radius['SHORT']:
        return 'SHORT'

    elif (delivery_radius['SHORT'] < 
                            distance_to_pizzeria <
                                            delivery_radius['MIDDLE']):
        return 'MIDDLE'

    elif (delivery_radius['MIDDLE'] < 
                            distance_to_pizzeria <
                                            delivery_radius['LONG']):
        return 'LONG'

    else:
        return 'FAR_AWAY'


def get_labeled_prices(cart_items, delivery_price=None):
    prices = []
    for item in cart_items['data']:
        item_name = item['name']
        display_price = item['meta']['display_price']
        item_price = display_price['with_tax']['unit']['amount']
        prices.append(LabeledPrice(item_name, item_price))

    if delivery_price:
        prices.append(LabeledPrice('Доставка', delivery_price * 100))

    return prices


def formatting_for_markdown(text):
    escaped_characters = [
        '[', ']', '(', ')', '~', '`', '>', '#', 
        '+', '-', '=', '|', '{', '}', '.', '!',
    ]

    for character in escaped_characters:
        text = text.replace(character, '\\' + character)

    return text


def format_cart(cart_items):
    cart_price = cart_items['meta']['display_price']['with_tax']['formatted']
    cart_items_for_print = ''
    
    for item in cart_items['data']:
        item_display_price = item['meta']['display_price']['with_tax']
        cart_item_to_print =  f'''
                *{item['name']}*
                {item['description']}
                
                _в заказе: {item['quantity']} шт._
                _на сумму {item_display_price['value']['formatted']}_

            '''
        cart_items_for_print += cart_item_to_print

    formated_cart = f'''
                {cart_items_for_print}
                
                *Сумма заказа: {cart_price}*
            '''
    formated_cart = textwrap.dedent(formated_cart)

    return formatting_for_markdown(formated_cart)


def format_product_info(product_data):
    product_data = product_data['data']
    product_meta = product_data['meta']
    display_price = product_meta['display_price']['with_tax']['formatted']

    formated_info = f'''
            *{product_data['name']}*
            {product_data['description']}

            _Цена: {display_price}_
        '''
    formated_info = textwrap.dedent(formated_info)
    formated_info = formatting_for_markdown(formated_info)

    return formated_info


def get_choice_of_delivery_message(delivery_area, delivery_price):
    if delivery_area in delivery_price.keys():
        delivery_message = f'''
            А можем и доставить за {delivery_price[delivery_area]} рублей 😊
        '''
        return textwrap.dedent(delivery_message)
    else:
        far_away_message = 'Простите, но Ваш адрес вне зоны доставки '\
                            'и мы не сможем привезти заказ к Вам 😔'
        return far_away_message


if __name__ == '__main__':
    logger.error('Этот скрипт не предназначен для запуска напрямую')
