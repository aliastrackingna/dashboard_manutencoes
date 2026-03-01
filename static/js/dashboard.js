const graficos = window.graficosData;
const CORES = ['#2563eb','#16a34a','#d97706','#dc2626','#8b5cf6','#06b6d4','#ec4899','#f59e0b','#10b981','#6366f1'];

let isDark = document.documentElement.classList.contains('dark');
let corTexto = isDark ? '#f3f4f6' : '#374151';
let corTextoSecundario = isDark ? '#d1d5db' : '#6b7280';
let corDestaque = isDark ? '#fca5a5' : '#991b1b';

Chart.defaults.color = corTexto;
Chart.defaults.borderColor = isDark ? 'rgba(156, 163, 175, 0.2)' : 'rgba(156, 163, 175, 0.3)';

window.atualizarCoresCharts = function() {
    isDark = document.documentElement.classList.contains('dark');
    corTexto = isDark ? '#f3f4f6' : '#374151';
    corTextoSecundario = isDark ? '#d1d5db' : '#6b7280';
    corDestaque = isDark ? '#fca5a5' : '#991b1b';
    Chart.defaults.color = corTexto;
    Chart.defaults.borderColor = isDark ? 'rgba(156, 163, 175, 0.2)' : 'rgba(156, 163, 175, 0.3)';
    Object.values(Chart.instances).forEach(function(chart) {
        Object.values(chart.options.scales || {}).forEach(function(scale) {
            if (scale.ticks) scale.ticks.color = corTexto;
            if (scale.title) scale.title.color = corTexto;
            if (scale.grid) scale.grid.color = isDark ? 'rgba(156, 163, 175, 0.2)' : 'rgba(156, 163, 175, 0.3)';
        });
        if (chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels) {
            chart.options.plugins.legend.labels.color = corTexto;
        }
        chart.data.datasets.forEach(function(ds) {
            if (ds.backgroundColor && Array.isArray(ds.backgroundColor)) {
                ds.backgroundColor = ds.backgroundColor.map(function(c) {
                    if (c === '#1d4ed8') return isDark ? '#1d4ed8' : '#1d4ed8';
                    if (c === '#60a5fa') return isDark ? '#60a5fa' : '#60a5fa';
                    return c;
                });
            }
        });
        chart.update('none');
    });
};

function drillTo(filtro, valor) {
    const periodo = document.getElementById('periodo-select').value;
    const unidade = document.getElementById('unidade-select').value;
    let url = `/dashboard/lista/?filtro=${filtro}&valor=${encodeURIComponent(valor)}&periodo=${periodo}`;
    if (unidade) url += `&unidade=${encodeURIComponent(unidade)}`;
    window.location.href = url;
}

function datalabelsPlugin(id, {formatFn = v => v} = {}) {
    return {
        id,
        afterDatasetsDraw(chart) {
            const ctx = chart.ctx;
            const isHorizontal = chart.config.options.indexAxis === 'y';
            chart.data.datasets[0].data.forEach((val, i) => {
                const meta = chart.getDatasetMeta(0).data[i];
                ctx.save();
                ctx.fillStyle = corTexto;
                ctx.font = 'bold 13px sans-serif';
                if (isHorizontal) {
                    ctx.textAlign = 'left';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(formatFn(val), meta.x + 6, meta.y);
                } else {
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'bottom';
                    ctx.fillText(formatFn(val), meta.x, meta.y - 4);
                }
                ctx.restore();
            });
        }
    };
}

function formatBRL(v) {
    return 'R$ ' + v.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

function groupedBarLabelsPlugin() {
    return {
        id: 'groupedBarLabels',
        afterDatasetsDraw(chart) {
            const ctx = chart.ctx;
            chart.data.datasets.forEach((dataset, dsIndex) => {
                dataset.data.forEach((val, i) => {
                    if (!val) return;
                    const meta = chart.getDatasetMeta(dsIndex).data[i];
                    ctx.save();
                    ctx.fillStyle = corTexto;
                    ctx.font = 'bold 11px sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'bottom';
                    ctx.fillText(val, meta.x, meta.y - 2);
                    ctx.restore();
                });
            });
        }
    };
}

const evolucaoDatasets = [{
    type: 'bar',
    label: 'Qtd OS',
    data: graficos.evolucao_mensal.data,
    backgroundColor: '#2563eb',
    borderRadius: 4,
    yAxisID: 'y',
    order: 2,
}];
if (graficos.evolucao_mensal.valor_total && graficos.evolucao_mensal.valor_total.some(v => v > 0)) {
    evolucaoDatasets.push({
        type: 'line',
        label: 'Valor (Pecas + Servicos)',
        data: graficos.evolucao_mensal.valor_total,
        borderColor: '#16a34a',
        backgroundColor: 'rgba(22, 163, 74, 0.1)',
        borderWidth: 2,
        pointRadius: 4,
        fill: false,
        tension: 0.3,
        yAxisID: 'y1',
        order: 1,
    });
}
new Chart(document.getElementById('chart-evolucao'), {
    type: 'bar',
    data: {
        labels: graficos.evolucao_mensal.labels,
        datasets: evolucaoDatasets,
    },
    options: {
        responsive: true,
        plugins: {
            legend: { display: evolucaoDatasets.length > 1, position: 'top', labels: { boxWidth: 14, font: { size: 11 } } },
            tooltip: {
                callbacks: {
                    label: function(ctx) {
                        if (ctx.datasetIndex === 1) return ctx.dataset.label + ': ' + formatBRL(ctx.raw);
                        return ctx.dataset.label + ': ' + ctx.raw;
                    }
                }
            },
        },
        scales: {
            y: {
                position: 'left',
                grid: { display: false },
                ticks: { font: { size: 11 } },
                title: { display: true, text: 'Qtd OS', font: { size: 11 } },
                suggestedMax: Math.max(...graficos.evolucao_mensal.data) + 10,
            },
            y1: {
                position: 'right',
                grid: { display: false },
                ticks: { font: { size: 11 }, callback: v => v >= 1000 ? 'R$ ' + (v / 1000).toLocaleString('pt-BR') + 'k' : 'R$ ' + v },
                title: { display: true, text: 'Valor (R$)', font: { size: 11 } },
            },
            x: { ticks: { font: { size: 13 } }, grid: { display: false } },
        },
        onClick: (e, els) => {
            if (els.length > 0) {
                const label = graficos.evolucao_mensal.labels[els[0].index];
                drillTo('mes', label);
            }
        }
    },
    plugins: [datalabelsPlugin('dl-evolucao')]
});

const STATUS_CORES = {
    'Lançada': '#9ca3af',
    'Orçamentação': '#d97706',
    'Análise Solicitante': '#9ca3af',
    'Controladoria': '#9ca3af',
    'Autorizada Execução': '#2563eb',
    'Em Execução': '#2563eb',
    'Executada': '#16a34a',
    'Cancelada pelo Usuário': '#dc2626',
};
const statusLabels = Object.keys(graficos.os_por_status);
const statusData = Object.values(graficos.os_por_status);
const statusColors = statusLabels.map(l => STATUS_CORES[l] || '#9ca3af');

new Chart(document.getElementById('chart-status'), {
    type: 'bar',
    data: {
        labels: statusLabels,
        datasets: [{
            data: statusData,
            backgroundColor: statusColors,
            borderRadius: 4,
        }]
    },
    options: {
        indexAxis: 'y',
        responsive: true,
        plugins: {
            legend: { display: false },
            tooltip: { enabled: true },
        },
        scales: {
            x: { display: false },
            y: { ticks: { font: { size: 13 } } },
        },
        onClick: (e, els) => {
            if (els.length > 0) {
                drillTo('status', statusLabels[els[0].index]);
            }
        }
    },
    plugins: [{
        id: 'datalabels-inline',
        afterDatasetsDraw(chart) {
            const ctx = chart.ctx;
            chart.data.datasets[0].data.forEach((val, i) => {
                const meta = chart.getDatasetMeta(0).data[i];
                ctx.save();
                ctx.fillStyle = corTexto;
                ctx.font = 'bold 13px sans-serif';
                ctx.textAlign = 'left';
                ctx.textBaseline = 'middle';
                ctx.fillText(val, meta.x + 6, meta.y);
                ctx.restore();
            });
        }
    }]
});

const unidadeDatasets = [{
    type: 'bar',
    label: 'Qtd OS',
    data: graficos.os_por_unidade.qtd,
    backgroundColor: '#2563eb',
    borderRadius: 4,
    yAxisID: 'y',
    order: 2,
}];
if (graficos.os_por_unidade.valor && graficos.os_por_unidade.valor.some(v => v > 0)) {
    unidadeDatasets.push({
        type: 'line',
        label: 'Valor Gasto',
        data: graficos.os_por_unidade.valor,
        borderColor: '#16a34a',
        backgroundColor: 'rgba(22, 163, 74, 0.1)',
        borderWidth: 2,
        pointRadius: 4,
        fill: false,
        tension: 0.3,
        yAxisID: 'y1',
        order: 1,
    });
}
new Chart(document.getElementById('chart-unidade'), {
    type: 'bar',
    data: {
        labels: graficos.os_por_unidade.labels,
        datasets: unidadeDatasets,
    },
    options: {
        responsive: true,
        plugins: {
            legend: { display: unidadeDatasets.length > 1, position: 'top', labels: { boxWidth: 14, font: { size: 11 } } },
            tooltip: {
                callbacks: {
                    label: function(ctx) {
                        if (ctx.datasetIndex === 1) return ctx.dataset.label + ': ' + formatBRL(ctx.raw);
                        return ctx.dataset.label + ': ' + ctx.raw;
                    }
                }
            },
        },
        scales: {
            y: {
                position: 'left',
                grid: { display: false },
                ticks: { font: { size: 11 }, stepSize: 1 },
                title: { display: true, text: 'Qtd OS', font: { size: 11 } },
                suggestedMax: Math.max(...graficos.os_por_unidade.qtd) + 1,
            },
            y1: {
                position: 'right',
                grid: { display: false },
                ticks: { font: { size: 11 }, callback: v => v >= 1000 ? 'R$ ' + (v / 1000).toLocaleString('pt-BR') + 'k' : 'R$ ' + v },
                title: { display: true, text: 'Valor (R$)', font: { size: 11 } },
            },
            x: { ticks: { font: { size: 10 }, maxRotation: 90, minRotation: 45 }, grid: { display: false } },
        },
        onClick: (e, els) => {
            if (els.length > 0) {
                const unidade = graficos.os_por_unidade.labels[els[0].index];
                drillTo('unidade', unidade);
            }
        }
    },
    plugins: [datalabelsPlugin('dl-unidade')]
});

function heatColor(val, min, max) {
    const range = max - min || 1;
    const t = (val - min) / range;
    let r, g, b;
    if (t < 0.5) {
        const s = t * 2;
        r = 255; g = Math.round(235 - s * 100); b = Math.round(59 - s * 39);
    } else {
        const s = (t - 0.5) * 2;
        r = Math.round(255 - s * 75); g = Math.round(135 - s * 105); b = Math.round(20 - s * 10);
    }
    return `rgba(${r}, ${g}, ${b}, 0.85)`;
}

const veiculosData = graficos.top_veiculos.map(v => v.total);
const veiculosMin = Math.min(...veiculosData);
const veiculosMax = Math.max(...veiculosData);
const veiculosCores = veiculosData.map(v => heatColor(v, veiculosMin, veiculosMax));

new Chart(document.getElementById('chart-veiculos'), {
    type: 'bar',
    data: {
        labels: graficos.top_veiculos.map(v => v.placa),
        datasets: [{
            data: veiculosData,
            backgroundColor: veiculosCores,
            borderRadius: 4,
        }]
    },
    options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
            y: { display: false },
            x: { ticks: { font: { size: 10 }, maxRotation: 90, minRotation: 45 } },
        },
        onClick: (e, els) => {
            if (els.length > 0) {
                const placa = graficos.top_veiculos[els[0].index].placa;
                window.location.href = `/veiculos/${placa}/`;
            }
        }
    },
    plugins: [{
        id: 'dl-veiculos',
        afterDatasetsDraw(chart) {
            const ctx = chart.ctx;
            chart.data.datasets[0].data.forEach((val, i) => {
                const meta = chart.getDatasetMeta(0).data[i];
                const label = 'R$ ' + Math.round(val).toLocaleString('pt-BR');
                ctx.save();
                ctx.fillStyle = corTexto;
                ctx.font = 'bold 11px sans-serif';
                ctx.textAlign = 'left';
                ctx.textBaseline = 'bottom';
                ctx.translate(meta.x, meta.y - 4);
                ctx.rotate(-Math.PI / 3);
                ctx.fillText(label, 0, 0);
                ctx.restore();
            });
        }
    }]
});

if (graficos.scatter_veiculos && graficos.scatter_veiculos.length > 0) {
    const scatterData = graficos.scatter_veiculos.map(v => ({x: v.qtd_os, y: v.custo_total, placa: v.placa}));
    const maxCusto = Math.max(...scatterData.map(d => d.y));
    const minCusto = Math.min(...scatterData.map(d => d.y));
    const range = maxCusto - minCusto || 1;
    const maxQtd = Math.max(...scatterData.map(d => d.x));
    const iOutlier = scatterData.reduce((max, d, i) => d.y > scatterData[max].y ? i : max, 0);

    function custoToColor(custo) { return heatColor(custo, minCusto, maxCusto).replace('0.85)', '0.65)'); }
    const scatterColors = scatterData.map(d => custoToColor(d.y));

    const radiiLog = scatterData.map(d => {
        const t = (d.y - minCusto) / range;
        return 6 + 34 * Math.log10(1 + t * 9);
    });

    function criarBubbleChart(canvasId, radii, idSuffix) {
        const outlierPlugins = [{
            id: 'outlier-label-' + idSuffix,
            afterDatasetsDraw(chart) {
                const ctx = chart.ctx;
                const point = chart.getDatasetMeta(0).data[iOutlier];
                if (!point) return;
                const d = scatterData[iOutlier];
                const r = radii[iOutlier];
                ctx.save();
                ctx.fillStyle = corDestaque;
                ctx.font = 'bold 11px sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'bottom';
                ctx.fillText(d.placa, point.x, point.y - r - 12);
                ctx.fillStyle = corTextoSecundario;
                ctx.font = '10px sans-serif';
                ctx.fillText(formatBRL(d.y), point.x, point.y - r - 2);
                ctx.restore();
            }
        }, {
            id: 'legend-' + idSuffix,
            afterDraw(chart) {
                const ctx = chart.ctx;
                const area = chart.chartArea;
                const lx = area.right - 110, ly = area.top + 8, lw = 100, lh = 10;
                ctx.save();
                ctx.fillStyle = corTexto === '#f3f4f6' ? 'rgba(31, 41, 55, 0.85)' : 'rgba(255,255,255,0.85)';
                ctx.fillRect(lx - 4, ly - 14, lw + 8, lh + 30);
                ctx.fillStyle = corTextoSecundario;
                ctx.font = '10px sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText('Custo', lx + lw / 2, ly - 2);
                const grad = ctx.createLinearGradient(lx, 0, lx + lw, 0);
                grad.addColorStop(0, custoToColor(minCusto));
                grad.addColorStop(0.5, custoToColor((minCusto + maxCusto) / 2));
                grad.addColorStop(1, custoToColor(maxCusto));
                ctx.fillStyle = grad;
                ctx.fillRect(lx, ly, lw, lh);
                ctx.fillStyle = corTextoSecundario;
                ctx.font = '9px sans-serif';
                ctx.textAlign = 'left';
                ctx.fillText('Menor', lx, ly + lh + 10);
                ctx.textAlign = 'right';
                ctx.fillText('Maior', lx + lw, ly + lh + 10);
                ctx.restore();
            }
        }];

        new Chart(document.getElementById(canvasId), {
            type: 'bubble',
            data: {
                datasets: [{
                    label: 'Veiculos',
                    data: scatterData.map((d, i) => ({x: d.x, y: d.y, r: radii[i], placa: d.placa})),
                    backgroundColor: scatterColors,
                    borderColor: scatterColors.map(c => c.replace('0.65)', '1)')),
                    borderWidth: 1,
                }]
            },
            options: {
                responsive: true,
                onHover: (e, els) => { e.native.target.style.cursor = els.length > 0 ? 'pointer' : 'default'; },
                onClick: (e, els) => {
                    if (els.length > 0) {
                        window.location.href = `/veiculos/${scatterData[els[0].index].placa}/`;
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: ctx => `${ctx.raw.placa}: ${ctx.raw.x} OS, ${formatBRL(ctx.raw.y)} (clique para abrir)` } },
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Qtd OS', font: { size: 12 } },
                        min: 0, max: maxQtd + 1,
                        ticks: { stepSize: 1, font: { size: 11 } },
                        grid: { color: 'rgba(156, 163, 175, 0.15)' },
                    },
                    y: {
                        title: { display: true, text: 'Custo Total (R$)', font: { size: 12 } },
                        ticks: { callback: v => formatBRL(v), font: { size: 11 } },
                        grid: { color: 'rgba(156, 163, 175, 0.15)' },
                    },
                },
            },
            plugins: outlierPlugins,
        });
    }

    criarBubbleChart('chart-scatter', radiiLog, 'log');
}

const setorLabels = Object.keys(graficos.os_por_setor);
const setorData = Object.values(graficos.os_por_setor);

new Chart(document.getElementById('chart-setor'), {
    type: 'bar',
    data: {
        labels: setorLabels,
        datasets: [{
            data: setorData,
            backgroundColor: '#2563eb',
            borderRadius: 4,
        }]
    },
    options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
            y: { display: false },
            x: { ticks: { font: { size: 10 }, maxRotation: 90, minRotation: 45 } },
        },
        onClick: (e, els) => {
            if (els.length > 0) {
                drillTo('setor', setorLabels[els[0].index]);
            }
        }
    },
    plugins: [datalabelsPlugin('dl-setor')]
});

new Chart(document.getElementById('chart-oficinas'), {
    type: 'bar',
    data: {
        labels: graficos.top_oficinas.map(o => o.oficina.split(/\s*[-=]\s*/)[0].trim()),
        datasets: [
            {
                label: 'Aprovados',
                data: graficos.top_oficinas.map(o => o.aprovados),
                backgroundColor: '#1d4ed8',
                borderRadius: 4,
            },
            {
                label: 'Restante',
                data: graficos.top_oficinas.map(o => o.total - o.aprovados),
                backgroundColor: '#60a5fa',
                borderRadius: 4,
            }
        ]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { display: true, position: 'bottom', labels: { color: corTexto } },
            tooltip: {
                callbacks: {
                    afterLabel: function(ctx) {
                        const vm = graficos.top_oficinas[ctx.dataIndex].valor_medio;
                        const apr = graficos.top_oficinas[ctx.dataIndex].aprovados;
                        const total = graficos.top_oficinas[ctx.dataIndex].total;
                        let txt = '';
                        if (vm) txt += 'Valor medio: ' + formatBRL(vm);
                        if (txt) txt += '\n';
                        txt += `Total: ${total} | Aprovados: ${apr}`;
                        return txt;
                    }
                }
            },
        },
        scales: {
            x: { ticks: { font: { size: 10 }, maxRotation: 45, minRotation: 45 } },
            y: { 
                display: true,
                beginAtZero: true,
                suggestedMax: Math.ceil(Math.max(...graficos.top_oficinas.map(o => Math.max(o.aprovados, o.total - o.aprovados))) / 5) * 5 + 5,
                ticks: { 
                    stepSize: 5,
                    color: corTexto,
                    font: { size: 10 }
                },
                grid: {
                    color: isDark ? 'rgba(156, 163, 175, 0.2)' : 'rgba(156, 163, 175, 0.3)'
                }
            },
        },
    },
    plugins: [groupedBarLabelsPlugin()]
});

new Chart(document.getElementById('chart-tipo'), {
    type: 'doughnut',
    data: {
        labels: Object.keys(graficos.dist_tipo).map(k => k === 'PCA' ? 'Peças' : 'Serviços'),
        datasets: [{
            data: Object.values(graficos.dist_tipo),
            backgroundColor: ['#2563eb', '#16a34a'],
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { position: 'right', labels: { boxWidth: 14, font: { size: 13 } } },
            tooltip: {
                callbacks: {
                    label: function(ctx) {
                        const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                        const pct = total > 0 ? Math.round(ctx.raw / total * 100) : 0;
                        return `${ctx.label}: ${formatBRL(ctx.raw)} (${pct}%)`;
                    }
                }
            },
        },
    },
    plugins: [{
        id: 'dl-tipo',
        afterDatasetsDraw(chart) {
            const ctx = chart.ctx;
            const ds = chart.data.datasets[0];
            const total = ds.data.reduce((a, b) => a + b, 0);
            if (total === 0) return;
            ds.data.forEach((val, i) => {
                const meta = chart.getDatasetMeta(0).data[i];
                const pos = meta.tooltipPosition();
                const pct = Math.round(val / total * 100);
                ctx.save();
                ctx.fillStyle = '#fff';
                ctx.font = 'bold 14px sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(`${pct}%`, pos.x, pos.y - 8);
                ctx.font = '12px sans-serif';
                ctx.fillText(formatBRL(val), pos.x, pos.y + 8);
                ctx.restore();
            });
            const {top, bottom, left, right} = chart.chartArea;
            const cx = (left + right) / 2;
            const cy = (top + bottom) / 2;
            ctx.save();
            ctx.fillStyle = corTexto;
            ctx.font = 'bold 15px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(formatBRL(total), cx, cy);
            ctx.restore();
        }
    }]
});

function applyFilters() {
    const periodo = document.getElementById('periodo-select').value;
    const unidade = document.getElementById('unidade-select').value;
    let url = `/dashboard/?periodo=${periodo}`;
    if (unidade) url += `&unidade=${encodeURIComponent(unidade)}`;
    window.location.href = url;
}
document.getElementById('periodo-select').addEventListener('change', applyFilters);
document.getElementById('unidade-select').addEventListener('change', applyFilters);

window.addEventListener('beforeprint', function() {
    const periodoSelect = document.getElementById('periodo-select');
    const periodoTexto = periodoSelect.options[periodoSelect.selectedIndex].text;
    const agora = new Date();
    const dataFormatada = agora.toLocaleDateString('pt-BR') + ' às ' + agora.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'});
    const unidadeSelect = document.getElementById('unidade-select');
    const unidadeTexto = unidadeSelect.options[unidadeSelect.selectedIndex].text;
    document.getElementById('print-meta').textContent = 'Impresso em ' + dataFormatada + '  •  Período: ' + periodoTexto + '  •  Unidade: ' + unidadeTexto;

    const wasDark = isDark;
    if (wasDark) {
        corTexto = '#374151';
        corTextoSecundario = '#6b7280';
        corDestaque = '#991b1b';
        Chart.defaults.color = '#374151';
        Chart.defaults.borderColor = 'rgba(156, 163, 175, 0.3)';
        Object.values(Chart.instances).forEach(function(chart) {
            Object.values(chart.options.scales || {}).forEach(function(scale) {
                if (scale.ticks) scale.ticks.color = '#374151';
                if (scale.title) scale.title.color = '#374151';
            });
            if (chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels) {
                chart.options.plugins.legend.labels.color = '#374151';
            }
            chart.update('none');
        });
    }

    document.querySelectorAll('canvas').forEach(function(canvas) {
        if (canvas.style.display === 'none') return;
        const scale = 2;
        const offscreen = document.createElement('canvas');
        offscreen.width = canvas.width * scale;
        offscreen.height = canvas.height * scale;
        const ctx = offscreen.getContext('2d');
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, offscreen.width, offscreen.height);
        ctx.scale(scale, scale);
        ctx.drawImage(canvas, 0, 0);
        const img = new Image();
        img.src = offscreen.toDataURL('image/png');
        img.style.width = '100%';
        img.classList.add('print-chart-img');
        canvas.parentNode.insertBefore(img, canvas.nextSibling);
        canvas.dataset.printHidden = '1';
    });

    if (wasDark) {
        corTexto = '#f3f4f6';
        corTextoSecundario = '#d1d5db';
        corDestaque = '#fca5a5';
        Chart.defaults.color = '#f3f4f6';
        Chart.defaults.borderColor = 'rgba(156, 163, 175, 0.2)';
        Object.values(Chart.instances).forEach(function(chart) {
            Object.values(chart.options.scales || {}).forEach(function(scale) {
                if (scale.ticks) scale.ticks.color = '#f3f4f6';
                if (scale.title) scale.title.color = '#f3f4f6';
            });
            if (chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels) {
                chart.options.plugins.legend.labels.color = '#f3f4f6';
            }
            chart.update('none');
        });
    }
});

window.addEventListener('afterprint', function() {
    document.querySelectorAll('.print-chart-img').forEach(function(img) { img.remove(); });
    document.querySelectorAll('canvas[data-print-hidden]').forEach(function(canvas) {
        delete canvas.dataset.printHidden;
    });
});
