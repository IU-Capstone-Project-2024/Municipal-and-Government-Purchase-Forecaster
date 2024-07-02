package ru.hackaton.config;

import lombok.Data;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.PropertySource;

/**
 * Конфигурационный класс для приложения.
 *
 * Этот класс используется для загрузки настроек из файла `application.properties`.
 *
 * Аннотация {@link Configuration} указывает, что этот класс является конфигурационным классом Spring.
 * Аннотация {@link PropertySource} указывает, что файл свойств `application.properties` должен быть использован для конфигурации.
 * Аннотация {@link Data} от Lombok автоматически генерирует геттеры и сеттеры для полей класса.
 */
@Configuration
@Data
@PropertySource("application.properties")
public class ApplicationConfig {

    /**
     * URL для подключения к MongoDB.
     *
     * Значение загружается из свойства `mongo.url` в файле `application.properties`.
     */
    @Value("${mongo.url}")
    String mongoUrl;
}
