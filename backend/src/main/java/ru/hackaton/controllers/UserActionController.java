package ru.hackaton.controllers;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

/**
 * REST контроллер для обработки действий пользователей.
 *
 * Этот контроллер предоставляет эндпоинт для обработки сообщений пользователей и получения специфических ответов от ChatGPT.
 *
 * Аннотация {@link RestController} указывает, что этот класс является контроллером Spring.
 * Аннотация {@link RequestMapping} определяет базовый URL для всех эндпоинтов в этом контроллере.
 * Аннотация {@link Tag} добавляет метаданные OpenAPI для этого контроллера.
 */
@RestController
@RequestMapping("/user-action")
@Slf4j
@Tag(name = "User Action Controller", description = "Endpoint for user actions")
public class UserActionController {

    /**
     * Эндпоинт для обработки сообщений пользователей.
     *
     * Этот метод принимает сообщение пользователя, отправляет его в ChatGPT для обработки и возвращает ответ.
     *
     * @param userMessage Сообщение пользователя, которое необходимо обработать.
     * @return Объект {@link ResponseEntity} с ответом от ChatGPT или сообщением об ошибке.
     */
    @GetMapping
    @Operation(summary = "Process user message", description = "Processes user message and provides a specific response")
    @ApiResponse(responseCode = "200", description = "Successful response with processed message", content = @Content(mediaType = "text/plain"))
    @ApiResponse(responseCode = "404", description = "Request to Model failed")
    public ResponseEntity<String> userAction(@RequestParam("message") String userMessage) {
        String pythonScriptPath = "/backend/src/main/java/ru/hackaton/python_scripts/classify_product.py";
        String[] command = {"python3", pythonScriptPath, userMessage};
        String message = "";

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
                return ResponseEntity.status(404).body(errorBuilder.toString());
            }

            return ResponseEntity.ok(message);
        } catch (IOException | InterruptedException e) {
            log.error("Exception occurred: {}", e.getMessage());
            return ResponseEntity.status(404).body("Wrong");
        }
    }
}
