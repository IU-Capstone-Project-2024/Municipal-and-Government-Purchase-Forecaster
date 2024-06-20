import argparse
import os
import sys
from time import time_ns
from matplotlib import pyplot as plt
from dotenv import load_dotenv

# Получаем текущий каталог и корень проекта для установки правильного пути системы.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
dotenv_path = os.path.join(project_root, 'variables.env')
sys.path.append(project_root)

load_dotenv(dotenv_path)


from utils.data_scripts import get_mongo_collection, fetch_data, aggregate_data, create_dataframe, \
    add_missing_dates


def make_plot_of_remainings(name):
    """
    Генерирует график остатков товара по времени для заданного названия продукта и отображает его.

    Аргументы:
        name (str): Название продукта, для которого необходимо сгенерировать график.

    Возвращает:
        dict: Содержит последнюю дату и соответствующий 'остаток'.
    """
    collection = get_mongo_collection('Оборотная ведомость')
    data, dates = fetch_data(collection, name)
    aggregated_data = aggregate_data(data, "единиц после")
    df = create_dataframe(aggregated_data, ['остаток', 'дата'])

    if df.empty:
        return "Извините, данные оборотной ведомости не найдены для данного товара, невозможно предсказать потребление."

    plt.rcParams.update({
        'font.size': 14,
        'font.family': 'serif',
        'axes.titlesize': 20,
        'axes.labelsize': 16,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'figure.titlesize': 22
    })

    df = add_missing_dates(df, dates, 'остаток')
    df.sort_values(by='дата', inplace=True)

    plt.figure(figsize=(8, 7))
    plt.bar(df['дата'].dt.strftime('%Y-%m'), df['остаток'], color='blue')
    plt.xlabel('Дата')
    plt.ylabel('Остатки')
    plt.title('Остатки за период в конце квартала')
    plt.xticks(rotation=45, ha='center')
    file_name = "/backend/src/main/java/ru/hackaton/python_scripts/images/" + str(time_ns()) + '.png'
    plt.savefig(file_name)

    return (f"По имеющимся данным на {df.iloc[-1]['дата'].strftime('%d.%m.%Y')} осталось "
            f"{int(df.iloc[-1]['остаток'])} ед. товара.\n") + file_name


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some arguments.')
    parser.add_argument('item_name', type=str)
    args = parser.parse_args()
    print(make_plot_of_remainings(args.item_name))