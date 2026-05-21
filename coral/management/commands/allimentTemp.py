from datetime import date
import io
from django.core.management.base import BaseCommand, CommandError
import copernicusmarine
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import duckdb
import time
import gc

class Command(BaseCommand):


    def _parse_date(self, value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            # Lançar CommandError faz o Django exibir uma mensagem amigável 
            # em vez de um erro de código (Traceback)
            raise CommandError(f"A data '{value}' não está no formato ISO (AAAA-MM-DD).")

    def add_arguments(self, parser):
        # Usamos o _parse_date como o tipo para validar na entrada
        parser.add_argument('start_date', type=self._parse_date)
        parser.add_argument('end_date', type=self._parse_date)
        parser.add_argument('--regiao', type=int)

    def salvar_duckdb(self, df, regiaogem):  
        start_duck = time.perf_counter()
        con = duckdb.connect("data/data.db")
        con.execute("LOAD spatial;")
        con.execute("""
            CREATE TABLE IF NOT EXISTS monitoramento_temp_mar (
                time DATE, 
                latitude FLOAT, 
                longitude FLOAT, 
                profundidade FLOAT, 
                temperatura FLOAT, 
                salinidade FLOAT, 
                corrente_zonal FLOAT,
                corrente_meridional FLOAT
            )
        """)

        con.execute("""
            INSERT INTO monitoramento_temp_mar 
            SELECT 
                time, 
                latitude, 
                longitude, 
                depth as profundidade, 
                thetao as temperatura, 
                so as salinidade, 
                uo as corrente_zonal,
                vo as corrente_meridional   
            FROM df
            WHERE ST_Within(
                ST_Point(longitude, latitude), 
                ST_GeomFromText(?)
            )
        """, [regiaogem])
        end = time.perf_counter() - start_duck
        self.stdout.write(f"Thread DuckBd terminou")
        con.close()
        return end
    
    def getRegiao(self, regiaoID):
        """
        Explode um MultiPolygon em Polígonos individuais diretamente via DuckDB Spatial
        e retorna o BBox de cada um para alimentar o laço do Copernicus.
        """
        query = """
            WITH sub_poligonos AS (
                select 
                    UNNEST(ST_Dump(areas)).geom AS poli
                FROM regiao
                WHERE id = ?
            )
            SELECT 
                ST_XMin(poli) AS min_lon,
                ST_XMax(poli) AS max_lon,
                ST_YMin(poli) AS min_lat,
                ST_YMax(poli) AS max_lat,
                ST_AsText(poli) AS wkt                
            FROM sub_poligonos;
        """
    
        with duckdb.connect('data/data.db') as con:
            con.execute("LOAD spatial;")
            # Retorna uma lista de dicionários nativos do Python
            return con.execute(query, [regiaoID]).fetchall()


    def handle(self, *args, **kwargs):
        initial_date = kwargs['start_date']
        final_date = kwargs['end_date']
        regiao =  kwargs['regiao']

        if final_date < initial_date:
            raise CommandError('Final date must be on or after initial date.')

        regiao_coords = self.getRegiao(regiao)
        


        tempo_duck_total = 0
        linhas_total = 0
        try:
            for coords in regiao_coords:
                min_lon, max_lon, min_lat, max_lat, regiaogem = coords
                current_date = initial_date
                while current_date <= final_date:
                    final_datetemp = min(current_date + pd.Timedelta(days=1825), final_date)

                    self.stdout.write(f"Processando data: {current_date.isoformat()} até {final_datetemp.isoformat()}")
                    start_read = time.perf_counter()
                    df = copernicusmarine.read_dataframe(
                        dataset_id="cmems_mod_glo_phy_my_0.083deg_P1D-m",
                        dataset_version="202311",  # Fixa a versão
                        dataset_part="default",    # Fixa a parte
                        variables=["thetao", "so", "uo", "vo"],
                        minimum_longitude=min_lon,
                        maximum_longitude=max_lon,
                        minimum_latitude=min_lat,
                        maximum_latitude=max_lat,
                        start_datetime=current_date.isoformat(),
                        end_datetime=final_datetemp.isoformat(),
                        minimum_depth=2.0,
                        maximum_depth=10.0,
                    )

                    df.reset_index(inplace=True)
                    df.dropna(subset=['thetao'], inplace=True)
                    df['thetao'] = df['thetao'].astype('float32')

                    df['time'] = pd.to_datetime(df['time']).dt.date
                    tempo_leitura = time.perf_counter() - start_read
                    
                    linhas = len(df)
                    self.stdout.write(f"DataFrame carregado: {linhas} linhas em {tempo_leitura:.2f}s")
                    tempo_duck = self.salvar_duckdb(df, regiaogem)
                    gc.collect()

                    # --- RELATÓRIO DE PERFORMANCE DA ETAPA ---
                    self.stdout.write("\n" + "-"*40)
                    self.stdout.write(self.style.SUCCESS(f"Lote Concluído: {linhas} linhas"))
                    self.stdout.write(f"DuckDB:     {tempo_duck:.4f}s")
                    self.stdout.write("-"*40)

                    # Acumuladores globais
                    tempo_duck_total += tempo_duck
                    linhas_total += linhas
                    
                    # Avança a data para o próximo loop
                    current_date = final_datetemp + pd.Timedelta(days=1)
                
                # --- RELATÓRIO DE PERFORMANCE ETAPA ---
                self.stdout.write("\n" + "="*30)
                self.stdout.write(self.style.SUCCESS(f"Dados processados: {linhas_total} linhas"))
                self.stdout.write(f"Tempo DuckDB: {tempo_duck_total:.4f}s")
                self.stdout.write("="*30 + "\n")
        except Exception as e:
            raise CommandError(f"Erro na operação: {e}")