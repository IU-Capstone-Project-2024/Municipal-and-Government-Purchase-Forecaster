package ru.hackaton.parsers;

import lombok.Data;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;

/**
 * Компонент Spring для преобразования объектов MultipartFile в File.
 * Этот компонент отвечает за преобразование MultipartFile во временный File, который можно использовать в дальнейших операциях.
 */
@Component
@Data
public class FromMultipartToFile {

    /**
     * Преобразует объект MultipartFile в File.
     *
     * @param multipartFile объект MultipartFile, который необходимо преобразовать
     * @return временный файл типа File, созданный из MultipartFile
     */
    public File convertMultipartFileToFile(MultipartFile multipartFile) {
        File file = new File(multipartFile.getOriginalFilename());
        try (FileOutputStream fos = new FileOutputStream(file)) {
            fos.write(multipartFile.getBytes());
        } catch (IOException e) {
            e.printStackTrace();
        }
        return file;
    }
}
