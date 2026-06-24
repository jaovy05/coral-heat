from datetime import date

from django.shortcuts import render, redirect
from django.http import JsonResponse, Http404
from .infra import db
import json
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView

# Create your views here.
def index(request):
    with db.obter_conexao() as con:
        result = con.execute("""
            SELECT 
                id,
                pais, 
                ST_AsGeoJSON(areas) as coordenadas  -- Assumindo que isto retorna uma string GeoJSON ou WKT
            FROM regiao
        """).fetchall()
        
    recifes = []
    for id, pais, geojson_str in result:
        recifes.append({
            'id': id,
            'pais': pais,
            'coordenadas': json.loads(geojson_str)
        })
        
  
    return render(request, 'index.html', {
        'recifes': recifes
    })

def getMediaMes(request):
    regiao_id_raw = request.GET.get('id') or request.GET.get('pais')
    profundidade_raw = request.GET.get('profundidade', 2.64567)

    if not regiao_id_raw:
        raise Http404("Região não fornecida")

    try:
        regiao_id = int(regiao_id_raw)
    except (TypeError, ValueError):
        raise Http404("ID de região inválido")

    try:
        profundidade = float(profundidade_raw)
    except (TypeError, ValueError):
        profundidade = 2.64567
    
    with db.obter_conexao() as conn:
        regiao = conn.execute("""
            SELECT id, pais
            FROM regiao
            WHERE id = $1
        """, (regiao_id,)).fetchone()

        if not regiao:
            raise Http404("Região não encontrada")

        result = conn.execute("""
            WITH sub_poligonos AS (
                SELECT unnest.geom AS poly, unnest.path AS index
                FROM regiao
                CROSS JOIN LATERAL unnest(ST_Dump(areas)) AS g
                WHERE id = $1
            )
            SELECT 
                COUNT(mar.ponto) AS qtd_leitura,
                ROUND(AVG(mar.temperatura), 2)          AS media_temperatura,
                ROUND(AVG(mar.salinidade), 2)           AS media_salinidade,
                ROUND(AVG(mar.corrente_zonal), 2)       AS media_corrente_zonal,
                ROUND(AVG(mar.corrente_meridional), 2)  AS media_corrente_meridional,
                ROUND(AVG(mar.oxigenio), 2)             AS media_oxigenio,
                ROUND(AVG(mar.plancton), 2)             AS media_plancton
            FROM monitoramento mar
            JOIN sub_poligonos sub ON ST_Contains(sub.poly, mar.ponto::GEOMETRY)
            WHERE mar.time >= date_trunc('month', current_date)
              AND mar.time < date_trunc('month', current_date) + INTERVAL '1 month'
              AND mar.profundidade BETWEEN $2 - 0.001 AND $2 + 0.001
        """, (regiao_id, profundidade)).fetch_df().to_dict(orient='records')
    
    return JsonResponse({
        'id': regiao[0],
        'pais': regiao[1],
        'profundidade': profundidade,
        'periodo': date.today().strftime('%m/%Y'),
        'dados': result
    })


def getMediaDetalhes(request):
    regiao_id_raw = request.GET.get('id') or request.GET.get('pais')
    profundidade_raw = request.GET.get('profundidade', 2.64567)

    if not regiao_id_raw:
        raise Http404("Região não fornecida")

    try:
        regiao_id = int(regiao_id_raw)
    except (TypeError, ValueError):
        raise Http404("ID de região inválido")

    try:
        profundidade = float(profundidade_raw)
    except (TypeError, ValueError):
        profundidade = 2.64567
    
    with db.obter_conexao() as conn:
        regiao = conn.execute("""
            SELECT id, pais
            FROM regiao
            WHERE id = $1
        """, (regiao_id,)).fetchone()

        if not regiao:
            raise Http404("Região não encontrada")

        result = conn.execute("""
            WITH sub_poligonos AS (
                SELECT unnest.geom AS poly, unnest.path[1] AS regioes_index -- path em ST_Dump é um array, pegamos o primeiro índice
                FROM regiao
                CROSS JOIN LATERAL unnest(ST_Dump(areas)) AS g
                WHERE id = $1
            ),
            dados_filtrados AS (
                SELECT 
                    sub.regioes_index,
                    mar.time,
                    -- Calcula o início do intervalo de 3 dias para cada registro
                    date_trunc('month', current_date) + 
                    (CAST(EXTRACT(DAY FROM mar.time - date_trunc('month', current_date)) AS INT) / 3 * 3 || ' days')::INTERVAL AS periodo_3_dias,
                    mar.temperatura,
                    mar.salinidade,
                    mar.corrente_zonal,
                    mar.corrente_meridional,
                    mar.oxigenio,
                    mar.plancton
                FROM monitoramento mar
                JOIN sub_poligonos sub ON ST_Contains(sub.poly, mar.ponto::GEOMETRY)
                WHERE mar.time >= date_trunc('month', current_date)
                AND mar.time < date_trunc('month', current_date) + INTERVAL '1 month'
                AND mar.profundidade BETWEEN $2 - 0.001 AND $2 + 0.001
            )
            SELECT 
                regioes_index AS sub_regiao_id,
                periodo_3_dias AS inicio_periodo,
                COUNT(*) AS qtd_leitura,
                ROUND(AVG(temperatura), 2)          AS media_temperatura,
                ROUND(AVG(salinidade), 2)           AS media_salinidade,
                ROUND(AVG(corrente_zonal), 2)       AS media_corrente_zonal,
                ROUND(AVG(corrente_meridional), 2)  AS media_corrente_meridional,
                ROUND(AVG(oxigenio), 2)             AS media_oxigenio,
                ROUND(AVG(plancton), 2)             AS media_plancton
            FROM dados_filtrados
            GROUP BY regioes_index, periodo_3_dias
ORDER BY regioes_index, periodo_3_dias;
        """, (regiao_id, profundidade)).fetch_df().to_dict(orient='records')
    
    return JsonResponse({
        'id': regiao[0],
        'pais': regiao[1],
        'profundidade': profundidade,
        'periodo': date.today().strftime('%m/%Y'),
        'dados': result
    })


def getDadosDia(request):
    # pais = request.GET.get('pais')  # Exemplo: obter o país da query
    profundidade_raw = request.GET.get('profundidade', 2.64567)
    try:
        profundidade = float(profundidade_raw)
    except (ValueError, TypeError):
        profundidade = 2.64567

    with db.obter_conexao() as conn:
        result = conn.execute("""
            SELECT 
                temperatura,
                ROUND(st_y(ponto), 5) AS lat, 
                ROUND(st_x(ponto), 5) AS lng,
                profundidade
            FROM monitoramento
            WHERE time = today() 
                AND profundidade BETWEEN ($1 - 0.001) AND ($1 + 0.001)
        """, (profundidade,)).fetch_df().to_dict(orient='records')


        extreme_temp = conn.execute("""
            select  round(max(temperatura), 2) - 2, 
                    round(min(temperatura), 2) + 2
            from monitoramento
        """,).fetchone()

    return JsonResponse({
        'dados': result,
        'extreme_temperatura': extreme_temp
    }, safe=False)        

class UserCreateView(CreateView):
    model = User
    form_class = UserCreationForm
    template_name = 'user_form.html'
    success_url = reverse_lazy('index')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    fields = ['username', 'email']
    template_name = 'user_form.html'
    success_url = reverse_lazy('index')

    def get_object(self, queryset=None):
        return self.request.user

class UserDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    template_name = 'user_confirm_delete.html'
    success_url = reverse_lazy('index')

    def get_object(self, queryset=None):
        return self.request.user

def sobre(request):
    """Página estática 'Sobre' com fatos críticos e lista de ONGs.
    Template: coral/templates/sobre.html
    """
    return render(request, 'sobre.html')
