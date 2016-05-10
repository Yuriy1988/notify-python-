import logging
import asyncio
import aiohttp
import itertools
from aiohttp.errors import ClientError
from decimal import Decimal, getcontext
from bs4 import BeautifulSoup, CData

__author__ = 'Kostel Serhii'


_log = logging.getLogger(__name__)

# Currency rate precision
getcontext().prec = 6


class CurrencyError(Exception):
    pass


class CurrencyLoadError(CurrencyError):
    pass


class CurrencyParseError(CurrencyError):
    pass


async def _get_page(url):
    """
    Load html page async.
    :param url: page url
    :return: page html content or None on error
    """
    _log.debug('Load page url: %s', url)
    try:
        with aiohttp.ClientSession() as session:
            with aiohttp.Timeout(10):
                async with session.get(url) as response:
                    rest_status = response.status
                    resp_body = await response.text()

    except (TimeoutError, ClientError) as err:
        _log.critical('HTTP Page Loader request error: %r', err)
        return None

    if rest_status != 200:
        _log.error('HTTP Page Loader wrong status %d', rest_status)
        return None

    return resp_body


async def _parse_currency_from_alpha_bank():
    """
    Parse currency from Alpha Bank html page.
    Get exchange rate (as coefficient) for:
        EUR -> RUB
        USD -> RUB
        RUB -> EUR
        RUB -> USD

    :return list with dict(from_currency, to_currency, rate)
    :raise CurrencyLoadError, CurrencyParseError
    """
    url = "https://alfabank.ru/_/rss/_currency.html"

    _log.debug('Load and parse currency from Alpha bank html page')

    page_html = await _get_page(url)
    if page_html is None:
        _log.error('Error loading page for Alpha Bank parser. Skip Parsing!')
        raise CurrencyLoadError('Error loading page for Alpha Bank (%s)' % url)

    try:
        page_soup = BeautifulSoup(page_html, "html.parser")

        for cd in page_soup.findAll(text=True):
            if isinstance(cd, CData):
                cd_data = cd.encode('cp1251')
                page_soup = BeautifulSoup(cd_data, "html.parser")

        # EUR -> RUB
        eur_rub_buy = page_soup.find('td', {'id': 'ЕвроnoncashBuy'}).text
        eur_rub_rate = Decimal(eur_rub_buy.replace(',', '.'))

        # USD -> RUB
        usd_rub_buy = page_soup.find('td', {'id': 'Доллар СШАnoncashBuy'}).text
        usd_rub_rate = Decimal(usd_rub_buy.replace(',', '.'))

        # RUB -> EUR
        eur_rub_sale = page_soup.find('td', {'id': 'ЕвроnoncashSell'}).text
        rub_eur_rate = Decimal(1)/Decimal(eur_rub_sale.replace(',', '.'))

        # RUB -> USD
        usd_rub_sale = page_soup.find('td', {'id': 'Доллар СШАnoncashSell'}).text
        rub_usd_rate = Decimal(1)/Decimal(usd_rub_sale.replace(',', '.'))

    except Exception as err:
        _log.error('Error parsing currency from Alpha bank: %r', err)
        raise CurrencyParseError('Error parsing currency from Alpha bank (%s)' % url)

    return [
        dict(from_currency='EUR', to_currency='RUB', rate=str(eur_rub_rate)),
        dict(from_currency='USD', to_currency='RUB', rate=str(usd_rub_rate)),
        dict(from_currency='RUB', to_currency='EUR', rate=str(rub_eur_rate)),
        dict(from_currency='RUB', to_currency='USD', rate=str(rub_usd_rate)),
    ]


async def _parse_currency_from_privat_bank():
    """
    Parse currency from Privat Bank html page.
    Get exchange rate (as coefficient) for:
        EUR -> UAH
        USD -> UAH
        RUB -> UAH
        UAH -> EUR
        UAH -> USD
        UAH -> RUB

    :return list with dict(from_currency, to_currency, rate)
    :raise CurrencyLoadError, CurrencyParseError
    """
    url = "https://api.privatbank.ua/p24api/pubinfo?exchange&coursid=5"

    _log.debug('Load and parse currency from Privat bank html page')

    page_html = await _get_page(url)
    if not page_html:
        _log.error('Error load page for Privat Bank parser. Skip Parsing!')
        raise CurrencyLoadError('Error loading page for Privat Bank (%s)' % url)

    try:
        page_soup = BeautifulSoup(page_html, "html.parser")
        exchanges = (currency.attrs for currency in page_soup.findAll('exchangerate'))

        exchange_UAH = {exch['ccy']: exch for exch in exchanges if exch['base_ccy'] == 'UAH'}
        if 'RUR' in exchange_UAH:
            exchange_UAH['RUB'] = exchange_UAH['RUR']

        # EUR -> UAH
        eur_uah_rate = Decimal(exchange_UAH['EUR']['buy'])

        # USD -> UAH
        usd_uah_rate = Decimal(exchange_UAH['USD']['buy'])

        # RUB -> UAH
        rub_uah_rate = Decimal(exchange_UAH['RUB']['buy'])

        # UAH -> EUR
        uah_eur_rate = Decimal(1)/Decimal(exchange_UAH['EUR']['sale'])

        # UAH -> USD
        uah_usd_rate = Decimal(1)/Decimal(exchange_UAH['USD']['sale'])

        # UAH -> RUB
        uah_rub_rate = Decimal(1)/Decimal(exchange_UAH['RUB']['sale'])

    except Exception as err:
        _log.error('Error parsing currency from Privat bank: %r', err)
        raise CurrencyParseError('Error parsing currency from Privat Bank (%s)' % url)

    return [
        dict(from_currency='EUR', to_currency='UAH', rate=str(eur_uah_rate)),
        dict(from_currency='USD', to_currency='UAH', rate=str(usd_uah_rate)),
        dict(from_currency='RUB', to_currency='UAH', rate=str(rub_uah_rate)),
        dict(from_currency='UAH', to_currency='EUR', rate=str(uah_eur_rate)),
        dict(from_currency='UAH', to_currency='USD', rate=str(uah_usd_rate)),
        dict(from_currency='UAH', to_currency='RUB', rate=str(uah_rub_rate)),
    ]

async def parse_currency():
    """
    Connect all parsers result together
    """
    parsers = (_parse_currency_from_alpha_bank, _parse_currency_from_privat_bank)
    parse_res = await asyncio.gather(*[parse_func() for parse_func in parsers])
    return list(itertools.chain(parse_res)) if all(parse_res) else []



# TODO: need research. Which exchange rate are exactly needed.
# # Парсим https://www.alfabank.by/personal/currency/
# page3 = requests.get("https://www.alfabank.by/personal/currency/")
# soup3 = BeautifulSoup(page3.text, "html.parser")
#
# cross_rate = soup3.find('cross_rate', {'code': '5'})
# cross_rate_record = cross_rate.find('cross_rate_record', {'mnem': 'EUR/USD'})
# # Получаем соотношение евро к доллару (продажа)
# eur_usd_sale = cross_rate_record['rate']


if __name__ == '__main__':

    logging.basicConfig(datefmt='%Y-%m-%d %H:%M:%S', level='DEBUG')

    async def parser():
        currency = await parse_currency()
        logging.info('Currency: %r', currency)

    loop = asyncio.get_event_loop()

    logging.info(' [*] Start')
    loop.run_until_complete(parser())

    logging.info(' [*] Stopped')
    loop.close()
