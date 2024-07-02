import argparse
import os
import sys
from time import time_ns
from matplotlib import pyplot as plt
from dotenv import load_dotenv
import matplotlib.font_manager as font_manager
import seaborn as sns

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


    df = add_missing_dates(df, dates, 'остаток')
    df.sort_values(by='дата', inplace=True)

    plt.figure(figsize=(8, 7))
    bars = sns.barplot(x='дата', y='остаток', hue='дата', palette='Reds', data=df, legend=False)

    font = font_manager.FontProperties(family='serif', style='italic')
    font1 = font_manager.FontProperties(family='serif',style='italic', size=16)

    # Add labels to the bars, using the x-axis values and y-axis values
    for p in bars.patches:
        plt.text(p.get_x() + p.get_width()/2., p.get_height(), f'{p.get_height():.2f}',
                 ha='center', va='bottom', fontsize=10, fontproperties=font)

    plt.xlabel('Дата', fontsize=14, fontproperties=font)
    plt.ylabel('Остатки', ha= 'center', fontsize=14, fontproperties=font)
    plt.title('Остатки за период в конце квартала', fontproperties=font1)

    plt.xticks(rotation=45, ha='center', fontsize=10, fontproperties=font)
    plt.yticks(fontsize=12, fontstyle= 'italic',fontproperties=font)


    file_name = "/backend/src/main/java/ru/hackaton/python_scripts/images/" + str(time_ns()) + '.png'
    plt.savefig(file_name)

    return (f"По имеющимся данным на {df.iloc[-1]['дата'].strftime('%d.%m.%Y')} осталось "
            f"{int(df.iloc[-1]['остаток'])} ед. товара.\n") + file_name


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some arguments.')
    parser.add_argument('item_name', type=str)
    args = parser.parse_args()
    print(make_plot_of_remainings(args.item_name))