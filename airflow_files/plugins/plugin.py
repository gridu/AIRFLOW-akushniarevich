from airflow.hooks.postgres_hook import PostgresHook
from airflow.models import BaseOperator
from airflow.plugins_manager import AirflowPlugin
from airflow.utils.decorators import apply_defaults
import logging


class PostgreSQLCountRowsOperator(BaseOperator):
    @apply_defaults
    def __init__(self, table_name,
                 *args, **kwargs):
        """

        :param table_name: table name
        """
        self.table_name = table_name
        self.hook = PostgresHook()
        super(PostgreSQLCountRowsOperator, self).__init__(*args, **kwargs)

    def execute(self, context):
        record = self.hook.get_first(sql="SELECT COUNT(*) FROM {};".format(self.table_name))
        context['ti'].xcom_push(key='count_rows',
                            value=record[0])
        logging.info("Result: {}".format(record[0]))


class PostgreSQLCustomOperatorsPlugin(AirflowPlugin):
    name = 'postgres_custom'
    operators = [PostgreSQLCountRowsOperator]
