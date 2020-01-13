FROM puckel/docker-airflow:1.10.6
RUN pip install --user psycopg2-binary
ENV AIRFLOW_HOME=/usr/local/airflow
COPY ./airflow.cfg /usr/local/airflow/airflow.cfg
RUN mkdir /usr/local/airflow/packages
COPY ./packages.pth /usr/local/lib/python3.7/site-packages
