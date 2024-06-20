package ru.hackaton.service;

import com.mongodb.client.*;
import com.mongodb.client.model.Filters;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.bson.Document;
import org.bson.conversions.Bson;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.*;

@Slf4j
@Data
@Component
public class SimilarProductFromDB {
    private static final int THREAD_POOL_SIZE = 5;
    private static final int MAX_PRODUCTS_IN_MESSAGE = 350;
    private static MongoClient client = MongoClients.create("mongodb://localhost:27017");
    private static MongoDatabase db = client.getDatabase("stock_remainings");
    private static MongoCollection<Document> collection = db.getCollection("Складские остатки");
    @Autowired
    private ChatGPTService chatGPTService;

    public List<String> mostSimilarProduct(String product) {
        FindIterable<Document> stocksss = collection.find();

        Set<String>stocks = new HashSet<>();
        for (var doc: stocksss) {
            stocks.add(doc.getString("полное название"));
        }

        var st = searchViaPrefixFunction(stocks, product);
        if (st.isEmpty()) {
            return new ArrayList<>();
        }
        if (st.size() < 5) {
            List<String> answer = new ArrayList<>();
            answer.addAll(st);
            return answer;
        }
        return simpleSearchViaChatGPT(st, product);
    }

    private Set<String> searchViaPrefixFunction(Set<String>stocks, String product) {
        String[] words = product.split(" ");
        Set<String>answer = new HashSet<>();
        Set<String>normStrs = new HashSet<>();
        for (var word: words) {
            for (String doc : stocks) {
                String norm = normalize(doc);
                if (containsSubstring(norm, normalize(word))) {
                    if (normStrs.contains(norm))
                        continue;
                    normStrs.add(norm);
                    answer.add(doc);
                }
            }
        }
        return answer;
    }

    private List<String> simpleSearchViaChatGPT(Set<String>st, String product) {
        String PROMPT = "У вас есть список товаров со склада ниже, необходимо найти ровно 5 наиболее похожих товаров на основе поискового запроса \"" + product + "\" и вывести только эти товары, строго название каждого товара в отдельной строчке, и строго без лишнего текста и форматирования.\n" +
                "Список товаров, каждый товар в отдельной строке:";
        StringBuilder builder = new StringBuilder();
        for (String str: st)
            builder.append(str).append("\n");
        List<String> answer = List.of(chatGPTService.sendMessage(PROMPT, builder.toString()).split("\n"));
        return answer;
    }

//    private String searchViaChatGPT(Set<String>stocks, String product) {
//        String PROMPT = "У вас есть список товаров со склада ниже, необходимо найти ровно 5 наиболее похожих товаров на основе поискового запроса \"" + product + "\" и вывести только эти товары, строго название каждого товара в отдельной строчке, и строго без лишнего текста и форматирования.\n" +
//                "Список товаров, каждый товар в отдельной строке:";
//        ExecutorService executorService = Executors.newFixedThreadPool(THREAD_POOL_SIZE);
//        List<Callable<String>> tasks = new ArrayList<>();
//
//        StringBuilder requestBuilder = new StringBuilder();
//        int k = 0;
//        for (var document: stocks) {
//            requestBuilder.append(document).append("\n");
//            k += 1;
//            if (k == MAX_PRODUCTS_IN_MESSAGE) {
//                String question = requestBuilder.toString();
//                tasks.add(() -> chatGPTService.sendMessage(PROMPT, question));
//                log.info(question);
//                requestBuilder.setLength(0);
//                k = 0;
//            }
//        }
//        if (k != 0) {
//            tasks.add(() -> chatGPTService.sendMessage(PROMPT, requestBuilder.toString()));
//        }
//
//        List<Future<String>> results;
//
//        try {
//            results = executorService.invokeAll(tasks);
//
//            executorService.shutdown();
//
//            StringBuilder answer = new StringBuilder();
//
//            for (Future<String> result : results) {
//                System.out.println(result.get());
//                System.out.println();
//                if (result.get().equals("404"))
//                    continue;
//                answer.append(result.get()).append("\n");
//            }
//            String result = answer.toString();
//            if (result.isEmpty()) {
//                log.error("Результат чаток нулевый");
//                return "404";
//            }
//            String[] linesArray = result.split("\\r?\\n");
//            if (linesArray.length > 5) {
//                log.info("Результат чаток больше 5");
//                Set<String> st = new HashSet<>();
//                StringBuilder builder = new StringBuilder();
//                for (var doc: linesArray) {
//                    if (st.contains(doc))
//                        continue;
//                    st.add(doc);
//                    if (doc.equals("404"))
//                        continue;
//                    builder.append(doc).append("\n");
//                    System.out.println(doc);
//                }
//                return builder.toString();
////                String result2 = chatGPTService.sendMessage(PROMPT, builder.toString());
////                String[] linesArr2 = result2.split("\\r?\\n");
////                StringBuilder build = new StringBuilder();
////                for (var lin: linesArr2)
////                    build.append(lin).append("\n");
////                return build.toString();
//            } else {
//                log.info("Результат чаток меньше 5");
//                Set<String> st = new HashSet<>();
//                StringBuilder builder = new StringBuilder();
//                for (var doc: linesArray) {
//                    if (st.contains(doc))
//                        continue;
//                    st.add(doc);
//                    if (doc.equals("404"))
//                        continue;
//                    builder.append(doc).append("\n");
//                    System.out.println(doc);
//                }
//                return builder.toString();
//            }
//        } catch (InterruptedException e) {
//            log.error("Error while executing tasks", e);
//            Thread.currentThread().interrupt();
//        } catch (ExecutionException e) {
//            throw new RuntimeException(e);
//        }
//        return "У нас проблемы";
//    }

    private String normalize(String str) {
        str = str.toLowerCase();
        return str;
    }

    private int[] computePrefixFunction(String pattern) {
        int m = pattern.length();
        int[] pi = new int[m];
        int k = 0;
        for (int i = 1; i < m; i++) {
            while (k > 0 && pattern.charAt(k) != pattern.charAt(i)) {
                k = pi[k - 1];
            }
            if (pattern.charAt(k) == pattern.charAt(i)) {
                k++;
            }
            pi[i] = k;
        }
        return pi;
    }

    private boolean containsSubstring(String text, String pattern) {
        int n = text.length();
        int m = pattern.length();
        if (m == 0) {
            return true;
        }
        int[] pi = computePrefixFunction(pattern);
        int q = 0;
        for (int i = 0; i < n; i++) {
            while (q > 0 && pattern.charAt(q) != text.charAt(i)) {
                q = pi[q - 1];
            }
            if (pattern.charAt(q) == text.charAt(i)) {
                q++;
            }
            if (q == m) {
                return true;
            }
        }
        return false;
    }
}
