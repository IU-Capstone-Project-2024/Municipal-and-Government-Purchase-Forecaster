package ru.hackaton.parsers;

import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.apache.poi.ss.usermodel.*;
import org.bson.Document;
import org.springframework.stereotype.Component;
import ru.hackaton.config.ApplicationConfig;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Компонент Spring для парсинга и сохранения данных о складских остатках из Excel файлов в MongoDB.
 */
@Component
@Slf4j
@Data
public class StockRemainingsParser {
    final ApplicationConfig config;
    private static MongoClient client;
    private static MongoDatabase db;
    private static MongoCollection<Document> collection;
    private static final String EXCEPTION_LOG = "Exception occurred: {}";

    /**
     * Конструктор для инициализации компонента.
     *
     * @param config конфигурация приложения, содержащая URL для подключения к MongoDB
     */
    public StockRemainingsParser(ApplicationConfig config) {
        this.config = config;
        client = MongoClients.create(config.getMongoUrl());
        db = client.getDatabase("stock_remainings");
        collection = db.getCollection("Складские остатки");
    }

    /**
     * Метод для обработки Excel файла со складскими остатками.
     *
     * @param excelFile Excel файл со складскими остатками
     */
    public void processFile(File excelFile) {
        try {
            log.info("Пришел новый файл со складскими остатками: {}", excelFile.getName());
            FileInputStream fis = new FileInputStream(excelFile);
            Workbook workbook = new XSSFWorkbook(fis); // Load Excel workbook
            Sheet sheet = workbook.getSheetAt(0); // Assuming there's only one sheet

            String filename = excelFile.getName();
            if (filename.endsWith("сч_21.xlsx")) {
                addIntoDb21(sheet, filename);
            } else if (filename.endsWith("сч_105.xlsx")) {
                addIntoDb105(sheet, filename);
            } else if (filename.endsWith("сч_101.xlsx")) {
                addIntoDb101(sheet, filename);
            }

            workbook.close();
            fis.close();
        } catch (IOException e) {
            log.error(EXCEPTION_LOG, e.getMessage());
        }
    }

    /**
     * Метод для обработки данных из Excel файла с кодом счёта 21 и сохранения их в MongoDB.
     *
     * @param sheet    лист Excel с данными
     * @param filename имя файла
     */
    public static void addIntoDb21(Sheet sheet, String filename) {
        log.info("Файл сч 21");
        String[] parts = filename.split("\\\\");

        String lastPart = parts[parts.length - 1];

        String date = lastPart.substring(22, 32);

        String subgroup = "";

        for(int i = 8; i <= sheet.getLastRowNum(); ++i){
            Row row = sheet.getRow(i);
            Cell cell0 = row.getCell(0);
            if (cell0 == null){
                continue;
            }
            try{
                double numeric_value = Integer.parseInt(cell0.getStringCellValue().replaceAll(" ", ""));
                Cell cell2 = row.getCell(2);
                Cell cell20 = row.getCell(20);
                String val2 = cell2.getStringCellValue();
                double val20 = cell20.getNumericCellValue();
                if (val2 != null){
                    //System.out.println(val2);
                    int pos = val2.lastIndexOf(',');
                    Document document = new Document("Название", normalizeName(val2))
                            .append("Остаток", val20)
                            .append("Подгруппа", subgroup)
                            .append("Дата", date)
                            .append("сч", 21)
                            .append("полное название", val2);
                    collection.insertOne(document);
                }
            } catch (NumberFormatException e){
                String string = cell0.getStringCellValue();
                if(string.contains("21.")){
                    Pattern pattern = Pattern.compile("21\\.\\d+");
                    Matcher matcher = pattern.matcher(string);
                    if (matcher.find()) {
                        subgroup = matcher.group();

                    }
                    i += 4;
                } else {
                    if(string.equals("Итого")){
                        break;
                    }
                }
            }
        }
    }

    /**
     * Метод для обработки данных из Excel файла с кодом счёта 105 и сохранения их в MongoDB.
     *
     * @param sheet    лист Excel с данными
     * @param filename имя файла
     */
    private static void addIntoDb105(Sheet sheet, String filename) {
        log.info("Файл сч 105");
        String[] parts = filename.split("\\\\");

        String lastPart = parts[parts.length - 1];

        String date = lastPart.substring(22, 32);
        int i = 0;
        boolean isNewSubgroup = false;
        boolean seenOne = false;
        double subgroupId = 0;

        for (Row row : sheet) {
            if (i < 6) {
                i++;
                continue;
            } else {
                Cell cell = row.getCell(0);

                if (cell != null) {
                    try {
                        double numericValue = Double.parseDouble(cell.toString());
                        if (!isNewSubgroup) {
                            isNewSubgroup = true;
                            subgroupId = numericValue;
                        } else {
                            if (numericValue == 1.0) {
                                seenOne = true;
                            } else if (isNewSubgroup && seenOne && numericValue != 1.0) {
                                subgroupId = numericValue;
                            } else {
                                isNewSubgroup = false;
                                seenOne = false;
                            }
                        }
                    } catch (NumberFormatException e) {
                        switch (cell.getCellType()) {
                            case STRING:
                                String stringValue = cell.getStringCellValue();

                                Cell cell2 = row.getCell(2);
                                Cell cell0 = row.getCell(0);

                                if (cell0 != null) {
                                    try {
                                        String value0 = cell0.getStringCellValue();
                                        if (value0.equals("Итого")) {
                                            break;
                                        }
                                        String value2 = Double.toString(cell2.getNumericCellValue());

                                        if (!value0.isEmpty()) {
                                            //System.out.println(value0);
                                            Document document = new Document("Название", normalizeName(value0.substring(0, value0.lastIndexOf(','))))
                                                    .append("Остаток", value2)
                                                    .append("Подгруппа", subgroupId)
                                                    .append("Дата", date)
                                                    .append("сч", 105)
                                                    .append("полное название", value0.substring(0, value0.lastIndexOf(',')));
                                            //System.out.println(document);
                                            collection.insertOne(document);
                                        }
                                    } catch (IllegalStateException ex) {
                                        log.error("Error processing row for MongoDB insertion: {}", ex.getMessage());
                                    }
                                }
                        }
                    }
                }
                i++;
            }
        }
    }

    /**
     * Метод для обработки данных из Excel файла с кодом счёта 101 и сохранения их в MongoDB.
     *
     * @param sheet    лист Excel с данными
     * @param filename имя файла
     */
    private static void addIntoDb101(Sheet sheet, String filename) {
        log.info("Файл сч 101");
        String[] parts = filename.split("\\\\");

        String lastPart = parts[parts.length - 1];

        String date = lastPart.substring(22, 32);

        String subgroup = "";

        for(int i = 9; i <= sheet.getLastRowNum(); ++i){
            Row row = sheet.getRow(i);
            Cell cell0 = row.getCell(0);
            if (cell0 == null){
                continue;
            }
            try{
                double numeric_value = Integer.parseInt(cell0.getStringCellValue());
                Cell cell2 = row.getCell(2);
                Cell cell20 = row.getCell(20);
                String val2 = cell2.getStringCellValue();
                double val20 = cell20.getNumericCellValue();
                if (val2 != null){
                    //System.out.println(val2);
                    int pos = val2.lastIndexOf(',');
                    Document document = new Document("Название", normalizeName(val2))
                            .append("Остаток", val20)
                            .append("Подгруппа", subgroup)
                            .append("Дата", date)
                            .append("сч", 101)
                            .append("полное название", val2);
                    collection.insertOne(document);
                }
            }catch (NumberFormatException e){
                String string = cell0.getStringCellValue();
                if(string.contains("101.")){
                    Pattern pattern = Pattern.compile("101\\.\\d+");
                    Matcher matcher = pattern.matcher(string);
                    if (matcher.find()) {
                        subgroup = matcher.group();

                    }
                    i += 4;
                } else {
                    if(string.equals("Итого")){
                        break;
                    }
                }
            }
        }

    }

    /**
     * Метод для нормализации имени товара (удаляет пробелы и приводит к нижнему регистру).
     *
     * @param name исходное имя товара
     * @return нормализованное имя товара
     */
    private static String normalizeName(String name) {
        return name.replaceAll("\\s", "").toLowerCase();
    }
}
