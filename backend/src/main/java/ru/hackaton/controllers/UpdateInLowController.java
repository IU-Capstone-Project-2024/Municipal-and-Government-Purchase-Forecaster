package ru.hackaton.controllers;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ru.hackaton.parsers.FZ44Parser;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * REST контроллер для проверки обновлений в законодательстве.
 *
 * Этот контроллер предоставляет эндпоинт для проверки и возврата информации об обновлениях в законодательстве.
 *
 * Аннотация {@link RestController} указывает, что этот класс является контроллером Spring.
 * Аннотация {@link RequestMapping} определяет базовый URL для всех эндпоинтов в этом контроллере.
 * Аннотация {@link Tag} добавляет метаданные OpenAPI для этого контроллера.
 */
@Slf4j
@RestController
@RequestMapping("/law-update")
@Tag(name = "Law Update Controller", description = "Endpoint for checking law updates")
public class UpdateInLowController {

    private LocalDate lastCheckedData = LocalDate.of(2024, 6, 7);
    @Autowired
    private FZ44Parser fz44Parser;

    /**
     * Эндпоинт для проверки обновлений в законодательстве.
     *
     * Этот метод вызывает парсер для получения информации об обновлениях и анализирует полученные данные,
     * чтобы определить, были ли изменения в законодательстве с последней проверки.
     *
     * @return Объект {@link ResponseEntity} с информацией об обновлениях или сообщением об их отсутствии.
     */
    @GetMapping
    @Operation(summary = "Check for law updates", description = "Check for updates in law and return information if available")
    @ApiResponse(responseCode = "200", description = "Successfully retrieved law update information", content = @Content(mediaType = "text/plain", schema = @Schema(type = "string")))
    @ApiResponse(responseCode = "404", description = "No updates found in law")
    public ResponseEntity<String> getLowUpdate() {
        String info = fz44Parser.isUpdate();
        Pattern datePattern = Pattern.compile("(\\d{4}-\\d{2}-\\d{2})");
        Matcher matcher = datePattern.matcher(info);

        if (matcher.find()) {
            String dateString = matcher.group(1);
            DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd");
            try {
                LocalDate date = LocalDate.parse(dateString, formatter);
                log.info("Извлеченная дата: {}", date);
                if (date.isEqual(lastCheckedData)) {
                    lastCheckedData = lastCheckedData.plusDays(1);
                    return ResponseEntity.ok(info);
                }
            } catch (DateTimeParseException e) {
                log.error("Ошибка парсинга даты: {}", e.getMessage());
            }
        } else {
            log.error("Дата не найдена в строке.");
        }
        return ResponseEntity.status(404).body("No updates in law");
    }
}
