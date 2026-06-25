from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from .infra import db
import json
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.views.generic import CreateView, UpdateView, DeleteView, ListView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import Contact, Alerta
from .forms import ContactForm, CustomUserCreationForm, UserUpdateForm, AlertaForm

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
    form_class = CustomUserCreationForm
    template_name = 'auth/register.html'
    success_url = reverse_lazy('index')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'auth/user_form.html'
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

class ContatoView(LoginRequiredMixin, CreateView):
    """Permite que usuários logados enviem mensagens de contato.
    Pré-preenche o nome e email com dados do usuário logado.
    """
    model = Contact
    form_class = ContactForm
    template_name = 'contato.html'
    success_url = reverse_lazy('contato-success')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['usuario'] = self.request.user
        return context
    
    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.nome_completo = self.request.user.get_full_name() or self.request.user.username
        form.instance.email = self.request.user.email
        return super().form_valid(form)

def contato_success(request):
    """Página de sucesso após envio de contato."""
    return render(request, 'contato_success.html')

class RelatosListView(LoginRequiredMixin, ListView):
    """Lista as mensagens (relatos) do usuário logado."""
    model = Contact
    template_name = 'relatos/relatos_list.html'
    context_object_name = 'relatos'
    paginate_by = 10
    
    def get_queryset(self):
        return Contact.objects.filter(usuario=self.request.user, deletado=False)

class RelatosUpdateView(LoginRequiredMixin, UpdateView):
    """Permite que usuário edite sua mensagem nos primeiros 2 minutos."""
    model = Contact
    form_class = ContactForm
    template_name = 'relatos/relatos_form.html'
    success_url = reverse_lazy('relatos-list')
    
    def get_queryset(self):
        return Contact.objects.filter(usuario=self.request.user)
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.pode_editar():
            return redirect('relatos-list')
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        self.object.atualizado_em = timezone.now()
        return super().form_valid(form)

@require_http_methods(["POST"])
def relatos_delete(request, pk):
    """Soft delete de uma mensagem (marca como deletada)."""
    relato = get_object_or_404(Contact, pk=pk, usuario=request.user)
    relato.deletado = True
    relato.save()
    return redirect('relatos-list')

def logout_view(request):
    """Faz logout do usuário."""
    logout(request)
    return redirect('index')


class AlertaListView(LoginRequiredMixin, ListView):
    model = Alerta
    template_name = 'alertas/alerta_list.html'
    context_object_name = 'alertas'

    def get_queryset(self):
        return Alerta.objects.filter(user=self.request.user).order_by('-criado_em')


class AlertaCreateView(LoginRequiredMixin, CreateView):
    model = Alerta
    form_class = AlertaForm
    template_name = 'alertas/alerta_form.html'
    success_url = reverse_lazy('alerta-list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class AlertaUpdateView(LoginRequiredMixin, UpdateView):
    model = Alerta
    form_class = AlertaForm
    template_name = 'alertas/alerta_form.html'
    success_url = reverse_lazy('alerta-list')

    def get_queryset(self):
        return Alerta.objects.filter(user=self.request.user)


class AlertaDeleteView(LoginRequiredMixin, DeleteView):
    model = Alerta
    template_name = 'alertas/alerta_confirm_delete.html'
    success_url = reverse_lazy('alerta-list')

    def get_queryset(self):
        return Alerta.objects.filter(user=self.request.user)


@require_http_methods(["POST"])
def criar_alerta_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Usuário não autenticado.'}, status=401)

    try:
        data = json.loads(request.body)
        region_name, target_temp, repeat, active = _parse_alerta_payload(data)
        alerta = Alerta.objects.create(
            user=request.user,
            region_name=region_name,
            target_temp=target_temp,
            repeat=repeat,
            active=active,
        )
        return JsonResponse({'success': True, 'alerta_id': alerta.id, 'alerta': _alerta_to_dict(alerta)})
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def _alerta_to_dict(alerta):
    return {
        'id': alerta.id,
        'region_name': alerta.region_name,
        'target_temp': alerta.target_temp,
        'repeat': alerta.repeat,
        'active': alerta.active,
        'criado_em': alerta.criado_em.strftime('%d/%m/%Y %H:%M'),
    }


def _parse_alerta_payload(data):
    region_name = (data.get('region_name') or '').strip()
    if not region_name:
        raise ValueError('Nome da região é obrigatório.')
    target_temp = float(data.get('target_temp'))
    repeat = bool(data.get('repeat', True))
    active = bool(data.get('active', True))
    return region_name, target_temp, repeat, active


@require_http_methods(["GET", "POST"])
def alertas_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Usuário não autenticado.'}, status=401)

    if request.method == 'GET':
        alertas = Alerta.objects.filter(user=request.user).order_by('-criado_em')
        return JsonResponse({
            'success': True,
            'alertas': [_alerta_to_dict(a) for a in alertas],
        })

    try:
        data = json.loads(request.body)
        region_name, target_temp, repeat, active = _parse_alerta_payload(data)
        alerta = Alerta.objects.create(
            user=request.user,
            region_name=region_name,
            target_temp=target_temp,
            repeat=repeat,
            active=active,
        )
        return JsonResponse({'success': True, 'alerta': _alerta_to_dict(alerta)})
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["PATCH", "DELETE"])
def alerta_api_detail(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Usuário não autenticado.'}, status=401)

    alerta = get_object_or_404(Alerta, pk=pk, user=request.user)

    if request.method == 'DELETE':
        alerta.delete()
        return JsonResponse({'success': True})

    try:
        data = json.loads(request.body)
        if 'region_name' in data:
            region_name = (data.get('region_name') or '').strip()
            if not region_name:
                raise ValueError('Nome da região é obrigatório.')
            alerta.region_name = region_name
        if 'target_temp' in data:
            alerta.target_temp = float(data['target_temp'])
        if 'repeat' in data:
            alerta.repeat = bool(data['repeat'])
        if 'active' in data:
            alerta.active = bool(data['active'])
        alerta.save()
        return JsonResponse({'success': True, 'alerta': _alerta_to_dict(alerta)})
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["GET"])
def alertas_regioes_api(request):
    from .forms import obter_regioes
    regioes = [nome for nome, _ in obter_regioes()]
    return JsonResponse({'success': True, 'regioes': regioes})

