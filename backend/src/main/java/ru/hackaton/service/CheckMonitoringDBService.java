package ru.hackaton.service;

import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import lombok.extern.slf4j.Slf4j;
import org.bson.Document;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import ru.hackaton.config.ApplicationConfig;

import java.time.LocalDate;
import java.time.temporal.TemporalAccessor;
import java.util.ArrayList;
import java.util.Date;

@Component
@Slf4j
public class CheckMonitoringDBService {
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

    @Autowired
    ProductMonitoringDB productMonitoringDB;

    public CheckMonitoringDBService(ApplicationConfig config) {
        this.config = config;
        client = MongoClients.create(config.getMongoUrl());
        db = client.getDatabase("stock_remainings");
        collection = db.getCollection("Мониторинг товаров");
    }

    @Scheduled(cron = "0 0 2 * * ?")
    public void check() {
        ArrayList<String> products = new ArrayList<>();
        try {
            Document filter = new Document("option", "Запустить предиктер еще раз в эту дату");
            for (Document doc : collection.find(filter)) {
                LocalDate date = LocalDate.parse(String.valueOf(doc.get("date")));
                if (date.isEqual(LocalDate.now())) {
                    log.info("Обновляем товар {}", doc);
                    collection.deleteOne(doc);
                    productMonitoringDB.addToMonitoringDB(doc.getLong("userId"), doc.getString("product"));
                }
            }
            log.info("Скедулер отработал");
        } catch (Exception e) {
            log.error("Ошибка у скедулера: {}", e.getMessage());
        }
    }
}
