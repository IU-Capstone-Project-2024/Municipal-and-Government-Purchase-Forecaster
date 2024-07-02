package ru.hackaton.service;

import com.mongodb.client.*;
import com.mongodb.client.model.Filters;
import com.mongodb.client.model.Projections;
import com.mongodb.client.model.Sorts;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.bson.Document;
import org.bson.conversions.Bson;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import ru.hackaton.config.ApplicationConfig;

import java.util.*;
import java.util.concurrent.*;
import java.util.stream.Collectors;

/**
 * Класс для поиска наиболее похожих продуктов из базы данных складских остатков.
 * Использует MongoDB для доступа к данным и ChatGPT для генерации ответов на основе запросов.
 * Реализует два метода поиска: простой поиск по префиксной функции и поиск с использованием ChatGPT.
 */
@Slf4j
@Data
@Component
public class SimilarProductFromDB {
    final ApplicationConfig config;
    /**
     * Размер пула потоков для обработки данных.
     */
    private static final int THREAD_POOL_SIZE = 5;
    /**
     * Максимальное количество продуктов в одном сообщении.
     */
    private static final int MAX_PRODUCTS_IN_MESSAGE = 350;
    /**
     * Клиент MongoDB для доступа к базе данных "stock_remainings".
     */
    private static MongoClient client;
    /**
     * База данных MongoDB для складских остатков.
     */
    private static MongoDatabase db;
    /**
     * Коллекция MongoDB для хранения складских остатков.
     */
    private static MongoCollection<Document> collection;

    public SimilarProductFromDB(ApplicationConfig config) {
        this.config = config;
        client = MongoClients.create(config.getMongoUrl());
        db = client.getDatabase("stock_remainings");
        collection = db.getCollection("Складские остатки");
    }

    /**
     * Метод для поиска наиболее похожих продуктов на основе запроса.
     *
     * @param product запрос пользователя для поиска похожих продуктов
     * @return список наиболее похожих продуктов
     */
    public List<String> mostSimilarProduct(String product) {
        log.info("Пришел запрос от пользователя: {}", product);

        String[] words = product.split("\\s+");
        Map<String, Integer> productCounter = new HashMap<>();

        for (String word : words) {
            word = normalize(word);
            log.info("Ищем слово: {}", word);

            var filter = Filters.regex("полное название", word, "i");
            var projection = Projections.include("полное название");

            for (var doc : collection.find(filter).projection(projection)) {
                var fullName = doc.getString("полное название");
                log.info("Найден документ: {}", fullName);
                productCounter.put(fullName, productCounter.getOrDefault(fullName, 0) + 1);
            }
        }

        log.info("Счетчики товаров: {}", productCounter);

        var sortedProducts = productCounter.entrySet()
                .stream()
                .sorted((e1, e2) -> e2.getValue().compareTo(e1.getValue()))
                .limit(10)
                .map(Map.Entry::getKey)
                .collect(Collectors.toList());

        log.info("Возвращаем следующий список: {}", sortedProducts);
        return new ArrayList<>(sortedProducts);
    }

    private String normalize(String str) {
        return str.trim().toLowerCase();
    }
}
