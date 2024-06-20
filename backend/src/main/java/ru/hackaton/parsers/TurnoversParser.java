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
    private static MongoClient client = MongoClients.create("mongodb://localhost:27017");
    private static MongoDatabase db = client.getDatabase("stock_remainings");
    private static MongoCollection<Document> collection = db.getCollection("Обороты по счету");

    public void processFile(File file) {
        if (file.getName().contains("сч_21")) {
            process21(file);
        } else if (file.getName().contains("сч_105")) {
            process105(file);
        } else if (file.getName().contains("сч_101")) {
            process101(file);
        } else {
            System.out.println("Skipping " + file.getName() + ", no matching function found");
        }
    }

    private void process105(File file) {
        try (FileInputStream fis = new FileInputStream(file)) {
            Workbook workbook = new XSSFWorkbook(fis);
            Sheet sheet = workbook.getSheetAt(0);

            String[] quarterYear = extractQuarterYear(file.getName());
            String quarter = quarterYear[0];
            String year = quarterYear[1];
            String subgroup = null;

            int i = 3;
            while (i <= sheet.getLastRowNum()) {
                Row row = sheet.getRow(i);

                if (row.getCell(0) == null) {
                    if(row.getCell(1) != null){
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
                    data.put("цена до", priceBeforeDebet);
                    data.put("единицы до", countBeforeDebet);
                    data.put("цена во деб", priceInDebet);
                    data.put("единицы во деб", countInDebet);
                    data.put("цена во кред", priceInKredit);
                    data.put("единицы во кред", countInKredit);
                    data.put("цена после", priceAfterDebet);
                    data.put("единицы после", countAfterDebet);
                    data.put("группа", 105);
                    data.put("подгруппа", subgroup);
                    data.put("квартал", quarter);
                    data.put("год", year);

                    insertDataToDb(data);
                }
                i++;
            }
        } catch (IOException e) {
            e.printStackTrace();
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
                // Insert to DB
                insertDataToDb(data);
                index += 3;
            }
            index++;
        }
    }

    private String[] extractQuarterYear(String filename) {
        Pattern quarterPattern = Pattern.compile("(\\d+) кв\\.");
        Pattern yearPattern = Pattern.compile("кв\\. (\\d+)");
        Matcher quarterMatcher = quarterPattern.matcher(filename);
        Matcher yearMatcher = yearPattern.matcher(filename);
        String quarter = quarterMatcher.find() ? quarterMatcher.group(1) : null;
        String year = yearMatcher.find() ? yearMatcher.group(1) : null;
        return new String[]{quarter, year};
    }

    private void insertDataToDb(Map<String, Object> data) {
        collection.insertOne(new Document(data));
    }

    private void process21(File file) {
        try (FileInputStream fis = new FileInputStream(file); Workbook workbook = new XSSFWorkbook(fis)) {
            Sheet sheet = workbook.getSheetAt(0);
            String[] quarterYear = extractQuarterYear(file.getName());
            processCommonLogic(sheet, quarterYear[0], quarterYear[1], 21, 9, 0);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private void process101(File file) {
        try (FileInputStream fis = new FileInputStream(file); Workbook workbook = new XSSFWorkbook(fis)) {
            Sheet sheet = workbook.getSheetAt(0);
            String[] quarterYear = extractQuarterYear(file.getName());
            processCommonLogic(sheet, quarterYear[0], quarterYear[1], 101, 9, 0);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private String normalizeName(String name) {
        return name.replaceAll("\\s", "").toLowerCase();
    }
}
