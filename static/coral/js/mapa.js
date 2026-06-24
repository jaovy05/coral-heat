let map;
let geojsonGroup;
let telemetryGroup;

document.addEventListener('DOMContentLoaded', () => {
    map = L.map('map-container', {
        zoomControl: false,
        attributionControl: false,
        minZoom: 2,
        maxZoom: 14,
        renderer: L.canvas()
    }).setView([-12.0, -42.0], 4);

    // Ensure the map knows about the fixed header height and resizes correctly
    try {
        const container = map.getContainer();
        // Force the CSS top if variable is present (helps when header CSS loads later)
        if (container && getComputedStyle(document.documentElement).getPropertyValue('--header-height')) {
            container.style.top = getComputedStyle(document.documentElement).getPropertyValue('--header-height').trim() || '64px';
        }
    } catch (e) {
        // non-fatal
        console.warn('Falha ao ajustar estilo do container do mapa:', e);
    }

    // invalidateSize fixes cases where map dimensions change after init (e.g. fixed header)
    map.whenReady(() => {
        setTimeout(() => map.invalidateSize(), 200);
    });

    // Also on window resize (not mobile-focused, just notebook and desktop)
    window.addEventListener('resize', () => {
        setTimeout(() => map.invalidateSize(), 120);
    });

    L.control.scale({
        metric: true,
        imperial: false,
        position: 'bottomleft'
    }).addTo(map);

    L.control.zoom({
        position: 'bottomright'
    }).addTo(map);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    geojsonGroup = L.featureGroup().addTo(map);
    telemetryGroup = L.featureGroup().addTo(map);

    if (typeof HeatmapModule !== 'undefined') {
        HeatmapModule.init(map);
    }

    renderizarRegioes();
    carregarDadosEHeatmap();
});
