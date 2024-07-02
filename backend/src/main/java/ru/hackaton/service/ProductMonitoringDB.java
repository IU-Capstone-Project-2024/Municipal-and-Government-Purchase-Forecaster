package ru.hackaton.service;

import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import lombok.extern.slf4j.Slf4j;
import org.bson.Document;
import org.springframework.stereotype.Component;
import ru.hackaton.config.ApplicationConfig;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Component
public class ProductMonitoringDB {
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
    final ApplicationConfig config;
    private static final String SUCCESS_MESSAGE = "Success";
    private static final String FAILED_MESSAGE = "Fail";

    public ProductMonitoringDB(ApplicationConfig config) {
        this.config = config;
        client = MongoClients.create(config.getMongoUrl());
        db = client.getDatabase("stock_remainings");
        collection = db.getCollection("Мониторинг товаров");
    }

    public String addToMonitoringDB(long userId, String product) {
        try {
            String pythonScriptPath = "/backend/src/main/java/ru/hackaton/python_scripts/forcaster.py";
            String[] command = {"python3", pythonScriptPath, product, Integer.toString(3)};
            String message = "";
            String answerFromPrediction = "";

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
                    answerFromPrediction = "Wrong!";
                } else {
                    String[] outputLines = message.split("\n");
                    if (outputLines.length >= 1) {
                        String predictionMessage = outputLines[0].trim();
                        log.info("We got ONLY prediction");
                        answerFromPrediction = predictionMessage;
                    }
                }
            } catch (IOException | InterruptedException e) {
                log.error("Exception occurred: {}", e.getMessage());
                answerFromPrediction = "Wrong!";
            }
            String option = "";
            LocalDate date = LocalDate.now();
            if (!(answerFromPrediction.startsWith("Необходимо докупить"))) {
                if (answerFromPrediction.startsWith("На складе имеется")) {
                    date = date.plusMonths(3);
                    option = "Запустить предиктер еще раз в эту дату";
                } else {
                    date = date.minusDays(1);
                    option = "Не запускать предиктер";
                }
            }
            else {
                log.info(answerFromPrediction);
                date = LocalDate.now().plusDays(1);
                option = "Отправить уведомление пользователю";
            }

            Document document = new Document();
            document.append("userId", userId)
                    .append("product", product)
                    .append("date", date.toString())
                    .append("option", option);
            collection.insertOne(document);

            log.info("Товар '{}' добавлен в мониторинг для пользователя с id={}, date={}, option={}", product, userId, date, option);
            return SUCCESS_MESSAGE;
        } catch (Exception e) {
            log.error("Ошибка при добавлении товара в мониторинг: {}", e.getMessage());
            return FAILED_MESSAGE;
        }
    }

    public String removeFromMonitoringDB(long userId, String product) {
        try {
            Document filter = new Document("userId", userId)
                    .append("product", product);
            collection.deleteOne(filter);

            log.info("Товар '{}' удален из мониторинга для пользователя с id={}", product, userId);
            return SUCCESS_MESSAGE;
        } catch (Exception e) {
            log.error("Ошибка при удалении товара из мониторинга: {}", e.getMessage());
            return FAILED_MESSAGE;
        }
    }

    public ArrayList<String> allProductForSpecialUser(long userId) {
        ArrayList<String> products = new ArrayList<>();
        try {
            Document filter = new Document("userId", userId);
            for (Document doc : collection.find(filter)) {
                String product = doc.getString("product");
                products.add(product);
            }
            log.info("Найдено {} товаров для пользователя с id={}", products.size(), userId);
        } catch (Exception e) {
            log.error("Ошибка при получении товаров для пользователя: {}", e.getMessage());
        }
        return products;
    }

    public List<String> scheduleRequest(long userId) {
        List<String>answer = new ArrayList<>();
        try {
            Document filter = new Document()
                    .append("userId", userId)
                    .append("date", LocalDate.now().toString())
                    .append("option", "Отправить уведомление пользователю");
            log.info(filter.toString());
            for (Document doc : collection.find(filter)) {
                StringBuilder cur = new StringBuilder();
                cur.append("Товар '").append(doc.getString("product"))
                        .append("' заканчивается. Позаботтесь о закупке данного товара.");
                answer.add(cur.toString());
                cur.setLength(0);
            }
            log.info(answer.toString());
            return answer;
        } catch (Exception e) {
            log.error("Ошибка при получении товаров для пользователя: {}", e.getMessage());
        }
        return answer;
    }
}
