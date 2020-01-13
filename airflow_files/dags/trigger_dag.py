from airflow import DAG
from airflow.models import Variable
from airflow.contrib.sensors.file_sensor import FileSensor
from airflow.operators.dagrun_operator import TriggerDagRunOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.subdag_operator import SubDagOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor
from datetime import datetime, timedelta
import logging


dag_number = Variable.get('dag_number', default_var=5)
run_flag_path = Variable.get('run_flag_path')


def print_result_to_log(**context):
    count_rows = context['ti'].xcom_pull(dag_id='dag_id_0',
                                         task_ids='query_the_table',
                                         key='count_rows')
    logging.info(count_rows)
    logging.info(context)


def create_process_results(parent_dag_name, child_dag_name, schedule_interval, start_date):
    subdag = DAG(
        dag_id='{}.{}'.format(parent_dag_name, child_dag_name),
        schedule_interval=schedule_interval,
        start_date=start_date
    )

    sensor_triggered_dag = ExternalTaskSensor(
        task_id='sensor_triggered_dag',
        external_dag_id='dag_id_0',
        external_task_id=None,
        # execution_date_fn=lambda exec_date: exec_date,
        allowed_states=['success'],
        mode='reschedule',
        poke_interval=20,
        dag=subdag
    )

    print_result = PythonOperator(
        task_id='print_result',
        python_callable=print_result_to_log,
        provide_context=True,
        dag=subdag
    )

    remove_run_file = BashOperator(
        task_id='remove_run_file',
        bash_command='rm $AIRFLOW_HOME/storage/{}'.format(run_flag_path),
        dag=subdag
    )

    finished_timestamp = BashOperator(
        task_id='finished_timestamp',
        bash_command='touch $AIRFLOW_HOME/finished_{{ ts_nodash }}',
        dag=subdag
    )

    sensor_triggered_dag >> print_result >> remove_run_file >> finished_timestamp

    return subdag


dag = DAG(
    dag_id='trigger_dag',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2019, 12, 27)
)

check_run_file_exists = FileSensor(
    task_id='check_file_exists',
    filepath=run_flag_path,
    fs_conn_id='fs_airflow',
    poke_interval=20,
    dag=dag
)

trigger_dags = TriggerDagRunOperator(
    task_id='trigger_dags',
    trigger_dag_id='dag_id_0',
    execution_date='{{ execution_date }}',
    dag=dag
)

process_results = SubDagOperator(
    task_id='process_results',
    subdag=create_process_results(parent_dag_name=dag.dag_id,
                                  child_dag_name='process_results',
                                  schedule_interval=dag.schedule_interval,
                                  start_date=dag.start_date
                                  ),
    dag=dag
)

check_run_file_exists >> trigger_dags >> process_results
