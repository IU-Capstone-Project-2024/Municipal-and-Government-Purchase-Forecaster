from aiogram.utils.keyboard import InlineKeyboardBuilder


def keyboard_builder(button_texts, custom_size=None):
    builder = InlineKeyboardBuilder()
    for text in button_texts:
        builder.button(text=text, callback_data=text)
    if custom_size:
        builder.adjust(*custom_size)
    else:
        builder.adjust(1)
    return builder.as_markup()
