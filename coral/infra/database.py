import duckdb
from django.conf import settings

class db:    
    @staticmethod
    def obter_conexao(write: bool = False) -> duckdb.DuckDBPyConnection:
        db_path = getattr(settings, "DUCKDB_PATH", "data/data.db")
        con = duckdb.connect(db_path, read_only=not write)
        con.execute("INSTALL spatial;LOAD spatial;")  # INSTALL só precisa rodar uma vez
        return con