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
import ru.hackaton.parsers.StockRemainingsParser;

import java.io.File;

/**
 * REST контроллер для загрузки новых остатков продуктов.
 *
 * Этот контроллер предоставляет эндпоинт для загрузки файлов в формате XLSX, содержащих информацию
 * о новых остатках продуктов. Загруженные файлы обрабатываются и сохраняются с оригинальным именем.
 *
 * Аннотация {@link RestController} указывает, что этот класс является контроллером Spring.
 * Аннотация {@link RequestMapping} определяет базовый URL для всех эндпоинтов в этом контроллере.
 * Аннотация {@link Tag} добавляет метаданные OpenAPI для этого контроллера.
 */
@Slf4j
@RestController
@RequestMapping("/upload")
@Tag(name = "Add New Remainings Controller", description = "Endpoint for downloading new stock reaminings")
public class AddNewRemainingsController {

    private static final String FAILED_MESSAGE = "Upload Fail";
    private static final String SUCCESS_MESSAGE = "Success Upload";

    @Autowired
    private StockRemainingsParser parser;

    @Autowired
    private FromMultipartToFile fromMultipartToFile;

    /**
     * Эндпоинт для загрузки файлов в формате XLSX.
     *
     * Этот метод принимает файл в формате XLSX и сохраняет его с оригинальным именем.
     * Загруженный файл затем обрабатывается для извлечения информации о новых остатках продуктов.
     *
     * @param file Файл в формате XLSX для загрузки.
     * @return Объект {@link ResponseEntity} с результатом загрузки: сообщение об успехе или неудаче.
     */
    @PostMapping("/remainings")
    @Operation(summary = "Upload an XLSX file", description = "Upload an XLSX file and save it with the original filename",
            requestBody = @RequestBody(content = @Content(mediaType = "multipart/form-data",
                    schema = @Schema(implementation = UploadXlsxRequest.class))))
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "File uploaded successfully", content = @Content(mediaType = "text/plain")),
            @ApiResponse(responseCode = "404", description = "File upload failed", content = @Content(mediaType = "text/plain"))
    })
    public ResponseEntity<String> uploadXlsx(@RequestParam("file") MultipartFile file) {
        try {
            log.info("Имя файла: {}", file.getOriginalFilename());
            File simplyFile = fromMultipartToFile.convertMultipartFileToFile(file);
            parser.processFile(simplyFile);
            log.info("Файл загрузился");
            simplyFile.delete();
        } catch (Exception e) {
            log.error("Exception occured: {}", e.getMessage());
            return ResponseEntity.status(404).body(FAILED_MESSAGE);
        }
        return ResponseEntity.ok(SUCCESS_MESSAGE);
    }

    /**
     * Внутренний класс, представляющий запрос на загрузку файла XLSX.
     */
    public static class UploadXlsxRequest {
        @Schema(type = "string", format = "binary", description = "XLSX file to upload")
        public MultipartFile file;
    }
}
