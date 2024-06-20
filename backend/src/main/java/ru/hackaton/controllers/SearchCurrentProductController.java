package ru.hackaton.controllers;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import ru.hackaton.service.SimilarProductFromDB;

import java.util.List;

@RestController
@RequestMapping("/search-product")
@Tag(name = "Search Product Controller", description = "Endpoint for searching similar products from the database")
public class SearchCurrentProductController {

    @Autowired
    private SimilarProductFromDB similarProductFromDB;

    @GetMapping
    @Operation(summary = "Search for similar products", description = "Finds and returns a list of products similar to the given product name")
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Successfully retrieved similar products"),
            @ApiResponse(responseCode = "404", description = "No similar products found")
    })
    public ResponseEntity<List<String>> currentProduct(@RequestParam("product") String product) {
        List<String>result = similarProductFromDB.mostSimilarProduct(product);
        if (result.isEmpty())
            return ResponseEntity.status(404).body(result);
        return ResponseEntity.ok(result);
    }
}
