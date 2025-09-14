# Crypto ETL Pipeline

Автоматизированный ETL-пайплайн для ежедневного сбора данных о курсах криптовалют с Alpha Vantage, их преобразования и загрузки в аналитическое хранилище.

## 🛠 Tech Stack

- **Orchestration:** Apache Airflow
- **Data Storage:** PostgreSQL
- **Transformation:** dbt (data build tool)
- **Infrastructure:** Docker & Docker Compose
- **Source:** Alpha Vantage API

## 📁 Project Structure
crypto_etl_pipeline/
├── dags/ # Airflow DAGs
├── dbt/ # dbt project (models, sources, etc.)
├── scripts/ # Вспомогательные скрипты
├── config/ # Конфигурационные файлы
├── docker-compose.yml # Docker Compose для инфраструктуры
├── .env.example # Пример файла с переменными окружения
└── README.md