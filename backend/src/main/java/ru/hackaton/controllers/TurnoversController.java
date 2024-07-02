package ru.hackaton.controllers;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.parameters.RequestBody;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import ru.hackaton.parsers.FromMultipartToFile;
import ru.hackaton.parsers.TurnoversParser;

import java.io.File;

/**
 * REST контроллер для загрузки файлов оборотов в формате XLSX.
 *
 * Этот контроллер предоставляет эндпоинт для загрузки и обработки файлов оборотов.
 *
 * Аннотация {@link RestController} указывает, что этот класс является контроллером Spring.
 * Аннотация {@link RequestMapping} определяет базовый URL для всех эндпоинтов в этом контроллере.
 * Аннотация {@link Tag} добавляет метаданные OpenAPI для этого контроллера.
 */
@RestController
@RequestMapping("/upload")
@Slf4j
@Tag(name = "Turnovers Controller", description = "Endpoint for uploading turnover XLSX files")
public class TurnoversController {

    private static final String SUCCESS_MESSAGE = "Success Upload";
    private static final String FAILED_MESSAGE = "Fail To Upload";

    @Autowired
    FromMultipartToFile fromMultipartToFile;

    @Autowired
    TurnoversParser parser;

    /**
     * Эндпоинт для загрузки файла оборотов в формате XLSX.
     *
     * Этот метод принимает файл в формате XLSX, сохраняет его с оригинальным именем
     * и обрабатывает с использованием парсера оборотов.
     *
     * @param file Файл в формате XLSX для загрузки.
     * @return Объект {@link ResponseEntity} с сообщением об успехе или ошибке.
     */
    @PostMapping("/turnovers")
    @Operation(summary = "Upload an XLSX file", description = "Upload an XLSX file and save it with the original filename",
            requestBody = @RequestBody(content = @Content(mediaType = "multipart/form-data",
                    schema = @Schema(implementation = TurnoversController.UploadXLSXRequest.class))))
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Successfully uploaded the XLSX file"),
            @ApiResponse(responseCode = "404", description = "Failed to upload the XLSX file")
    })
    public ResponseEntity<String> turnoversUpload(@RequestParam("file") MultipartFile file) {
        try {
            File excelFile = fromMultipartToFile.convertMultipartFileToFile(file);
            parser.processFile(excelFile);
            excelFile.delete();
        } catch (Exception e) {
            log.error("Exception occurred: {}", e.getMessage());
            return ResponseEntity.status(404).body(FAILED_MESSAGE);
        }
        return ResponseEntity.ok(SUCCESS_MESSAGE);
    }

    /**
     * Класс-запрос для загрузки файла в формате XLSX.
     */
    public static class UploadXLSXRequest {
        @Schema(type = "string", format = "binary", description = "XLSX file to upload")
        public MultipartFile file;
    }
}
