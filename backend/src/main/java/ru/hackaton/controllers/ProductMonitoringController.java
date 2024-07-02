package ru.hackaton.controllers;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import ru.hackaton.service.ProductMonitoringDB;

import java.util.ArrayList;
import java.util.List;

@Slf4j
@RestController
@RequestMapping("/monitoring")
@Tag(name = "Product Monitoring Controller", description = "Endpoint adding, removing and showing monitoring products")
public class ProductMonitoringController {

    private static final String SUCCESS_MESSAGE = "Success";
    private static final String FAILED_MESSAGE = "Fail";

    @Autowired
    ProductMonitoringDB db;

    @Operation(summary = "Add a product to monitoring for a specific user")
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Product added successfully", content = @Content(schema = @Schema(implementation = String.class))),
            @ApiResponse(responseCode = "404", description = "Failed to add product", content = @Content(schema = @Schema(implementation = String.class)))
    })
    @PostMapping("/add")
    public ResponseEntity<String> addProduct(@RequestParam("user_id") long userId, @RequestParam("product") String product) {
        String response = db.addToMonitoringDB(userId, product);
        if (response.equals(SUCCESS_MESSAGE))
            return ResponseEntity.ok(response);
        return ResponseEntity.status(404).body(FAILED_MESSAGE);
    }

    @Operation(summary = "Remove a product from monitoring for a specific user")
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Product removed successfully", content = @Content(schema = @Schema(implementation = String.class))),
            @ApiResponse(responseCode = "404", description = "Failed to remove product", content = @Content(schema = @Schema(implementation = String.class)))
    })
    @DeleteMapping("/delete")
    public ResponseEntity<String> removeProduct(@RequestParam("user_id") long userId, @RequestParam("product") String product) {
        String response = db.removeFromMonitoringDB(userId, product);
        if (response.equals(SUCCESS_MESSAGE))
            return ResponseEntity.ok(response);
        return ResponseEntity.status(404).body(FAILED_MESSAGE);
    }

    @Operation(summary = "Get all products for a specific user")
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Products retrieved successfully", content = @Content(schema = @Schema(implementation = ArrayList.class)))
    })
    @GetMapping("/all")
    public ResponseEntity<List<String>> allProducts(@RequestParam("user_id") long userId) {
        return ResponseEntity.ok().body(new ArrayList<>(db.allProductForSpecialUser(userId)));
    }

    @GetMapping("/schedule")
    public ResponseEntity<List<String>> scheduleRequest(@RequestParam("user_id") long userId) {
        List<String> response = db.scheduleRequest(userId);
        if (response.isEmpty())
            return ResponseEntity.status(404).body(response);
        return ResponseEntity.ok(response);
    }
}
