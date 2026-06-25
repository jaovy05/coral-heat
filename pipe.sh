START_DATE="2026-01-01"
END_DATE="2026-03-01"

for REGIAO in {1..30}; do
    echo "========================================"
    echo "Processando região $REGIAO"
    echo "========================================"

    python3 manage.py allimentTemp \
        --regiao "$REGIAO" \
        --start_date "$START_DATE" \
        --end_date "$END_DATE"

    python3 manage.py allimentPlancton \
        --regiao "$REGIAO" \
        --start_date "$START_DATE" \
        --end_date "$END_DATE"

    python3 manage.py mergeBases
done