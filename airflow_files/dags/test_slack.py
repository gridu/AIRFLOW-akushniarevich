from datetime import datetime
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator

from slack import *

with DAG(dag_id='dependency_dag',
         start_date=datetime(2020, 1, 7),
         schedule_interval=None) as dag:
    DummyOperator(task_id='dummy')
