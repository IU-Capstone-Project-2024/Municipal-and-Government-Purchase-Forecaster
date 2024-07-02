package ru.hackaton.controllers;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.*;

/**
 * REST контроллер для предсказания моделей и возврата соответствующих изображений.
 *
 * Этот контроллер предоставляет эндпоинт для запуска предсказания для указанного продукта и месяца
 * и возвращает сообщение с результатом и до двух изображений, если они доступны.
 *
 * Аннотация {@link RestController} указывает, что этот класс является контроллером Spring.
 * Аннотация {@link RequestMapping} определяет базовый URL для всех эндпоинтов в этом контроллере.
 * Аннотация {@link Tag} добавляет метаданные OpenAPI для этого контроллера.
 */
@RestController
@RequestMapping("/predict")
@Slf4j
@Tag(name = "Predict Model Controller", description = "Endpoint for predicting model outcomes and returning relevant images")
public class PredictModelController {

    /**
     * Эндпоинт для предсказания моделей на основе продукта и месяца.
     *
     * Этот метод вызывает Python-скрипт для выполнения предсказания и возвращает результат
     * в виде сообщения и до двух изображений.
     *
     * @param product Название продукта.
     * @param month Номер месяца.
     * @return Объект {@link ResponseEntity} с предсказанием и изображениями или сообщением об ошибке.
     */
    @GetMapping
    @Operation(summary = "Predict model outcomes", description = "Runs a prediction for the specified product and month, returning a message and up to two images.")
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Successfully retrieved prediction and images", content = @Content(mediaType = "application/json", schema = @Schema(implementation = PredictionResponse.class))),
            @ApiResponse(responseCode = "404", description = "Prediction or images not found", content = @Content(mediaType = "application/json", schema = @Schema(implementation = PredictionResponse.class))),
    })
    public ResponseEntity<PredictionResponse> predict(@RequestParam("product") String product, @RequestParam("month") Integer month) {
        String pythonScriptPath = "/backend/src/main/java/ru/hackaton/python_scripts/forcaster.py";
        String[] command = {"python3", pythonScriptPath, product, month.toString()};
        String message = "";
        byte[] imageBytes1 = new byte[0];
        byte[] imageBytes2 = new byte[0];

        try {
            ProcessBuilder pb = new ProcessBuilder(command);
            Process process = pb.start();
            BufferedReader stdInput = new BufferedReader(new InputStreamReader(process.getInputStream()));
            BufferedReader stdError = new BufferedReader(new InputStreamReader(process.getErrorStream()));

            StringBuilder outputBuilder = new StringBuilder();
            String s;
            while ((s = stdInput.readLine()) != null) {
                outputBuilder.append(s).append("\n");
            }
            message = outputBuilder.toString().trim();

            StringBuilder errorBuilder = new StringBuilder();
            while ((s = stdError.readLine()) != null) {
                errorBuilder.append(s).append("\n");
            }

            int exitCode = process.waitFor();
            if (exitCode != 0) {
                log.error("Python script error: {}", errorBuilder.toString());
                return ResponseEntity.status(404).body(new PredictionResponse(errorBuilder.toString(), null, null));
            }

            // Parsing message to get image paths
            String[] outputLines = message.split("\n");
            if (outputLines.length == 1) {
                String predictionMessage = outputLines[0].trim();
                log.info("We got ONLY prediction");
                return ResponseEntity.status(200).body(new PredictionResponse(predictionMessage, null, null));
            }
            if (outputLines.length == 2) {
                String predictionMessage = outputLines[0].trim();
                String imagePath1 = outputLines[1].trim();
                imageBytes1 = readFileToByteArray(imagePath1);
                log.info("We got prediction and ONLY one image");
                return ResponseEntity.status(200).body(new PredictionResponse(predictionMessage, imageBytes1, null));
            }
            String predictionMessage = outputLines[0].trim();
            String imagePath1 = outputLines[1].trim();
            String imagePath2 = outputLines[2].trim();

            imageBytes1 = readFileToByteArray(imagePath1);
            imageBytes2 = readFileToByteArray(imagePath2);

            File file = new File(imagePath1);
            file.delete();
            file = new File(imagePath2);
            file.delete();

            log.info("All good! We got prediction and two images");
            return ResponseEntity.ok(new PredictionResponse(predictionMessage, imageBytes1, imageBytes2));

        } catch (IOException | InterruptedException e) {
            log.error("Exception occurred: {}", e.getMessage());
            return ResponseEntity.status(404).body(new PredictionResponse(e.getMessage(), null, null));
        }
    }

    /**
     * Читает содержимое файла в массив байтов.
     *
     * @param filePath Путь к файлу.
     * @return Массив байтов, содержащий данные файла.
     * @throws IOException Если происходит ошибка при чтении файла.
     */
    private byte[] readFileToByteArray(String filePath) throws IOException {
        File imgFile = new File(filePath);
        byte[] fileBytes = new byte[(int) imgFile.length()];
        try (FileInputStream fis = new FileInputStream(imgFile)) {
            fis.read(fileBytes);
        }
        return fileBytes;
    }

    /**
     * Внутренний класс, представляющий ответ, содержащий предсказание и изображения.
     */
    @Data
    @AllArgsConstructor
    @Schema(description = "Response containing the prediction message and images (if available)")
    static class PredictionResponse {
        /**
         * Сообщение с результатом предсказания.
         */
        @Schema(description = "Message detailing the result of the prediction")
        private String message;
        /**
         * Первое изображение в виде массива байтов, если доступно.
         */
        @Schema(description = "First image file as byte array, if available")
        private byte[] image1;
        /**
         * Второе изображение в виде массива байтов, если доступно.
         */
        @Schema(description = "Second image file as byte array, if available")
        private byte[] image2;
    }
}