from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import requests
import json
import os

def extract_crypto_data(**kwargs):
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    crypto_symbols = ['BTC', 'ETH']
    base_currency = 'USD'
    raw_data_list = []
    successful_symbols = []
    failed_symbols = []

    for symbol in crypto_symbols:
        url = f'https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={symbol}&market={base_currency}&apikey={api_key}'
        print(f"Fetching data for {symbol} from URL: {url.split('apikey')[0]}...")
        try:
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            if 'Error Message' in data:
                error_msg = data['Error Message']
                print(f'Error from API for {symbol}: {error_msg}')
                failed_symbols.append(symbol)
                continue
            if 'Information' in data:
                info_msg = data['Information']
                print(f"Info from API for {symbol}: {info_msg}")
                failed_symbols.append(symbol)
                continue
            if 'Meta Data' not in data:
                print(f"Unexpected API response structure for {symbol}. Response: {data}")
                failed_symbols.append(symbol)
                continue
            data['Meta Data']['symbol'] = symbol
            raw_data_list.append(data)
            successful_symbols.append(symbol)
            print(f"Successfully fetched data for {symbol}.")

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occured for {symbol}")
            failed_symbols.append(symbol)
        except Exception as err:
            print(f"Other error occured for {symbol}: {err}")
            failed_symbols.append(symbol)

    print(f"Successfully processed symbols: {successful_symbols}")
    print(f"Failed symbols: {failed_symbols}")

    if not raw_data_list:
        raise ValueError("All API requests failed! Check logs for details.")
    kwargs['ti'].xcom_push(key='raw_crypto_data', value=raw_data_list)
    return raw_data_list



def load_raw_data_to_postgres(**kwargs):
    try:
        ti = kwargs['ti']
        raw_data_list = ti.xcom_pull(task_ids='extract_crypto_data', key='raw_crypto_data')
        if not raw_data_list:
            raise ValueError("No data received from XCom. The 'extract' task might have failed. Check logs.")
        pg_hook = PostgresHook(
            postgres_conn_id='postgres_conn',
            schema='airflow',
            user='airflow',
            password='airflow',
            host='postgres',
            port=5432
        )
        conn = pg_hook.get_conn()
        cursor = conn.cursor()

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS raw_crypto_data (
            id SERIAL PRIMARY KEY,
            data JSONB NOT NULL,
            symbol VARCHAR(10) NOT NULL,
            ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_sql)
        print('Table checked/created successfully.')

        for data in raw_data_list:
            symbol = data['Meta Data']['symbol']
            data_json = json.dumps(data)
            insert_sql = """
            INSERT INTO raw_crypto_data (data, symbol)
            VALUES (%s, %s);
            """
            print(f"Inserting data for {symbol}")
            cursor.execute(insert_sql, (data_json, symbol))
        conn.commit()
        print("Data successfully loaded into pgsql.")
    except Exception as e:
        print(f"An error occured during database operation: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        raise e
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        print("DB connection closed.")
        
default_args ={
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'crypto_etl_pipeline',
    default_args=default_args,
    description='A simple crypto ETL pipeline',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2025, 9, 14),
    catchup=False,
    tags=['crypto', 'etl'],
) as dag:
    extract_task = PythonOperator(
        task_id='extract_crypto_data',
        python_callable=extract_crypto_data,
        provide_context=True,
    )

    load_task = PythonOperator(
        task_id='load_raw_data_to_postgres',
        python_callable=load_raw_data_to_postgres,
        provide_context=True,
    )

    extract_task >> load_task