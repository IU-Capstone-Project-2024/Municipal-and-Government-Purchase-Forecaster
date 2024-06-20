FROM openjdk:22-ea-28-jdk-bullseye

RUN apt-get update && apt-get install -y python3 python3-pip

WORKDIR /backend

COPY . /backend

RUN pip3 install --no-cache-dir -r requirements.txt

RUN mkdir -p /var/log/project

RUN chmod +x ./mvnw

RUN ./mvnw package spring-boot:repackage

CMD ["java", "-jar", "target/backend-1.0-SNAPSHOT.jar"]
