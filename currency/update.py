from requests import post

from currency.parsers import parse_alphabank, parse_privat24


API_HOST = 'http://localhost:7128'
API_URL = API_HOST + '/api/admin/dev/currency/update'


def humanize(string):
    """
    Convert solid string with '_' to human readable capitalize format (example: 'ab_cd' -> 'Ab cd')
    :param string: string with '_'
    :return: Humanized string
    """
    words = string.lower().split('_')
    return " ".join(words).capitalize()


def get_currency_data(**sources):
    parsers = {humanize(key): value for key, value in sources.items()}
    exchange_rates, update_errors = [], []
    for source_name, parser_func in parsers.items():
        new_exchange_rates = parser_func()
        if new_exchange_rates:
            exchange_rates.extend(new_exchange_rates)
        else:
            update_errors.append("Update from {source} failed.".format(source=source_name))
    return exchange_rates, update_errors


def update():
    """
    Update currency data from specified sources and send to xopay-admin.
    :return: (rates, errors) if update succeed otherwise False
    """
    rates, errors = get_currency_data(
        alpha_bank=parse_alphabank,
        privat_bank=parse_privat24,
    )

    # send updates to admin API
    try:
        post(API_URL, json={"update": rates})
    except Exception as ex:  # if connection refused.
        rates = None
        errors.append(ex)

    return rates, errors


if __name__ == '__main__':
    update()
