from datetime import datetime


def make_datetime(quarter, year):
    """
    Преобразует квартал и год в соответствующую дату.

    :param quarter: Квартал (1-4)
    :param year: Год
    :return: Дата последнего дня квартала
    """
    quarter = int(quarter)
    year = int(year)
    date_list = [
        datetime(year, 3, 31),
        datetime(year, 6, 30),
        datetime(year, 9, 30),
        datetime(year, 12, 31)
    ]
    return date_list[quarter - 1]