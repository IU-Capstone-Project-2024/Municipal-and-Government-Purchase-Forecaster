import argparse
import re
import string
import pymorphy3
from transformers import BertTokenizer, BertForSequenceClassification
import torch

morph = pymorphy3.MorphAnalyzer()
common_time = {'месяц': 30, 'год': 365, "квартал": 90, "полгода": 180, "лет": 365, "неделя": 7, "день": 1}


def choose_action(question):
    # Загрузка сохраненной модели и токенизатора
    model = BertForSequenceClassification.from_pretrained("/backend/src/main/java/ru/hackaton/python_scripts/saved_model")
    tokenizer = BertTokenizer.from_pretrained("/backend/src/main/java/ru/hackaton/python_scripts/saved_model")

    # Пример нового текста для предсказания
    text = question

    # Токенизация текста
    inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=64)

    # Прогон данных через модель
    model.eval()  # Перевод модели в режим предсказания
    with torch.no_grad():  # Отключение градиентов для ускорения и снижения потребления памяти
        outputs = model(**inputs)

    # Логиты (сырые предсказания модели)
    logits = outputs.logits

    # Предсказание класса
    predictions = torch.argmax(logits, dim=1)

    # Интерпретация предсказания
    return predictions.item()


def classify_product(question):

        text = question


        # Функция для извлечения и нормализации потенциальных товаров с использованием регулярных выражений
        def extract_genitive_plural(text: str):
            # Обновленное регулярное выражение
            matches = re.findall(r'\b\w+(?:ов|ев|ей|ий|ей|й|й|ы|и|ь|г|ж|ч|д|ш|ц|й|ей|ов|ев|ий|р|к|т|а)\b', text.lower())
            return normalize_words(matches)

        def extract_nominative_plural(text: str):
            matches = re.findall(r'\b\w*(?:и|ы|а)\b', text.lower())
            return normalize_words(matches)

        def extract_genitive_singular(text: str):
            matches = re.findall(r'\b\w*(?:ы|и)\b', text.lower())
            return normalize_words(matches)


        def normalize_words(words):
            normalized = []
            for word in words:
                parsed_word = morph.parse(word)

                # Ищем правильный разбор
                for parse in parsed_word:
                    if parse.tag.POS == 'NOUN' and 'Name' not in parse.tag:
                        nominative_singular = parse.inflect({'nomn', 'sing'})
                        if nominative_singular:
                            normalized.append(nominative_singular.word)
                            break  # Прекращаем цикл, как только найдем правильный разбор

            return list(set(normalized))

        def extract_and_normalize_entities(text: str):
            genitive_plural = extract_genitive_plural(text)
            nominative_plural = extract_nominative_plural(text)
            genitive_singular = extract_genitive_singular(text)
            all_extracted = list(set(nominative_plural+ genitive_plural + genitive_singular))
            return all_extracted


        # Извлечение и нормализация потенциальных товаров из каждого запроса

        products = extract_and_normalize_entities(text)
        if 'остаток' in products:
            products.remove('остаток')
        if 'комплект' in products:
            products.remove('комплект')
        for product in products:
            if product in common_time.keys():
                products.remove(product)
        if 'склад' in products:
            products.remove('склад')

        return products[0]

def get_time_interval(mesg):

    common_digits = {
        "один": 1,
        "два": 2,
        "три": 3,
        "четыре": 4,
        "пять": 5,
        "шесть": 6,
        "семь": 7,
        "восемь": 8,
        "девять": 9,
        "десять": 10,
        "одиннадцать": 11,
        "двенадцать": 12
    }
    translator = str.maketrans('', '', string.punctuation)
    text = mesg.translate(translator).lower()
    days = -1
    multip = 1
    for j, word in enumerate(text.split()):
        for i in morph.parse(word):
            if i.normal_form in common_time.keys():
                days = common_time[i.normal_form]
                if j > 0 and morph.parse(text.split()[j - 1])[0].normal_form in common_digits.keys():
                    multip = common_digits[morph.parse(text.split()[j - 1])[0].normal_form]
                elif j < len(text.split()) - 1 and morph.parse(text.split()[j + 1])[
                    0].normal_form in common_digits.keys():
                    multip = common_digits[morph.parse(text.split()[j + 1])[0].normal_form]
                elif j > 0 and text.split()[j - 1].isdigit():
                    multip = int(text.split()[j - 1])
                elif j < len(text.split()) - 1 and text.split()[j + 1].isdigit():
                    multip = int(text.split()[j + 1])
                break
        if days != -1:
            return days*multip
    return -1


# print(get_time_interval('Сколько ноутбуков потребуется обновить в течение шести месяцев?'))
#
# classify_product('Сколько процессоров осталось на складе?')
def make_action_time_code(question_from_user):
    response_list = []
    if choose_action(question_from_user) == 1:
        response_list.append('1')
        response_list.append(classify_product(question_from_user))
        response_list.append('-')
    else:
        response_list.append('2')
        response_list.append(classify_product(question_from_user))
        response_list.append(str(get_time_interval(question_from_user)))
    print(', '.join(response_list))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some arguments.')
    parser.add_argument('message', type=str)
    args = parser.parse_args()
    make_action_time_code(args.message)
