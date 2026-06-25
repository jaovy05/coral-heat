function getCsrfToken() {
    if (window.__CSRF_TOKEN__) {
        return window.__CSRF_TOKEN__;
    }
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
}

async function alertasFetch(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
        ...(options.headers || {}),
    };
    const response = await fetch(url, { ...options, headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.error || `Erro ${response.status}`);
    }
    return data;
}

const AlertasApi = {
    list() {
        return alertasFetch('/alertas/api/');
    },
    create(payload) {
        return alertasFetch('/alertas/api/', { method: 'POST', body: JSON.stringify(payload) });
    },
    update(id, payload) {
        return alertasFetch(`/alertas/api/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) });
    },
    remove(id) {
        return alertasFetch(`/alertas/api/${id}/`, { method: 'DELETE' });
    },
    regioes() {
        return alertasFetch('/alertas/api/regioes/');
    },
};

function escapeAlertHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
    })[char]);
}

function renderAlertaItem(alerta, regioes) {
    const regiaoOptions = regioes.map((nome) => `
        <option value="${escapeAlertHtml(nome)}" ${nome === alerta.region_name ? 'selected' : ''}>
            ${escapeAlertHtml(nome)}
        </option>
    `).join('');

    return `
        <article class="alerta-item" data-id="${alerta.id}">
            <div class="alerta-item__view">
                <div class="alerta-item__main">
                    <strong class="alerta-item__region">${escapeAlertHtml(alerta.region_name)}</strong>
                    <span class="alerta-item__temp">≥ ${Number(alerta.target_temp).toFixed(1)} °C</span>
                </div>
                <div class="alerta-item__meta">
                    <span class="alerta-badge ${alerta.active ? 'alerta-badge--on' : 'alerta-badge--off'}">
                        ${alerta.active ? 'Ativo' : 'Inativo'}
                    </span>
                    <span class="alerta-badge ${alerta.repeat ? '' : 'alerta-badge--once'}">
                        ${alerta.repeat ? 'Repetir' : 'Uma vez'}
                    </span>
                    <span class="alerta-item__date">${escapeAlertHtml(alerta.criado_em)}</span>
                </div>
                <div class="alerta-item__actions">
                    <button type="button" class="alerta-btn alerta-btn--ghost" data-action="edit">Editar</button>
                    <button type="button" class="alerta-btn alerta-btn--danger" data-action="delete">Excluir</button>
                </div>
            </div>
            <form class="alerta-item__edit" hidden>
                <label class="alerta-field">
                    <span>Região</span>
                    <select name="region_name" required>${regiaoOptions}</select>
                </label>
                <label class="alerta-field">
                    <span>Temperatura limite (°C)</span>
                    <input type="number" name="target_temp" step="0.1" min="0" max="45" value="${Number(alerta.target_temp)}" required>
                </label>
                <label class="alerta-check">
                    <input type="checkbox" name="repeat" ${alerta.repeat ? 'checked' : ''}>
                    <span>Repetir alerta por e-mail</span>
                </label>
                <label class="alerta-check">
                    <input type="checkbox" name="active" ${alerta.active ? 'checked' : ''}>
                    <span>Alerta ativo</span>
                </label>
                <div class="alerta-item__actions">
                    <button type="submit" class="alerta-btn alerta-btn--primary">Salvar</button>
                    <button type="button" class="alerta-btn alerta-btn--ghost" data-action="cancel">Cancelar</button>
                </div>
            </form>
        </article>
    `;
}

function renderAlertasList(alertas, regioes) {
    if (!alertas.length) {
        return '<p class="alertas-empty">Nenhum alerta cadastrado. Crie um abaixo ou pelo mapa.</p>';
    }
    return alertas.map((alerta) => renderAlertaItem(alerta, regioes)).join('');
}

function renderRegiaoOptions(regioes, selected = '') {
    if (!regioes.length) {
        return '<option value="">Sem regiões disponíveis</option>';
    }
    return regioes.map((nome) => `
        <option value="${escapeAlertHtml(nome)}" ${nome === selected ? 'selected' : ''}>
            ${escapeAlertHtml(nome)}
        </option>
    `).join('');
}

function setAlertasFeedback(message, isError = false) {
    const el = document.getElementById('alertas-feedback');
    if (!el) {
        return;
    }
    el.textContent = message || '';
    el.classList.toggle('alertas-feedback--error', Boolean(isError));
    el.hidden = !message;
}

async function loadAlertasPanel(prefill = {}) {
    const listRoot = document.getElementById('alertas-list');
    if (!listRoot) {
        return;
    }

    listRoot.innerHTML = '<p class="alertas-loading">Carregando alertas...</p>';
    setAlertasFeedback('');

    try {
        const [alertasData, regioesData] = await Promise.all([
            AlertasApi.list(),
            AlertasApi.regioes(),
        ]);
        const regioes = regioesData.regioes || [];
        const alertas = alertasData.alertas || [];

        listRoot.innerHTML = renderAlertasList(alertas, regioes);

        const form = document.getElementById('alerta-create-form');
        const regionSelect = form?.querySelector('[name="region_name"]');
        if (regionSelect) {
            regionSelect.innerHTML = renderRegiaoOptions(regioes, prefill.region_name || '');
        }
        if (prefill.target_temp && form) {
            form.querySelector('[name="target_temp"]').value = Number(prefill.target_temp).toFixed(1);
        }

        bindAlertasListEvents(regioes);
    } catch (err) {
        listRoot.innerHTML = '<p class="alertas-empty alertas-feedback--error">Não foi possível carregar os alertas.</p>';
        setAlertasFeedback(err.message, true);
    }
}

function bindAlertasListEvents(regioes) {
    const listRoot = document.getElementById('alertas-list');
    if (!listRoot) {
        return;
    }

    listRoot.querySelectorAll('.alerta-item').forEach((item) => {
        const id = Number(item.dataset.id);
        const view = item.querySelector('.alerta-item__view');
        const form = item.querySelector('.alerta-item__edit');

        item.querySelector('[data-action="edit"]')?.addEventListener('click', () => {
            view.hidden = true;
            form.hidden = false;
        });

        item.querySelector('[data-action="cancel"]')?.addEventListener('click', () => {
            form.hidden = true;
            view.hidden = false;
        });

        item.querySelector('[data-action="delete"]')?.addEventListener('click', async () => {
            if (!confirm('Excluir este alerta?')) {
                return;
            }
            try {
                await AlertasApi.remove(id);
                setAlertasFeedback('Alerta excluído.');
                await loadAlertasPanel();
            } catch (err) {
                setAlertasFeedback(err.message, true);
            }
        });

        form?.addEventListener('submit', async (event) => {
            event.preventDefault();
            const payload = {
                region_name: form.region_name.value,
                target_temp: parseFloat(form.target_temp.value),
                repeat: form.repeat.checked,
                active: form.active.checked,
            };
            try {
                await AlertasApi.update(id, payload);
                setAlertasFeedback('Alerta atualizado.');
                await loadAlertasPanel();
            } catch (err) {
                setAlertasFeedback(err.message, true);
            }
        });
    });
}

function abrirPainelAlertas(prefill = {}) {
    const panel = document.getElementById('alertas-panel');
    if (!panel) {
        window.location.href = '/login/?next=' + encodeURIComponent(window.location.pathname);
        return;
    }

    panel.classList.add('is-open');
    panel.setAttribute('aria-hidden', 'false');
    document.getElementById('userDropdown')?.classList.remove('show');
    loadAlertasPanel(prefill);

    if (window.lucide?.createIcons) {
        lucide.createIcons();
    }
}

function fecharPainelAlertas() {
    const panel = document.getElementById('alertas-panel');
    if (!panel) {
        return;
    }
    panel.classList.remove('is-open');
    panel.setAttribute('aria-hidden', 'true');
    setAlertasFeedback('');
}

async function criarAlerta(payload) {
    return AlertasApi.create(payload);
}

window.abrirPainelAlertas = abrirPainelAlertas;
window.fecharPainelAlertas = fecharPainelAlertas;
window.criarAlerta = criarAlerta;

document.addEventListener('DOMContentLoaded', () => {
    const panel = document.getElementById('alertas-panel');
    const openBtn = document.getElementById('alertasMenuBtn');
    const createForm = document.getElementById('alerta-create-form');

    openBtn?.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        abrirPainelAlertas();
    });

    panel?.addEventListener('click', (event) => {
        if (event.target === panel) {
            fecharPainelAlertas();
        }
    });

    createForm?.addEventListener('submit', async (event) => {
        event.preventDefault();
        const payload = {
            region_name: createForm.region_name.value,
            target_temp: parseFloat(createForm.target_temp.value),
            repeat: createForm.repeat.checked,
            active: createForm.active.checked,
        };
        try {
            await AlertasApi.create(payload);
            setAlertasFeedback('Alerta criado com sucesso.');
            createForm.reset();
            createForm.active.checked = true;
            createForm.repeat.checked = true;
            await loadAlertasPanel();
        } catch (err) {
            setAlertasFeedback(err.message, true);
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && panel?.classList.contains('is-open')) {
            fecharPainelAlertas();
        }
    });
});
