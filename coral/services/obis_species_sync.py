import requests
from coral.infra import db


class ObisSpeciesSync:

    def __init__(self):
        self.url_obis = "https://api.obis.org/v3/occurrence"
        self.url_dataset = "https://api.obis.org/v3/dataset"

        self.grupos_alvo = {
            "Coral": 1363,
            "Peixe": 10194,
            "Crustaceo": 1066,
        }

        # cache simples para evitar chamadas repetidas
        self.dataset_cache = {}

    # -------------------------
    # TABELAS
    # -------------------------
    def _criar_tabelas_se_nao_existirem(self, connection):

        connection.execute("""
            CREATE TABLE IF NOT EXISTS especies (
                aphia_id BIGINT PRIMARY KEY,
                nome_cientifico VARCHAR UNIQUE,
                nome_comum VARCHAR,
                grupo VARCHAR,

                reino VARCHAR,
                filo VARCHAR,
                classe VARCHAR,
                ordem VARCHAR,
                familia VARCHAR,
                genero VARCHAR,
                especie VARCHAR,

                scientific_name_id VARCHAR,
                taxon_rank VARCHAR
            );
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id UUID PRIMARY KEY,
                titulo TEXT,
                resumo TEXT,
                doi VARCHAR,
                citation TEXT,
                url VARCHAR,
                archive_url VARCHAR,
                instituicao TEXT,
                publicado_em TIMESTAMP,
                atualizado_em TIMESTAMP
            );
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS ocorrencias (
                id UUID PRIMARY KEY,

                aphia_id BIGINT,
                dataset_id UUID,

                regiao_id BIGINT,
                poligono_id BIGINT,

                latitude DOUBLE,
                longitude DOUBLE,
                profundidade DOUBLE,

                institution_code VARCHAR,
                collection_code VARCHAR,
                recorded_by VARCHAR
            );
        """)

    # -------------------------
    # DATASET ENRICHMENT
    # -------------------------
    def _get_dataset(self, dataset_id):
        if dataset_id in self.dataset_cache:
            return self.dataset_cache[dataset_id]

        try:
            r = requests.get(f"{self.url_dataset}/{dataset_id}", timeout=15)
            if r.status_code != 200:
                return None

            data = r.json().get("results", [])
            if not data:
                return None

            dataset = data[0]
            self.dataset_cache[dataset_id] = dataset
            return dataset

        except Exception:
            return None

    # -------------------------
    # SYNC PRINCIPAL
    # -------------------------
    def sincronizar(self, regiao_id=None, log_func=print):

        with db.obter_conexao(True) as connection:
            self._criar_tabelas_se_nao_existirem(connection)

            query_regioes = """
                SELECT 
                    id AS regiao_id,
                    unnest.path[1] AS poligono_id,
                    ST_AsText(ST_Envelope(unnest.geom)) AS envelope_wkt
                FROM regiao
                CROSS JOIN LATERAL unnest(ST_Dump(areas)) AS g
            """

            if regiao_id:
                query_regioes += f" WHERE id = {regiao_id}"

            sub_poligonos = connection.execute(query_regioes).fetchall()

            if not sub_poligonos:
                log_func("Nenhum polígono encontrado.")
                return

            for reg_id, poly_id, envelope_wkt in sub_poligonos:
                log_func(f"Região {reg_id} / Polígono {poly_id}")

                for grupo, taxon_id in self.grupos_alvo.items():

                    params = {
                        "geometry": envelope_wkt,
                        "taxonid": taxon_id,
                        "size": 500,
                        "startdepth": 0,   # Começa na superfície
                        "enddepth": 30,
                    }

                    try:
                        response = requests.get(self.url_obis, params=params, timeout=15)

                        if response.status_code != 200:
                            continue

                        resultados = response.json().get("results", [])
                        if not resultados:
                            continue

                        log_func(f"  {grupo}: {len(resultados)} registros")

                        for item in resultados:

                            aphia_id = item.get("aphiaID")
                            nome_cientifico = item.get("scientificName")

                            if not aphia_id or not nome_cientifico:
                                continue

                            # -------------------------
                            # ESPÉCIE
                            # -------------------------
                            connection.execute("""
                                INSERT INTO especies (
                                    aphia_id,
                                    nome_cientifico,
                                    grupo,
                                    reino,
                                    filo,
                                    classe,
                                    ordem,
                                    familia,
                                    genero,
                                    especie,
                                    scientific_name_id,
                                    taxon_rank
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT (aphia_id) DO NOTHING
                            """, (
                                int(aphia_id),
                                nome_cientifico,
                                grupo,
                                item.get("kingdom"),
                                item.get("phylum"),
                                item.get("class"),
                                item.get("order"),
                                item.get("family"),
                                item.get("genus"),
                                item.get("species"),
                                item.get("scientificNameID"),
                                item.get("taxonRank"),
                            ))

                            # -------------------------
                            # DATASET
                            # -------------------------
                            dataset_id = item.get("dataset_id")

                            if dataset_id:
                                dataset = self._get_dataset(dataset_id)

                                if dataset:
                                    connection.execute("""
                                        INSERT INTO datasets (
                                            dataset_id,
                                            titulo,
                                            resumo,
                                            doi,
                                            citation,
                                            url,
                                            archive_url,
                                            instituicao,
                                            publicado_em,
                                            atualizado_em
                                        )
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        ON CONFLICT (dataset_id) DO NOTHING
                                    """, (
                                        dataset.get("id"),
                                        dataset.get("title"),
                                        dataset.get("abstract"),
                                        dataset.get("citation_id"),
                                        dataset.get("citation"),
                                        dataset.get("url"),
                                        dataset.get("archive"),
                                        None,
                                        dataset.get("published"),
                                        dataset.get("updated"),
                                    ))

                            # -------------------------
                            # OCORRÊNCIA
                            # -------------------------
                            connection.execute("""
                                INSERT INTO ocorrencias (
                                    id,
                                    aphia_id,
                                    dataset_id,
                                    regiao_id,
                                    poligono_id,
                                    latitude,
                                    longitude,
                                    profundidade,
                                    institution_code,
                                    collection_code,
                                    recorded_by
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT DO NOTHING
                            """, (
                                item.get("id"),
                                int(aphia_id),
                                dataset_id,
                                reg_id,
                                poly_id,
                                item.get("decimalLatitude"),
                                item.get("decimalLongitude"),
                                item.get("depth"),
                                item.get("institutionCode"),
                                item.get("collectionCode"),
                                item.get("recordedBy"),
                            ))

                    except requests.exceptions.RequestException as e:
                        log_func(f"[ERRO API] {grupo}: {e}")