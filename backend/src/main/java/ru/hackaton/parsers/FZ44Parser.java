package ru.hackaton.parsers;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Компонент Spring для парсинга информации о последних изменениях в законодательстве FZ44.
 * Данный компонент осуществляет извлечение информации о последних изменениях и их дате с сайта Consultant.ru.
 */
@Component
@Data
@Slf4j
public class FZ44Parser {

    /**
     * Метод для извлечения информации о последних изменениях в законодательстве FZ44 с сайта Consultant.ru.
     *
     * @return строка с датой последних изменений и самими изменениями
     * @throws RuntimeException если произошла ошибка при подключении к сайту или парсинге данных
     */
    public String isUpdate() {
        try {
            // Подключаемся к странице на Consultant.ru
            Document document = Jsoup.connect("https://www.consultant.ru/document/cons_doc_LAW_462163/").get();

            // Ищем блок с последними изменениями
            Elements changeBlocks = document.select(".document__insert p:contains(Последние изменения)");
            Element lastChangesBlock = changeBlocks.first();

            // Извлекаем все элементы с изменениями
            Elements changesElements = lastChangesBlock.parent().select("p.no-indent");

            // Собираем текст изменений в одну строку
            StringBuilder changes = new StringBuilder();
            boolean check = false;
            for (Element change : changesElements) {
                String text = change.text();
                if (text.equals("Последние изменения"))
                    check = true;
                if (check)
                    changes.append(text).append("\n");
            }

            // Ищем дату в тексте изменений
            Pattern datePattern = Pattern.compile("С (\\d{1,2} \\p{IsAlphabetic}+)");
            Matcher matcher = datePattern.matcher(changes.toString());
            LocalDate localDate = null;

            if (matcher.find()) {
                // Форматируем строку даты и парсим в LocalDate
                String dateString = matcher.group(1) + " 2024"; // Добавляем год, так как на странице дата без года
                DateTimeFormatter formatter = DateTimeFormatter.ofPattern("d MMMM yyyy", new Locale("ru"));
                try {
                    localDate = LocalDate.parse(dateString, formatter);
                    log.info("Извлеченная дата: {}", localDate);
                } catch (DateTimeParseException e) {
                    log.error("Ошибка парсинга даты: {}", e.getMessage());
                }
            } else {
                log.error("Дата не найдена в тексте.");
            }

            // Собираем результат в строку и возвращаем
            String result = localDate.toString() + "\n" + changes;
            log.info(result);
            return result;
        } catch (IOException e) {
            // В случае ошибки при подключении или парсинге выбрасываем исключение
            throw new RuntimeException(e);
        }
    }
}
