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

/**
 * REST контроллер для поиска похожих продуктов в базе данных.
 *
 * Этот контроллер предоставляет эндпоинт для поиска и возврата списка продуктов,
 * похожих на указанный продукт.
 *
 * Аннотация {@link RestController} указывает, что этот класс является контроллером Spring.
 * Аннотация {@link RequestMapping} определяет базовый URL для всех эндпоинтов в этом контроллере.
 * Аннотация {@link Tag} добавляет метаданные OpenAPI для этого контроллера.
 */
@RestController
@RequestMapping("/search-product")
@Tag(name = "Search Product Controller", description = "Endpoint for searching similar products from the database")
public class SearchCurrentProductController {

    @Autowired
    private SimilarProductFromDB similarProductFromDB;

    /**
     * Эндпоинт для поиска похожих продуктов.
     *
     * Этот метод принимает название продукта в качестве параметра и возвращает список продуктов,
     * похожих на указанный продукт.
     *
     * @param product Название продукта для поиска похожих продуктов.
     * @return Объект {@link ResponseEntity} с списком похожих продуктов или сообщением об ошибке.
     */
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
