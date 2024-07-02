import argparse

import pandas as pd

from math import ceil
from time import time_ns
from datetime import datetime
from matplotlib import pyplot as plt
from pmdarima import auto_arima
import matplotlib.font_manager as font_manager
import seaborn as sns

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

    plt.figure(figsize=(8, 7))
    if len(df_forecast) == 1:
        plt.xlim(-2, 2)
    bars = sns.barplot(x='дата', y='прогноз', hue='дата', palette='Reds', data=df_forecast, legend=False)

    font = font_manager.FontProperties(family='serif', style='italic')
    font1 = font_manager.FontProperties(family='serif',style='italic', size=16)

    # Add labels to the bars, using the x-axis values and y-axis values
    for p in bars.patches:
        plt.text(p.get_x() + p.get_width()/2., p.get_height(), f'{p.get_height():.2f}',
                 ha='center', va='bottom', fontsize=10, fontproperties=font)

    plt.xlabel('Дата', fontsize=14, fontproperties=font)
    plt.ylabel('Прогноз потребления', ha= 'center', fontsize=14, fontproperties=font)
    plt.title('Прогноз потребления на конец каждого квартала', fontproperties=font1)

    plt.xticks(rotation=45, ha='center', fontsize=10, fontproperties=font)
    plt.yticks(fontsize=12, fontstyle= 'italic',fontproperties=font)

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

    plt.figure(figsize=(8, 7))


    bars = sns.barplot(x='дата', y='Kredit', hue='дата', palette='Reds', data=df, legend=False)

    font = font_manager.FontProperties(family='serif', style='italic')
    font1 = font_manager.FontProperties(family='serif',style='italic', size=16)

    # Add labels to the bars, using the x-axis values and y-axis values
    for p in bars.patches:
        plt.text(p.get_x() + p.get_width()/2., p.get_height(), f'{p.get_height():.2f}',
                 ha='center', va='bottom', fontsize=10, fontproperties=font)

    plt.xlabel('Дата', fontsize=14, fontproperties=font)
    plt.ylabel('Потребление', ha= 'center', fontsize=14, fontproperties=font)
    plt.title('Известное потребление за период в конце квартала', fontproperties=font1)

    plt.xticks(rotation=45, ha='center', fontsize=10, fontproperties=font)
    plt.yticks(fontsize=12, fontstyle= 'italic',fontproperties=font)


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

        plt.figure(figsize=(8, 7))
        if months == 1:
            plt.xlim(-2, 2)
        plt.bar(monthly_consuming['дата'].dt.strftime('%Y-%m'), monthly_consuming['прогноз'], color='blue', width=0.4)

        bars = sns.barplot(x='дата', y='прогноз', hue='дата', palette='Reds', data=monthly_consuming, legend=False)
        font = font_manager.FontProperties(family='serif', style='italic')
        font1 = font_manager.FontProperties(family='serif',style='italic', size=16)
        # Add labels to the bars, using the x-axis values and y-axis values
        for p in bars.patches:
            plt.text(p.get_x() + p.get_width()/2., p.get_height(), f'{p.get_height():.2f}',
                     ha='center', va='bottom', fontsize=10, fontproperties=font)
        plt.xlabel('Дата', fontsize=14, fontproperties=font)
        plt.ylabel('Прогноз потребления', ha= 'center', fontsize=14, fontproperties=font)
        plt.title('Прогноз потребления по месяцам', fontproperties=font1)
        plt.xticks(rotation=45, ha='center', fontsize=10, fontproperties=font)
        plt.yticks(fontsize=12, fontstyle= 'italic',fontproperties=font)

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