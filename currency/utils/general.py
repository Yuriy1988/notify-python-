from datetime import datetime


def format_currency(currency_dict):
    """
    Returns formatted representation of currency rate.
    :param currency_dict: currency raw data.
    :return: formatted string.
    """
    return '{from_currency}/{to_currency}:\t {rate}'.format(**currency_dict)


def humanize(string):
    """
    Convert solid string with '_' to human readable capitalize format (example: 'ab_cd' -> 'Ab cd')
    :param string: string with '_'
    :return: Humanized string
    """
    words = string.lower().split('_')
    return " ".join(words).capitalize()


def success_update_message(rates, update_errors):
    return "Exchange rates was successfully updated.\n\n{rates}\n\nCommit time (UTC): {date_time}\n\n{update_errors}"\
        .format(
            rates="\n".join(map(format_currency, rates)),
            update_errors="\n".join(update_errors),
            date_time=datetime.utcnow(),
        )
