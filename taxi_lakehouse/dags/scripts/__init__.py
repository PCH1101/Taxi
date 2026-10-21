"""
NYC Taxi Lakehouse Pipeline — DAG Tasks Package
===============================================
Modular Airflow task callables for Bronze, Silver, Gold, and Quality checks.
"""

from .bronze import check_data_files, ingest_bronze
from .silver import populate_silver
from .gold import rebuild_gold

__all__ = [
    "check_data_files",
    "ingest_bronze",
    "populate_silver",
    "rebuild_gold",
]
