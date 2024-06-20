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

@RestController
@Slf4j
@RequestMapping("/check-remainings")
@Tag(name = "Check Remainings Controller", description = "Endpoint for checking product remainings")
public class CheckRemainingsController {

    @GetMapping
    @Operation(summary = "Check remainings for a product", description = "Checks the remainings for a given product and returns a message and an image (if available).")
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Successfully checked remainings", content = @Content(mediaType = "application/json", schema = @Schema(implementation = RemainingsResponse.class))),
            @ApiResponse(responseCode = "404", description = "Something went wrong", content = @Content(mediaType = "application/json", schema = @Schema(implementation = RemainingsResponse.class)))
    })
    public ResponseEntity<RemainingsResponse> checkRemainings(@RequestParam("product") String product) {
        String pythonScriptPath = "/backend/src/main/java/ru/hackaton/python_scripts/remainings_by_item.py";
        String[] command = {"python3", pythonScriptPath, product};
        String message = "";
        byte[] imageBytes = new byte[0];

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
                return ResponseEntity.status(404).body(new CheckRemainingsController.RemainingsResponse(errorBuilder.toString(), null));
            }

            String[] outputLines = message.split("\n");
            if (outputLines.length == 1) {
                String predictionMessage = outputLines[0].trim();
                return ResponseEntity.status(404).body(new CheckRemainingsController.RemainingsResponse(predictionMessage, null));
            }
            String predictionMessage = outputLines[0].trim();
            String imagePath = outputLines[1].trim();

            imageBytes = readFileToByteArray(imagePath);

            File file = new File(imagePath);
            file.delete();

            return ResponseEntity.ok(new CheckRemainingsController.RemainingsResponse(predictionMessage, imageBytes));
        } catch (IOException | InterruptedException e) {
            log.error("Exception occurred: {}", e.getMessage());
        }
        return ResponseEntity.ok(new RemainingsResponse(message, imageBytes));
    }

    private byte[] readFileToByteArray(String filePath) throws IOException {
        File imgFile = new File(filePath);
        byte[] fileBytes = new byte[(int) imgFile.length()];
        try (FileInputStream fis = new FileInputStream(imgFile)) {
            fis.read(fileBytes);
        }
        return fileBytes;
    }

    @Data
    @AllArgsConstructor
    @Schema(description = "Response containing the message and image (if available)")
    static class RemainingsResponse{
        @Schema(description = "Message detailing the result of the check")
        private String message;
        @Schema(description = "Image file as byte array, if available")
        private byte[] image;
    }
}
