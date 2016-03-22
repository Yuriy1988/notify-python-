def catch_parse_errors(func):
    """
    Catch all exceptions. If there are some return [] otherwise func return value.
    :param func: decorated function.
    :return: func.
    """
    def wrapper():
        try:
            return func()
        except Exception as ex:
            # TODO: add logging
            return []
    return wrapper
