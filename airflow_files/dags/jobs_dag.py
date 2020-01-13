from airflow import DAG
from airflow.models import Connection, Variable
from airflow.hooks.postgres_hook import PostgresHook
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.postgres_custom import PostgreSQLCountRowsOperator
from airflow.utils.trigger_rule import TriggerRule
from airflow.ti_deps.deps.trigger_rule_dep import TriggerRuleDep
from datetime import datetime
import logging
import uuid

dag_number = int(Variable.get('dag_number'))
config = {}
for id in range(dag_number):
    config['dag_id_{}'.format(id)] = \
        {"start_date": datetime(2019, 12, 1), "table_name": "table_name_{}".format(id)}


def process_db_table(dag_id, database, **context):
    logging.info('{dag_id} start processing tables in database: {database}'.format(
        dag_id=dag_id,
        database=database
    ))


def check_table_existance(sql_to_get_schema, sql_to_check_table_exist, table_name, **context):
    hook = PostgresHook()
    query = hook.get_records(sql=sql_to_get_schema)
    logging.info(query)
    for result in query:
        if 'airflow' in result:
            schema = result[0]
            logging.info(schema)
            break

    query = hook.get_first(sql=sql_to_check_table_exist.format(schema, table_name))
    logging.info(query)

    return 'skip_table_creation' if query else 'create_table'


def push_finished_state(query, **context):
    hook = PostgresHook()
    records = hook.get_records(sql=query)
    context['ti'].xcom_push(key='count_rows',
                            value=records[0])
    logging.info(query)


for dag_id in config:
    dag = DAG(
        dag_id=dag_id,
        default_args=config[dag_id],
        schedule_interval=None
    )

    start_processing_tables_in_db = PythonOperator(
        task_id='start_processing_tables_in_database',
        provide_context=True,
        python_callable=process_db_table,
        op_kwargs=dict(
            dag_id=dag_id,
            database='airflow'
        ),
        dag=dag
    )
    get_current_user = BashOperator(
        task_id='get_current_user',
        bash_command='echo $USER',
        xcom_push=True,
        dag=dag
    )
    check_table_exist = BranchPythonOperator(
        task_id='check_table_exist',
        provide_context=True,
        python_callable=check_table_existance,
        op_kwargs=dict(
            sql_to_get_schema="SELECT * FROM pg_tables;",
            sql_to_check_table_exist="SELECT * FROM information_schema.tables "
                                     "WHERE table_schema = '{}'"
                                     "AND table_name = '{}';",
            table_name='clients'
        ),
        dag=dag
    )
    create_table = PostgresOperator(
        task_id='create_table',
        postgres_conn_id='postgres_default',
        sql="CREATE TABLE clients ("
            "custom_id integer NOT NULL,"
            "user_name VARCHAR (50) NOT NULL,"
            "timestamp TIMESTAMP NOT NULL);",
        dag=dag
    )
    skip_table_creation = DummyOperator(
        task_id='skip_table_creation',
        dag=dag
    )
    insert_new_row = PostgresOperator(
        task_id='insert_new_row',
        postgres_conn_id='postgres_default',
        sql="INSERT INTO clients VALUES(%s, '{{ ti.xcom_pull(task_ids='get_current_user') }}', %s)",
        parameters=(uuid.uuid4().int % 123456789, datetime.now()),
        trigger_rule=TriggerRule.ALL_DONE,
        dag=dag
    )
    query_the_table = PostgreSQLCountRowsOperator(
        task_id='query_the_table',
        table_name='clients',
        provide_context=True,
        dag=dag
    )
    start_processing_tables_in_db >> get_current_user >> check_table_exist >> \
        [create_table, skip_table_creation] >> insert_new_row >> query_the_table

    globals().update({dag_id: dag})


