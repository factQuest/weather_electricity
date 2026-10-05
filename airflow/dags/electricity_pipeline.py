import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

PROJECT_DIR_WIN = os.environ["ELECTRICITY_PROJECT_DIR_WIN"]
WINDOWS_PYTHON = os.environ["WINDOWS_PYTHON"]
WINDOWS_DBT = os.environ["WINDOWS_DBT"]


with DAG(
    dag_id="electricity_pipeline",
    start_date=datetime(2026, 9, 1),
    schedule="0 1 * * *",
    catchup=True,
    tags=["electricity", "elt"],
) as dag:

    extract_data = BashOperator(
        task_id="extract_data",
        bash_command=(
            f'"{WINDOWS_PYTHON}" '
            f'"{PROJECT_DIR_WIN}\\extract.py"'
        ),
    )

    run_dbt = BashOperator(
        task_id="run_dbt",
        bash_command=(
            f'"{WINDOWS_DBT}" run '
            f'--project-dir "{PROJECT_DIR_WIN}\\dbt"'
        ),
    )

    extract_data >> run_dbt