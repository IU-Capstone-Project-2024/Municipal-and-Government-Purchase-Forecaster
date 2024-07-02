package ru.hackaton.parsers;

import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.bson.Document;
import org.springframework.stereotype.Component;
import ru.hackaton.config.ApplicationConfig;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Component
@Data
@Slf4j
public class TurnoversParser {
    final ApplicationConfig config;
    private static MongoClient client;
    private static MongoDatabase db;
    private static MongoCollection<Document> collection;
    private static final String EXCEPTION_LOG = "Exception occurred: {}";
    private static final String SUCCESS_UPLOAD = "Файл успешно загружен";

    /**
     * Конструктор для инициализации компонента.
     *
     * @param config конфигурация приложения, содержащая URL для подключения к MongoDB
     */
    public TurnoversParser(ApplicationConfig config) {
        this.config = config;
        client = MongoClients.create(config.getMongoUrl());
        db = client.getDatabase("stock_remainings");
        collection = db.getCollection("Оборотная ведомость");
    }

    /**
     * Метод для обработки файла с оборотами.
     *
     * @param file файл для обработки
     */
    public void processFile(File file) {
        log.info("Пришел новый файл turnovers: {}", file.getName());
        if (file.getName().contains("сч_21")) {
            process21(file);
        } else if (file.getName().contains("сч_105")) {
            process105(file);
        } else if (file.getName().contains("сч_101")) {
            process101(file);
        } else {
            log.error("Skipping {}, no matching function found", file.getName());
        }
    }

    /**
     * Обработка файла с кодом счёта 105.
     *
     * @param file файл для обработки
     */
    private void process105(File file) {
        log.info("Файл сч 105");
        try (FileInputStream fis = new FileInputStream(file)) {
            Workbook workbook = new XSSFWorkbook(fis);
            Sheet sheet = workbook.getSheetAt(0);

            String[] quarterYear = extractQuarterYear(file.getName());
            String quarter = quarterYear[0];
            String year = quarterYear[1];
            String subgroup = null;

            int i = 2;
            while (i <= sheet.getLastRowNum()) {
                Row row = sheet.getRow(i);

                if (row.getCell(0) == null || row.getCell(0).toString().isEmpty()) {

                    if(row.getCell(1) != null && !row.getCell(1).getStringCellValue().isEmpty()){
                        subgroup = row.getCell(1).getStringCellValue().split(" ")[0];
                    } else{
                        i++;
                        continue;
                    }

                } else if (row.getCell(3) != null && row.getCell(3).getStringCellValue().equals("Итого")) {
                    break;
                } else {
                    String name = row.getCell(3).getStringCellValue();
                    if(name.isEmpty()){
                        i++;
                        continue;
                    }
                    double countBeforeDebet = getCellValue(row.getCell(5));
                    double priceBeforeDebet = getCellValue(row.getCell(6));
                    priceBeforeDebet = Double.isNaN(countBeforeDebet) ? priceBeforeDebet : priceBeforeDebet / countBeforeDebet;

                    double priceInDebet = getCellValue(row.getCell(8));
                    double countInDebet = getCellValue(row.getCell(7));
                    priceInDebet = Double.isNaN(countInDebet) ? priceInDebet : priceInDebet / countInDebet;

                    double priceInKredit = getCellValue(row.getCell(10));
                    double countInKredit = getCellValue(row.getCell(9));
                    priceInKredit = Double.isNaN(countInKredit) ? priceInKredit : priceInKredit / countInKredit;

                    double priceAfterDebet = getCellValue(row.getCell(12));
                    double countAfterDebet = getCellValue(row.getCell(11));
                    priceAfterDebet = Double.isNaN(countAfterDebet) ? priceAfterDebet : priceAfterDebet / countAfterDebet;

                    Map<String, Object> data = new HashMap<>();
                    data.put("name", normalizeName(name));
                    data.put("единиц до", countBeforeDebet);
                    data.put("цена до", priceBeforeDebet);
                    data.put("цена дебет во", priceInDebet);
                    data.put("единиц дебет во", countInDebet);
                    data.put("цена кредит во", priceInKredit);
                    data.put("единиц кредит во", countInKredit);
                    data.put("цена после", priceAfterDebet);
                    data.put("единиц после", countAfterDebet);
                    data.put("группа", 105);
                    data.put("подгруппа", subgroup);
                    data.put("квартал", quarter);
                    data.put("год", year);
                    data.put("единица измерения", row.getCell(4).getStringCellValue());

                    insertDataToDb(data);
                }
                i++;
            }
            log.info(SUCCESS_UPLOAD);
        } catch (IOException e) {
            log.error(EXCEPTION_LOG, e.getMessage());
        }
    }


    private double getCellValue(Cell cell) {
        if (cell == null) {
            return Double.NaN;
        }
        switch (cell.getCellType()) {
            case NUMERIC:
                return cell.getNumericCellValue();
            case STRING:
                try {
                    return Double.parseDouble(cell.getStringCellValue());
                } catch (NumberFormatException e) {
                    return Double.NaN;
                }
            default:
                return Double.NaN;
        }
    }

    private boolean isNaN(double value) {
        return Double.isNaN(value);
    }

    /**
     * Общая логика обработки данных из листа Excel.
     *
     * @param sheet     лист Excel
     * @param quarter   квартал
     * @param year      год
     * @param group     код группы (21, 101, 105)
     * @param rowIndex  индекс начала обработки строк
     * @param nameIndex индекс столбца с наименованием
     */
    private void processCommonLogic(Sheet sheet, String quarter, String year, int group, int rowIndex, int nameIndex) {
        String subgroup = null;
        int index = rowIndex;
        while (index < sheet.getPhysicalNumberOfRows()) {
            Row row = sheet.getRow(index);
            Row nextRow = sheet.getRow(index + 1);
            if (row == null || row.getCell(0) == null) {
                break;
            }

            String cellValue = row.getCell(0).toString();
            if (cellValue.matches(group + "\\.\\d+")) {
                subgroup = cellValue;
            } else if ("Итого".equals(cellValue)) {
                break;
            } else if (subgroup != null && !cellValue.isEmpty()) {
                String name = row.getCell(nameIndex).toString();
                // Processing logic here.
                double countBeforeDebet = getCellValue(nextRow.getCell(10));
                double priceBeforeDebet = getCellValue(row.getCell(10));
                priceBeforeDebet = isNaN(countBeforeDebet) ? priceBeforeDebet : priceBeforeDebet / countBeforeDebet;

                double priceInDebet = getCellValue(row.getCell(12));
                double countInDebet = getCellValue(nextRow.getCell(12));
                priceInDebet = isNaN(countInDebet) ? priceInDebet : priceInDebet / countInDebet;

                double priceInKredit = getCellValue(row.getCell(13));
                double countInKredit = getCellValue(nextRow.getCell(13));
                priceInKredit = isNaN(countInKredit) ? priceInKredit : priceInKredit / countInKredit;

                double priceAfterDebet = getCellValue(row.getCell(14));
                double countAfterDebet = getCellValue(nextRow.getCell(14));
                priceAfterDebet = isNaN(countAfterDebet) ? priceAfterDebet : priceAfterDebet / countAfterDebet;

                // Insert data to DB
                Map<String, Object> data = new HashMap<>();
                // Populate data map with required fields
                data.put("name", normalizeName(name));
                data.put("группа", group);
                data.put("подгруппа", subgroup);
                data.put("квартал", quarter);
                data.put("год", year);
                data.put("единиц до", countBeforeDebet);
                data.put("цена до", priceBeforeDebet);
                data.put("цена дебет во", priceInDebet);
                data.put("единиц дебет во", countInDebet);
                data.put("цена кредит во", priceInKredit);
                data.put("единиц кредит во", countInKredit);
                data.put("цена после", priceAfterDebet);
                data.put("единиц после", countAfterDebet);
                data.put("единица измерения", "шт.");
                // Insert to DB
                insertDataToDb(data);
                index += 3;
            }
            index++;
        }
    }

    /**
     * Извлечение квартала и года из имени файла.
     *
     * @param filename имя файла
     * @return массив строк с кварталом и годом
     */
    private String[] extractQuarterYear(String filename) {
        Pattern quarterPattern = Pattern.compile("(\\d+) кв\\.");
        Pattern yearPattern = Pattern.compile("кв\\. (\\d+)");
        Matcher quarterMatcher = quarterPattern.matcher(filename);
        Matcher yearMatcher = yearPattern.matcher(filename);
        String quarter = quarterMatcher.find() ? quarterMatcher.group(1) : null;
        String year = yearMatcher.find() ? yearMatcher.group(1) : null;
        return new String[]{quarter, year};
    }

    /**
     * Вставка данных в MongoDB.
     *
     * @param data данные для вставки
     */
    private void insertDataToDb(Map<String, Object> data) {
        collection.insertOne(new Document(data));
    }

    /**
     * Обработка файла с кодом счёта 21.
     *
     * @param file файл для обработки
     */
    private void process21(File file) {
        log.info("Файл сч 21");
        try (FileInputStream fis = new FileInputStream(file); Workbook workbook = new XSSFWorkbook(fis)) {
            Sheet sheet = workbook.getSheetAt(0);
            String[] quarterYear = extractQuarterYear(file.getName());
            processCommonLogic(sheet, quarterYear[0], quarterYear[1], 21, 9, 0);
            log.info(SUCCESS_UPLOAD);
        } catch (IOException e) {
            log.error(EXCEPTION_LOG, e.getMessage());
        }
    }

    /**
     * Обработка файла с кодом счёта 101.
     *
     * @param file файл для обработки
     */
    private void process101(File file) {
        log.info("Файл сч 101");
        try (FileInputStream fis = new FileInputStream(file); Workbook workbook = new XSSFWorkbook(fis)) {
            Sheet sheet = workbook.getSheetAt(0);
            String[] quarterYear = extractQuarterYear(file.getName());
            processCommonLogic(sheet, quarterYear[0], quarterYear[1], 101, 9, 0);
            log.info(SUCCESS_UPLOAD);
        } catch (IOException e) {
            log.error(EXCEPTION_LOG, e.getMessage());
        }
    }

    private String normalizeName(String name) {
        return name.replaceAll("\\s", "").toLowerCase();
    }
}
