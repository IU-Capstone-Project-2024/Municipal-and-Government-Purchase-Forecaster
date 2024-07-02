package ru.hackaton;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Главный класс приложения, который запускает Spring Boot приложение.
 */
@SpringBootApplication
@EnableScheduling
public class Main {

    /**
     * Точка входа в приложение. Метод запускает Spring Boot приложение.
     *
     * @param args аргументы командной строки
     */
    public static void main(String[] args) {
        SpringApplication.run(Main.class, args);
    }
}
