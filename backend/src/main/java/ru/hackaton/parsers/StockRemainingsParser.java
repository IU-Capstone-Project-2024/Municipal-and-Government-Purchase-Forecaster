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

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Component
@Slf4j
@Data
public class StockRemainingsParser {
    private static MongoClient client = MongoClients.create("mongodb://localhost:27017");
    private static MongoDatabase db = client.getDatabase("stock_remainings");
    private static MongoCollection<Document> collection = db.getCollection("Складские остатки");

    public void processFile(File excelFile) {
        try {
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
            e.printStackTrace();
        }
    }

    public static void addIntoDb21(Sheet sheet, String filename) {
        String[] parts = filename.split("\\\\");

        String lastPart = parts[parts.length - 1];

        String date = lastPart.substring(22, 32);

        String subgroup = "";

        for(int i = 0; i <= sheet.getLastRowNum(); ++i){
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
                    Document document = new Document("Название", normalizeName(val2.substring(0, pos != -1? pos: val2.length() )))
                            .append("Остаток", val20)
                            .append("Подгруппа", subgroup)
                            .append("Дата", date)
                            .append("сч", 21);
                    collection.insertOne(document);
                }
            } catch (NumberFormatException e){
                String string = cell0.getStringCellValue();
                if(string.contains("21")){
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

    private static void addIntoDb105(Sheet sheet, String filename) {
        log.info("Начали обрабатывать файл");
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
                                                    .append("сч", 105);
                                            //System.out.println(document);
                                            log.info("Грузим в БД");
                                            collection.insertOne(document);
                                        }
                                    } catch (IllegalStateException ex) {
                                        System.out.println("Error processing row for MongoDB insertion: " + ex.getMessage());
                                    }
                                }
                        }
                    }
                }
                i++;
            }
        }
    }

    private static void addIntoDb101(Sheet sheet, String filename) {
        String[] parts = filename.split("\\\\");

        String lastPart = parts[parts.length - 1];

        String date = lastPart.substring(22, 32);

        String subgroup = "";

        for(int i = 0; i <= sheet.getLastRowNum(); ++i){
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
                    Document document = new Document("Название", normalizeName(val2.substring(0, pos != -1? pos: val2.length() )))
                            .append("Остаток", val20)
                            .append("Подгруппа", subgroup)
                            .append("Дата", date)
                            .append("сч", 101);
                    collection.insertOne(document);
                }
            }catch (NumberFormatException e){
                String string = cell0.getStringCellValue();
                if(string.contains("101")){
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

    private static String normalizeName(String name) {
        return name.replaceAll("\\s", "").toLowerCase();
    }
}
