const METRICAS_INFO = {
    temperatura: "A temperatura elevada causa o branqueamento dos corais, expulsando as algas simbiontes que fornecem energia e cor.",
    salinidade: "Mudanças bruscas na salinidade afetam a regulação osmótica dos pólipos, podendo levar à morte do coral.",
    corrente_zonal: "Correntes zonais transportam nutrientes e larvas. Alterações afetam a dispersão e a alimentação.",
    corrente_meridional: "Essenciais para a troca de calor e nutrientes. Impactam a temperatura local e a clareza da água.",
    oxigenio: "Essencial para a respiração dos organismos. Níveis baixos (hipóxia) podem causar estresse severo na comunidade.",
    plancton: "Base da cadeia alimentar. Níveis adequados garantem a nutrição, níveis excessivos podem causar eutrofização."
};

const METRICAS_DETALHE = [
    {
        key: 'temperatura',
        field: 'media_temperatura',
        label: 'Temperatura',
        icon: 'thermometer',
        unit: '°C',
        digits: 1,
        color: '#ffae30',
        title: 'Temperatura da Água',
        subtitle: 'Variação média por período'
    },
    {
        key: 'salinidade',
        field: 'media_salinidade',
        label: 'Salinidade',
        icon: 'droplets',
        unit: 'PSU',
        digits: 2,
        color: '#4cd7ff',
        title: 'Salinidade',
        subtitle: 'Concentração por período'
    },
    {
        key: 'corrente_zonal',
        field: 'media_corrente_zonal',
        label: 'Corrente Zonal',
        icon: 'move-horizontal',
        unit: 'm/s',
        digits: 2,
        color: '#9bdbff',
        title: 'Corrente Zonal',
        subtitle: 'Fluxo leste/oeste'
    },
    {
        key: 'corrente_meridional',
        field: 'media_corrente_meridional',
        label: 'Corrente Meridional',
        icon: 'move-vertical',
        unit: 'm/s',
        digits: 2,
        color: '#7cd4b4',
        title: 'Corrente Meridional',
        subtitle: 'Fluxo norte/sul'
    },
    {
        key: 'oxigenio',
        field: 'media_oxigenio',
        label: 'Oxigênio',
        icon: 'wind',
        unit: 'mg/L',
        digits: 2,
        color: '#8be3d0',
        title: 'Oxigênio Dissolvido',
        subtitle: 'Disponibilidade respiratória'
    },
    {
        key: 'plancton',
        field: 'media_plancton',
        label: 'Plâncton',
        icon: 'activity',
        unit: 'u.a.',
        digits: 2,
        color: '#d6a4ff',
        title: 'Plâncton',
        subtitle: 'Distribuição biológica'
    }
];

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    })[char]);
}

function formatMetric(value, digits = 2) {
    const numeric = Number(value);
    if (Number.isNaN(numeric)) {
        return '--';
    }
    return numeric.toFixed(digits);
}

function formatPeriodoLabel(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return String(value ?? '--');
    }
    return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short' }).format(date);
}

function groupDetalhesPorPeriodo(dados) {
    const buckets = new Map();

    (dados || []).forEach((row) => {
        const periodoRaw = row.inicio_periodo || row.periodo || row.time;
        const periodo = periodoRaw ? new Date(periodoRaw) : null;
        const key = periodo && !Number.isNaN(periodo.getTime()) ? periodo.toISOString() : String(periodoRaw ?? row.sub_regiao_id ?? buckets.size);
        const weight = Math.max(Number(row.qtd_leitura) || 0, 1);

        if (!buckets.has(key)) {
            buckets.set(key, {
                key,
                periodo,
                label: formatPeriodoLabel(periodoRaw),
                weightTotal: 0,
                media_temperatura: 0,
                media_salinidade: 0,
                media_corrente_zonal: 0,
                media_corrente_meridional: 0,
                media_oxigenio: 0,
                media_plancton: 0
            });
        }

        const bucket = buckets.get(key);
        bucket.weightTotal += weight;

        METRICAS_DETALHE.forEach((metric) => {
            const numeric = Number(row[metric.field]);
            if (Number.isFinite(numeric)) {
                bucket[metric.field] += numeric * weight;
            }
        });
    });

    return Array.from(buckets.values())
        .sort((a, b) => {
            const aTime = a.periodo ? a.periodo.getTime() : 0;
            const bTime = b.periodo ? b.periodo.getTime() : 0;
            return aTime - bTime;
        })
        .map((bucket) => {
            const divisor = bucket.weightTotal || 1;
            return {
                periodo: bucket.periodo,
                label: bucket.label,
                qtd_leitura: bucket.weightTotal,
                media_temperatura: bucket.media_temperatura / divisor,
                media_salinidade: bucket.media_salinidade / divisor,
                media_corrente_zonal: bucket.media_corrente_zonal / divisor,
                media_corrente_meridional: bucket.media_corrente_meridional / divisor,
                media_oxigenio: bucket.media_oxigenio / divisor,
                media_plancton: bucket.media_plancton / divisor
            };
        });
}

function average(values) {
    const filtered = values.filter((value) => Number.isFinite(value));
    if (!filtered.length) {
        return null;
    }
    return filtered.reduce((acc, value) => acc + value, 0) / filtered.length;
}

function calcularResumoModal(series) {
    if (!series.length) {
        return {
            avgTemperature: null,
            minTemperature: null,
            maxTemperature: null,
            avgSalinity: null,
            avgOxygen: null,
            avgPlankton: null,
            totalReadings: 0,
            healthScore: 0,
            healthClass: 'modal-stat-value--critical',
            healthLabel: 'Sem dados',
            healthNote: 'Nenhuma leitura consolidada',
            statusClass: 'modal-stat-value--critical',
            statusLabel: 'Indefinido',
            statusNote: 'Sem medições para o período'
        };
    }

    const avgTemperature = average(series.map((item) => item.media_temperatura));
    const minTemperature = Math.min(...series.map((item) => item.media_temperatura));
    const maxTemperature = Math.max(...series.map((item) => item.media_temperatura));
    const avgSalinity = average(series.map((item) => item.media_salinidade));
    const avgOxygen = average(series.map((item) => item.media_oxigenio));
    const avgPlankton = average(series.map((item) => item.media_plancton));
    const totalReadings = series.reduce((acc, item) => acc + (Number(item.qtd_leitura) || 0), 0);

    let healthScore = 100;
    if (avgTemperature !== null) {
        healthScore -= Math.abs(avgTemperature - 27.8) * 12;
    }
    if (avgOxygen !== null) {
        healthScore -= Math.max(0, 6.4 - avgOxygen) * 6;
    }
    if (avgPlankton !== null) {
        healthScore -= Math.max(0, avgPlankton - 1.2) * 3;
    }
    healthScore = Math.max(0, Math.min(100, Math.round(healthScore)));

    const statusLabel = healthScore >= 75 ? 'Estável' : healthScore >= 50 ? 'Atenção' : 'Crítico';
    const statusClass = healthScore >= 50 ? '' : 'modal-stat-value--critical';
    const healthClass = healthScore >= 75 ? 'modal-stat-value--good' : healthScore >= 50 ? '' : 'modal-stat-value--critical';

    return {
        avgTemperature,
        minTemperature,
        maxTemperature,
        avgSalinity,
        avgOxygen,
        avgPlankton,
        totalReadings,
        healthScore,
        healthClass,
        healthLabel: `${healthScore}%`,
        healthNote: 'Indicador visual do recife',
        statusClass,
        statusLabel,
        statusNote: healthScore >= 75 ? 'Monitoramento ativo' : 'Acompanhamento recomendado'
    };
}

function renderMetricChart(series, metricKey) {
    const metric = METRICAS_DETALHE.find((item) => item.key === metricKey) || METRICAS_DETALHE[0];

    if (!series.length) {
        return `
            <div class="modal-chart__empty">
                Sem dados suficientes para desenhar ${escapeHtml(metric.label.toLowerCase())}.
            </div>
        `;
    }

    const values = series.map((item) => Number(item[metric.field])).filter((value) => Number.isFinite(value));
    if (!values.length) {
        return '<div class="modal-chart__empty">Sem dados para esta métrica.</div>';
    }

    const width = 860;
    const height = 320;
    const padding = { top: 24, right: 24, bottom: 80, left: 58 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const range = Math.max(maxValue - minValue, 0.5);

    const points = series.map((item, index) => {
        const value = Number(item[metric.field]);
        const normalized = Number.isFinite(value) ? (value - minValue) / range : 0;
        const x = padding.left + (series.length === 1 ? plotWidth / 2 : (index / (series.length - 1)) * plotWidth);
        const y = padding.top + (1 - normalized) * plotHeight;
        return {
            x,
            y,
            value,
            label: item.label
        };
    });

    const linePath = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(' ');
    const areaPath = [
        `M ${points[0].x.toFixed(1)} ${height - padding.bottom}`,
        ...points.map((point) => `L ${point.x.toFixed(1)} ${point.y.toFixed(1)}`),
        `L ${points[points.length - 1].x.toFixed(1)} ${height - padding.bottom}`,
        'Z'
    ].join(' ');

    const yLines = Array.from({ length: 4 }, (_, index) => {
        const ratio = index / 3;
        const value = maxValue - ratio * range;
        const y = padding.top + ratio * plotHeight;
        return `
            <line x1="${padding.left}" y1="${y.toFixed(1)}" x2="${width - padding.right}" y2="${y.toFixed(1)}" stroke="rgba(145, 201, 222, 0.16)" stroke-width="1" />
            <text x="${padding.left - 10}" y="${y.toFixed(1)}" text-anchor="end" dominant-baseline="middle" fill="rgba(200, 233, 246, 0.75)" font-size="11">${formatMetric(value, metric.digits)} ${metric.unit}</text>
        `;
    }).join('');

    // ... (keeping previous content) ...
        const xLabels = points.map((point) => {
            const x = point.x.toFixed(1);
            const y = height - 14;
            return `
                <text
                    x="${x}"
                    y="${y}"
                    transform="rotate(60 ${x} ${y})"
                    text-anchor="end"
                    fill="rgba(200, 233, 246, 0.75)"
                    font-size="11"
                >${escapeHtml(point.label)}</text>
            `;
        }).join('');
    // ... (rest of function renderMetricChart)


    const dots = points.map((point) => `
        <circle 
            cx="${point.x.toFixed(1)}" 
            cy="${point.y.toFixed(1)}" 
            r="5" 
            fill="${metric.color}" 
            stroke="#fff" 
            stroke-width="2" 
            style="cursor: pointer;"
            onmouseover="showTooltip(evt, '${escapeHtml(point.label)}', '${formatMetric(point.value, metric.digits)} ${metric.unit}')"
            onmouseout="hideTooltip()"
        />
    `).join('');

    return `
        <div class="modal-chart">
            <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(metric.title)}">
                <defs>
                    <linearGradient id="modal-${metric.key}-fill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="${metric.color}" stop-opacity="0.55" />
                        <stop offset="100%" stop-color="${metric.color}" stop-opacity="0" />
                    </linearGradient>
                </defs>
                ${yLines}
                <path d="${areaPath}" fill="url(#modal-${metric.key}-fill)" opacity="0.9"></path>
                <path d="${linePath}" fill="none" stroke="${metric.color}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"></path>
                ${dots}
                ${xLabels}
            </svg>
            <div id="modal-chart-tooltip" class="modal-chart-tooltip"></div>
        </div>
    `;
}

function showTooltip(evt, label, value) {
    const tooltip = document.getElementById("modal-chart-tooltip");
    tooltip.innerHTML = `<strong>${label}</strong><br>${value}`;
    tooltip.style.display = "block";
    tooltip.style.left = (evt.clientX + 10) + "px";
    tooltip.style.top = (evt.clientY + 10) + "px";
}

function hideTooltip() {
    const tooltip = document.getElementById("modal-chart-tooltip");
    tooltip.style.display = "none";
}

function renderMetricCards(series, selectedMetric) {
    const latest = series[series.length - 1] || {};

    return METRICAS_DETALHE.map((metric) => `
        <div
            role="button"
            tabindex="0"
            class="modal-metric-card ${metric.key === selectedMetric ? 'is-active' : ''}"
            data-metric="${metric.key}"
        >
            <button
                type="button"
                id="metric-info-${metric.key}"
                class="modal-metric-info-btn"
                popovertarget="popover-${metric.key}"
                popovertargetaction="toggle"
                aria-label="Informações sobre ${escapeHtml(metric.label)}"
            >
                <i data-lucide="help-circle" style="width: 16px; height: 16px;"></i>
            </button>
            <div id="popover-${metric.key}" popover="auto" class="modal-popover" anchor="metric-info-${metric.key}">
                ${METRICAS_INFO[metric.key] || 'Informação não disponível.'}
            </div>
            <span class="modal-metric-card__icon">
                <i data-lucide="${metric.icon}" style="width: 16px; height: 16px;"></i>
            </span>
            <span class="modal-metric-card__label">${escapeHtml(metric.label)}</span>
            <strong class="modal-metric-card__value">
                ${formatMetric(latest[metric.field], metric.digits)} <span>${metric.unit}</span>
            </strong>
            <span class="modal-metric-card__note">Clique para trocar o gráfico</span>
        </div>
    `).join('');
}

function mountMetricSwitcher(modalState) {
    const root = document.getElementById('media-mes-modal');
    if (!root) {
        return;
    }

    root.querySelectorAll('.modal-popover[popover]').forEach((popover) => {
        popover.addEventListener('toggle', (event) => {
            if (event.newState !== 'open') {
                return;
            }
            root.querySelectorAll('.modal-popover[popover]').forEach((other) => {
                if (other !== popover && other.matches(':popover-open')) {
                    other.hidePopover();
                }
            });
        });
    });

    root.querySelectorAll('.modal-metric-info-btn').forEach((btn) => {
        btn.addEventListener('click', (event) => event.stopPropagation());
    });

    const cards = root.querySelectorAll('.modal-metric-card');
    cards.forEach((card) => {
        const activate = () => {
            const metricKey = card.dataset.metric;
            if (!metricKey || metricKey === modalState.selectedMetric) {
                return;
            }
            modalState.selectedMetric = metricKey;
            atualizarGraficoModal(modalState);
        };

        card.addEventListener('click', (event) => {
            if (event.target.closest('.modal-metric-info-btn')) {
                return;
            }
            activate();
        });
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                activate();
            }
        });
    });
}

function atualizarGraficoModal(modalState) {
    const chartRoot = document.getElementById('media-mes-chart-root');
    const chartTitle = document.getElementById('media-mes-chart-title');
    const chartSubtitle = document.getElementById('media-mes-chart-subtitle');
    const metric = METRICAS_DETALHE.find((item) => item.key === modalState.selectedMetric) || METRICAS_DETALHE[0];

    if (chartRoot) {
        chartRoot.innerHTML = renderMetricChart(modalState.series, metric.key);
    }
    if (chartTitle) {
        chartTitle.textContent = metric.title;
    }
    if (chartSubtitle) {
        chartSubtitle.textContent = metric.subtitle;
    }

    document.querySelectorAll('#media-mes-modal .modal-metric-card').forEach((card) => {
        card.classList.toggle('is-active', card.dataset.metric === metric.key);
    });

    if (window.lucide?.createIcons) {
        lucide.createIcons();
    }
}

function renderAlertaSection(regiao, resumo) {
    const regionName = regiao?.pais || '';
    const suggestedTemp = resumo?.avgTemperature != null
        ? Number(resumo.avgTemperature).toFixed(1)
        : '28.0';

    if (!window.__USER_AUTHENTICATED__) {
        return `
            <section class="modal-section modal-alerta-section">
                <div class="modal-alerta-section__title">
                    <i data-lucide="bell" style="width: 18px; height: 18px;"></i>
                    Alertas por e-mail
                </div>
                <p class="modal-alerta-section__subtitle">Cadastre um alerta para ser avisado quando a temperatura ultrapassar o limite.</p>
                <div class="modal-alerta-guest">
                    <a href="/login/?next=${encodeURIComponent(window.location.pathname)}">Faça login</a> para criar alertas de temperatura nesta região.
                </div>
            </section>
        `;
    }

    return `
        <section class="modal-section modal-alerta-section">
            <div class="modal-alerta-section__title">
                <i data-lucide="bell" style="width: 18px; height: 18px;"></i>
                Alertas por e-mail
            </div>
            <p class="modal-alerta-section__subtitle">O cron diário enviará e-mail se a média do dia atingir ou ultrapassar o limite.</p>
            <form id="modal-alerta-form" class="modal-alerta-form">
                <label class="alerta-field">
                    <span>Região</span>
                    <input type="text" name="region_name" value="${escapeHtml(regionName)}" readonly>
                </label>
                <label class="alerta-field">
                    <span>Temperatura limite (°C)</span>
                    <input type="number" name="target_temp" step="0.1" min="0" max="45" value="${suggestedTemp}" required>
                </label>
                <button type="submit" class="alerta-btn alerta-btn--primary">Cadastrar alerta</button>
            </form>
            <label class="alerta-check">
                <input type="checkbox" name="repeat" id="modal-alerta-repeat" form="modal-alerta-form" checked>
                <span>Repetir alerta por e-mail</span>
            </label>
            <p id="modal-alerta-message" class="modal-alerta-message" hidden></p>
        </section>
    `;
}

function mountAlertaForm(regiao, resumo) {
    const form = document.getElementById('modal-alerta-form');
    const message = document.getElementById('modal-alerta-message');
    if (!form || !window.criarAlerta) {
        return;
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const repeatCheckbox = document.getElementById('modal-alerta-repeat');
        const payload = {
            region_name: form.region_name.value,
            target_temp: parseFloat(form.target_temp.value),
            repeat: repeatCheckbox ? repeatCheckbox.checked : true,
            active: true,
        };

        if (message) {
            message.hidden = false;
            message.textContent = 'Salvando alerta...';
            message.classList.remove('modal-alerta-message--error');
        }

        try {
            await window.criarAlerta(payload);
            if (message) {
                message.textContent = 'Alerta cadastrado! Você receberá e-mail quando o limite for atingido.';
            }
        } catch (err) {
            if (message) {
                message.textContent = err.message || 'Não foi possível cadastrar o alerta.';
                message.classList.add('modal-alerta-message--error');
            }
        }
    });
}

function renderResumoModal(payload, regiao, modalState) {
    const series = modalState.series;
    const resumo = modalState.resumo;

    return `
        <div class="modal-shell">

            <section class="modal-section">
                <div class="modal-section__heading">
                    <div>
                        <div id="media-mes-chart-title" class="modal-section__title">${METRICAS_DETALHE[0].title}</div>
                        <div id="media-mes-chart-subtitle" class="modal-section__subtitle">${METRICAS_DETALHE[0].subtitle}</div>
                    </div>
                    <span class="modal-badge">${escapeHtml(payload.periodo || '--')} • ${formatMetric(payload.profundidade, 1)} m</span>
                </div>

                <div class="modal-metric-grid">
                    ${renderMetricCards(series, modalState.selectedMetric)}
                </div>

                <div id="media-mes-chart-root" class="modal-chart-wrap">
                    ${renderMetricChart(series, modalState.selectedMetric)}
                </div>
            </section>

            ${renderAlertaSection(regiao, resumo)}
        </div>
    `;
}

function abrirModalMediaMes(regiao) {
    const modal = document.getElementById('media-mes-modal');
    const title = document.getElementById('media-mes-modal-title');
    const subtitle = document.getElementById('media-mes-modal-subtitle');
    const body = document.getElementById('media-mes-modal-body');

    if (!modal || !title || !subtitle || !body || !regiao?.id) {
        return;
    }

    title.innerHTML = `<span class="modal-title-inner"><i data-lucide="calendar-range" style="width: 0.95em; height: 0.95em;"></i><span>Histórico: ${escapeHtml(regiao.pais || 'Recife')}</span></span>`;
    subtitle.textContent = 'Médias consolidadas do mês';
    body.innerHTML = '<div class="modal-loading">Buscando médias mensais...</div>';
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    modal.scrollTop = 0;

    if (window.lucide?.createIcons) {
        lucide.createIcons();
    }

    fetch(`/getMediaDetalhes/?id=${encodeURIComponent(regiao.id)}`)
        .then((response) => {
            if (!response.ok) {
                throw new Error(`Falha ao carregar dados mensais: ${response.status}`);
            }
            return response.json();
        })
        .then((payload) => {
            const series = groupDetalhesPorPeriodo(payload.dados || []);
            const resumo = calcularResumoModal(series);
            const modalState = {
                selectedMetric: 'temperatura',
                series,
                resumo,
                payload
            };

            window.__mediaMesModalState = modalState;
            body.innerHTML = renderResumoModal(payload, regiao, modalState);
            mountMetricSwitcher(modalState);
            mountAlertaForm(regiao, resumo);

            if (window.lucide?.createIcons) {
                lucide.createIcons();
            }
        })
        .catch((err) => {
            console.error('Erro ao carregar dados mensais:', err);
            subtitle.textContent = 'Não foi possível carregar os dados do mês.';
            body.innerHTML = '<div class="modal-loading modal-loading--error">Erro ao carregar dados mensais.</div>';
        });
}

function fecharModalMediaMes() {
    const modal = document.getElementById('media-mes-modal');
    if (!modal) {
        return;
    }

    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
}

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('media-mes-modal');
    if (modal) {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                fecharModalMediaMes();
            }
        });
    }

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            fecharModalMediaMes();
        }
    });
});