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

@Component
@Data
@Slf4j
public class FZ44Parser {
    public String isUpdate() {
        try {
            Document document = Jsoup.connect("https://www.consultant.ru/document/cons_doc_LAW_462163/").get();
            Elements changeBlocks = document.select(".document__insert p:contains(Последние изменения)");

            Element lastChangesBlock = changeBlocks.first();
            Elements changesElements = lastChangesBlock.parent().select("p.no-indent");

            StringBuilder changes = new StringBuilder();
            boolean check = false;
            for (Element change : changesElements) {
                String text = change.text();
                if (text.equals("Последние изменения"))
                    check = true;
                if (check)
                    changes.append(text).append("\n");
            }

            Pattern datePattern = Pattern.compile("С (\\d{1,2} \\p{IsAlphabetic}+)");
            Matcher matcher = datePattern.matcher(changes.toString());
            
            LocalDate localDate = null;

            if (matcher.find()) {
                String dateString = matcher.group(1) + " 2024";
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

            String result = localDate.toString() + "\n" + changes;
            log.info(result);
            return result;
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }
}
