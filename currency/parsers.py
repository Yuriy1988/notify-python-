from decimal import Decimal

import requests
from bs4 import BeautifulSoup, CData

from currency.utils.decorators import catch_parse_errors


@catch_parse_errors
def parse_alphabank():
    # Парсим alfabank.ru
    page1 = requests.get("https://alfabank.ru/_/rss/_currency.html")
    soup1 = BeautifulSoup(page1.text, "html.parser")

    for cd in soup1.findAll(text=True):
        if isinstance(cd, CData):
            cd_data = cd.encode('cp1251')

    soup1_1 = BeautifulSoup(cd_data, "html.parser")

    # Получаем соотношение евро к рублю (покупка)
    eur_rur_buy = soup1_1.find(
        'td',
        {'id': 'ЕвроnoncashBuy'}
    ).text.replace(',', '.')

    # Получаем соотношение евро к рублю (продажа)
    eur_rur_sale = soup1_1.find(
        'td',
        {'id': 'ЕвроnoncashSell'}
    ).text.replace(',', '.')

    # Получаем соотношение доллара к рублю (покупка)
    usd_rur_buy = soup1_1.find(
        'td',
        {'id': 'Доллар СШАnoncashBuy'}
    ).text.replace(',', '.')

    # Получаем соотношение рубля к доллару (продажа)
    usd_rur_sale = soup1_1.find(
        'td',
        {'id': 'Доллар СШАnoncashSell'}
    ).text.replace(',', '.')

    return [
        dict(
            from_currency='RUB',
            to_currency='EUR',
            rate=str(Decimal(1)/Decimal(eur_rur_sale)),
        ),
        dict(
            from_currency='EUR',
            to_currency='RUB',
            rate=str(Decimal(eur_rur_buy)),
        ),
        dict(
            from_currency='RUB',
            to_currency='USD',
            rate=str(Decimal(1)/Decimal(usd_rur_sale)),
        ),
        dict(
            from_currency='USD',
            to_currency='RUB',
            rate=str(Decimal(usd_rur_buy)),
        )
    ]


@catch_parse_errors
def parse_privat24():
    currency_records = []
    # Парсим https://api.privatbank.ua/p24api/pubinfo?exchange&coursid=5
    page2 = requests.get("https://api.privatbank.ua/p24api/pubinfo?exchange&coursid=5")
    soup2 = BeautifulSoup(page2.text, "html.parser")

    for currency in soup2.findAll('exchangerate'):

        # Obtain exchange rates for UAH (RUR, USD, EUR):
        if currency.attrs['base_ccy'] == 'UAH':
            ccy = currency.attrs.get('ccy')
            ccy = 'RUB' if ccy == 'RUR' else ccy
            currency_records.extend([
                dict(
                    from_currency=currency.attrs.get('base_ccy'),
                    to_currency=ccy,
                    rate=str(Decimal(1)/Decimal(currency.attrs.get('sale'))),
                ),
                dict(
                    from_currency=ccy,
                    to_currency=currency.attrs.get('base_ccy'),
                    rate=str(Decimal(currency.attrs.get('buy'))),
                )]
            )
    return currency_records


# TODO: need research. Which exchange rate are exactly needed.
# # Парсим https://www.alfabank.by/personal/currency/
# page3 = requests.get("https://www.alfabank.by/personal/currency/")
# soup3 = BeautifulSoup(page3.text, "html.parser")
#
# cross_rate = soup3.find('cross_rate', {'code': '5'})
# cross_rate_record = cross_rate.find('cross_rate_record', {'mnem': 'EUR/USD'})
# # Получаем соотношение евро к доллару (продажа)
# eur_usd_sale = cross_rate_record['rate']
