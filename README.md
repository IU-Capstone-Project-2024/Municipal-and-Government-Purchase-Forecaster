# Procurement Forecasting and Planning Service

This service leverages past procurement data and accounting information to:
- Visualize statistics
- Forecast procurement needs
- Prepare data for procurement planning

The goal of the service is to reduce the labor required by government institutions for procurement planning by automating the forecasting of product needs and their quantities.

## Features

- **Chat-Bot Interface**: Interact with the service through a user-friendly chat-bot.
- **Data Consolidation**: Integrates past procurement and accounting data.
- **Forecasting**: Uses machine learning models to predict future procurement needs.
- **Visualization**: Provides graphical representations and reports of procurement data.
- **Prediction Correcting In Place**: The user may change the resulting file in bot, withoud additional tools.

## Architecture

The architecture consists of the following key components:

1. **User Interface (UI)**
   - Chat-bot integrated with a popular messenger Telegram.
   
2. **Dialog Management Service**
   - Serves a user with friendly interface.
   - Handles user requests and manages dialog flows using NLP.
   
4. **Data Processing Service**
   - Consolidates, cleans, validates, and pre-processes procurement data.
   
5. **Analytics and Forecasting Service**
   - Analyzes historical data and uses ML model called ARIMA for forecasting.
   
6. **Data Visualization Service**
   - Creates charts and reports for data presentation.
   
7. **Database**
   - Stores procurement data, accounting data, and analysis results using and NoSQL (MongoDB) databases.
   
8. **Authentication and Authorization Service**
   - Manages user access to different service functions.
   - Uses keycloak, a very secure and popular application.

## Technology Stack

- **Chat-Bot and Interface**: Python, Aiogram
- **Data Processing and Analysis**: Python, pandas, scikit-learn
- **Database**: MongoDB
- **Visualization**: Python, pandas, matplotlib
- **Infrastructure and Deployment**: Docker, Docker Compose

## Getting Started

### Prerequisites

- Docker
- Python 3.8+
- MongoDB

### Installation

1. **Clone the repository**:
    ```sh
    git clone https://github.com/yourusername/procurement-forecasting-service.git
    cd procurement-forecasting-service
    ```

2. **Set up the environment**:
    - Create a `.env` file and populate it with the necessary environment variables.
    - Example:
      ```env
      DATABASE_URL=postgresql://username:password@localhost:5432/procurement_db
      MONGO_URL=mongodb://localhost:27017
      ```

3. **Build and run the services using Docker**:
    ```sh
    docker-compose up --build
    ```

### Usage

1. **Access the chat-bot**:
   - Access the chatbot in Telegram

2. **Interact with the chat-bot**:
   - Use natural language to request procurement data, forecasts, and visualizations.
   - Use friendly and simple buttons to do the same.


### User view and flow of the service
1. Firstly, you need to type /start in bot.


2. Authorize with keycloak via link wich bot has provided you


3. Accept that you authorized
   a. Accept user case

   b. Decline user case

4. Select what do you want to do
   1. Use buttons te flow then is simple: choose option and write a parameter that bot asks from you
   2. Type in your message with choosing the option and its parameters, e.g. Найди сколько осталось на складе бумаги.

6. Get the response and visuals if your request succeed

7. If you want to save the requested forecast, you can download tha json-file that was sent by bot
8. If you want to change the json in Telegram itself choose the button for editing
9. Update or keep as it was parameters of json
10. Save the updated json

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/YourFeature`).
3. Commit your changes (`git commit -am 'Add new feature'`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Create a new Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

