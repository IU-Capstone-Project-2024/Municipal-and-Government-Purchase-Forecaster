package ru.hackaton.controllers;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.Map;

@RestController
@RequestMapping("/get-json")
@Slf4j
@Tag(name = "Get Json Controller", description = "endpoint for generating json")
public class GetJsonController {
    private int id = 1;
    @GetMapping
    @Operation(summary = "Generate JSON data based on parameters", description = "Generates JSON data using a Python script based on provided parameters.")
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Successfully generated JSON data", content = {@io.swagger.v3.oas.annotations.media.Content(mediaType = "application/json", schema = @Schema(implementation = GetJsonResponse.class))}),
            @ApiResponse(responseCode = "404", description = "Failed to generate JSON data", content = {@io.swagger.v3.oas.annotations.media.Content(mediaType = "application/json", schema = @Schema(implementation = GetJsonResponse.class))})
    })
    public ResponseEntity<GetJsonResponse> getJson(@RequestParam("product") String product,
                                                       @RequestParam("id_user") int idUser,
                                                       @RequestParam("predict") int predict,
                                                       @RequestParam("start_date") String startDate,
                                                       @RequestParam("end_date") String endDate) {
        String pythonScriptPath = "/backend/src/main/java/ru/hackaton/python_scripts/json_maker.py";
        String[] command = {"python3", pythonScriptPath, product, String.valueOf(id), String.valueOf(idUser), String.valueOf(predict), startDate, endDate};
        String message = "";
        try {
            String s;
            ProcessBuilder pb = new ProcessBuilder(command);
            Process process = pb.start();
            BufferedReader stdInput = new BufferedReader(new InputStreamReader(process.getInputStream()));

            // Check exit code of python code
            BufferedReader stdError = new BufferedReader(new InputStreamReader(process.getErrorStream()));
            StringBuilder errorBuilder = new StringBuilder();
            while ((s = stdError.readLine()) != null) {
                errorBuilder.append(s).append("\n");
            }
            int exitCode = process.waitFor();
            if (exitCode != 0) {
                log.error("Python script error: {}", errorBuilder.toString());
                return ResponseEntity.status(404).body(new GetJsonResponse());
            }

            // Check output of the python script for Json creating
            StringBuilder outputBuilder = new StringBuilder();
            while ((s = stdInput.readLine()) != null) {
                outputBuilder.append(s).append("\n");
            }
            message = outputBuilder.toString().trim();
            //System.out.println(message);
            ObjectMapper objectMapper = new ObjectMapper();
            Map<String, Object> map = objectMapper.readValue(message, new TypeReference<>() {});
            log.info(map.toString());
            return ResponseEntity.ok(new GetJsonResponse(map));
        } catch (IOException | InterruptedException e) {
            log.error("Exception occured: {}", e.getMessage());
            return ResponseEntity.status(404).body(new GetJsonResponse());
        }
    }

    @Data
    @AllArgsConstructor
    @NoArgsConstructor
    static class GetJsonResponse {
        Map<String, Object> mp;
    }
}
