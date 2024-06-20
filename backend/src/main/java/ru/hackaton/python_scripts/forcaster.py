import argparse

import pandas as pd

from math import ceil
from time import time_ns
from datetime import datetime
from matplotlib import pyplot as plt
from pmdarima import auto_arima

from utils.data_scripts import get_mongo_collection, fetch_data, aggregate_data, create_dataframe, add_missing_dates, \
    mongo_find

ABSOLUTE_PATH = "/backend/src/main/java/ru/hackaton/python_scripts/"

def purchase(months, forecast):
    """
    Рассчитывает сумму закупок за заданное количество месяцев.

    :param months: Количество месяцев
    :param forecast: Прогноз потребления
    :return: Сумма закупок
    """
    sum_of_purchase = 0.
    for quarter in range(months // 3):
        sum_of_purchase += float(forecast.iloc[quarter])
    if months > (months // 3) * 3:
        sum_of_purchase += float(forecast.iloc[months // 3]) * (months - (months // 3) * 3) / 3
    return sum_of_purchase


def plot_forecast(df_forecast, filename):
    """
    Строит график прогноза потребления.

    :param df_forecast: DataFrame с прогнозом потребления
    """
    plt.rcParams.update({
        'font.size': 14,
        'font.family': 'serif',
        'axes.titlesize': 20,
        'axes.labelsize': 16,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'figure.titlesize': 22
    })
    plt.figure(figsize=(8, 7))
    if len(df_forecast) == 1:
        plt.xlim(-2, 2)
    plt.bar(df_forecast['дата'].dt.strftime('%Y-%m'), df_forecast['прогноз'], color='blue', width=0.4, edgecolor='black')
    plt.xlabel('Дата')
    plt.ylabel('Прогноз потребления')
    plt.title('Прогноз потребления на конец каждого квартала')
    plt.xticks(rotation=45, ha='center')
    plt.savefig(filename)


def make_forecast(name, months):
    """
    Делает прогноз потребления на заданное количество месяцев.

    :param name: Название продукта
    :param months: Количество месяцев для прогноза
    :return: Прогноз потребления или сообщение об ошибке
    """
    collection = get_mongo_collection("Оборотная ведомость")
    name = name.lower().replace(" ", "")
    data, dates = fetch_data(collection, name)
    aggregated_data = aggregate_data(data, "единиц кредит во")
    df = create_dataframe(aggregated_data, ['Kredit', 'дата'])

    if df.empty:
        return "Извините, данные оборотной ведомости не найдены для данного товара, невозможно предсказать потребление."

    df = add_missing_dates(df, dates, 'Kredit')
    df.sort_values(by='дата', inplace=True)
    plt.rcParams.update({
        'font.size': 14,
        'font.family': 'serif',
        'axes.titlesize': 20,
        'axes.labelsize': 16,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'figure.titlesize': 22
    })
    plt.figure(figsize=(8, 7))
    plt.bar(df['дата'].dt.strftime('%Y-%m'), df['Kredit'], color='blue', width=0.4)
    plt.xlabel('Дата')
    plt.ylabel('Потребление')
    plt.title('Известное потребление за период в конце квартала')
    plt.xticks(rotation=45, ha='center')
    known_consume_filename = ABSOLUTE_PATH + "images/" + str(time_ns()) + ".png"
    plt.savefig(known_consume_filename)
    if pd.notna(df['Kredit']).sum() == 0 or df['Kredit'].max() == 0:
        return ("Извините, кажется, данный товар не тратился в течение всего времени, невозможно предсказать "
                "потребление.")
    df.set_index('дата', inplace=True)
    model = auto_arima(df, seasonal=True, stepwise=True, trace=False, m=4, D=0)
    forecast = model.predict(n_periods=ceil(months / 3))
    forecast = forecast.apply(lambda x: round(x))

    if forecast.max() == 0:
        return "Кажется данный товар редко используется, невозможно предсказать потребление.\n" + known_consume_filename

    df_forecast = pd.DataFrame(
        {'дата': pd.date_range(start=forecast.index[0], periods=len(forecast), freq='Q'), 'прогноз': forecast})
    predict_consume_filename = ABSOLUTE_PATH + "images/" + str(time_ns()) + ".png"
    if months % 3 == 0:
        plot_forecast(df_forecast, predict_consume_filename)
    else:
        monthly_consuming = pd.DataFrame(columns=['дата', 'прогноз'])
        for index, row in df_forecast.iterrows():
            avg_consuming = row['прогноз'] / 3
            until_month = 0
            if index == df_forecast.index[-1]:
                until_month = 3 - months % 3
            for month in range(2, until_month - 1, -1):
                monthly_consuming.loc[len(monthly_consuming)] = [row['дата'] - pd.offsets.MonthEnd(month),
                                                                 avg_consuming]
        plt.rcParams.update({
            'font.size': 14,
            'font.family': 'serif',
            'axes.titlesize': 20,
            'axes.labelsize': 16,
            'xtick.labelsize': 12,
            'ytick.labelsize': 12,
            'figure.titlesize': 22
        })
        plt.figure(figsize=(8, 7))
        if months == 1:
            plt.xlim(-2, 2)
        plt.bar(monthly_consuming['дата'].dt.strftime('%Y-%m'), monthly_consuming['прогноз'], color='blue', width=0.4)
        plt.xlabel('Дата')
        plt.ylabel('Прогноз потребления')
        plt.title('Прогноз потребления по месяцам')
        plt.xticks(rotation=45, ha='center')
        plt.savefig(predict_consume_filename)

    remainings_data = mongo_find({"Название": name})
    df = pd.DataFrame(columns=['дата', 'остатки'])
    for document in remainings_data:
        df.loc[len(df)] = [document['Дата'], document['Остаток']]

    df['дата'] = pd.to_datetime(df['дата'], dayfirst=True)
    df.sort_values(by='дата', inplace=True)
    df.reset_index(drop=True, inplace=True)

    if len(df) == 0 or df.iloc[-1]['дата'] < datetime(2022, 12, 31):
        rem = 0.
    else:
        rem = float(df.iloc[-1]['остатки'])

    sum_of_purchase = purchase(months, forecast)
    if sum_of_purchase < rem:
        return "На складе имеется достаточное количество товаров для данного срока.\n" + known_consume_filename + "\n" + predict_consume_filename

    return "Необходимо докупить " + str(ceil((sum_of_purchase - rem) * 1.1)) + " ед. товара.\n" + known_consume_filename + "\n" + predict_consume_filename


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some arguments.')
    parser.add_argument('item_name', type=str)
    parser.add_argument('n_months', type=int)
    args = parser.parse_args()
    print(make_forecast(args.item_name, args.n_months))
