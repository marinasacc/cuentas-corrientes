/**
 * Cuentas Corrientes - Pantalla de Actualizaciones
 */

let cambios = [];
let filtroActual = '';

// ============================================================
// INICIALIZACION
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
    await cargarActualizaciones();

    // Buscador
    const buscador = document.getElementById('buscador-cambios');
    let timeout;
    buscador.addEventListener('input', (e) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => renderCambios(e.target.value), 300);
    });

    // Filtros
    document.querySelectorAll('.filtro-cambio').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filtro-cambio').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filtroActual = btn.dataset.filtro;
            renderCambios();
        });
    });
});


async function cargarActualizaciones() {
    try {
        const resp = await fetch(`/api/actualizaciones/${CARGA_ID}`);
        const data = await resp.json();

        if (data.carga) {
            const fecha = new Date(data.carga.fecha_carga);
            document.getElementById('info-archivo').textContent = data.carga.nombre_archivo;
            document.getElementById('info-fecha').textContent = fecha.toLocaleDateString('es-AR') + ' ' +
                fecha.toLocaleTimeString('es-AR', {hour: '2-digit', minute: '2-digit'});
        }

        cambios = data.cambios;
        document.getElementById('info-cambios').textContent = cambios.length;

        // Stats
        document.getElementById('stat-pagaron').textContent = cambios.filter(c => c.tipo_cambio === 'pago_total').length;
        document.getElementById('stat-cambio-saldo').textContent = cambios.filter(c => c.tipo_cambio === 'cambio_saldo').length;
        document.getElementById('stat-nuevos').textContent = cambios.filter(c => c.tipo_cambio === 'nuevo').length;

        renderCambios();
    } catch (error) {
        console.error('Error:', error);
    }
}


function renderCambios(busqueda = '') {
    let filtrados = [...cambios];

    // Aplicar filtro de tipo
    if (filtroActual) {
        filtrados = filtrados.filter(c => c.tipo_cambio === filtroActual);
    }

    // Aplicar busqueda
    if (busqueda) {
        const q = busqueda.toLowerCase();
        filtrados = filtrados.filter(c =>
            c.cliente_codigo.toLowerCase().includes(q) ||
            c.nombre.toLowerCase().includes(q)
        );
    }

    const tbody = document.getElementById('tbody-cambios');
    const sinCambios = document.getElementById('sin-cambios');

    if (filtrados.length === 0) {
        tbody.innerHTML = '';
        sinCambios.style.display = 'block';
        return;
    }

    sinCambios.style.display = 'none';

    tbody.innerHTML = filtrados.map(c => {
        const diferencia = c.saldo_total_nuevo - c.saldo_total_anterior;
        const tipoBadge = getTipoBadge(c.tipo_cambio);

        return `
            <tr onclick="window.location='/cliente/${encodeURIComponent(c.cliente_codigo)}'" style="cursor:pointer;">
                <td><span class="badge ${tipoBadge.clase}">${tipoBadge.texto}</span></td>
                <td><code>${escapeHtml(c.cliente_codigo)}</code></td>
                <td class="fw-semibold">${escapeHtml(c.nombre)}</td>
                <td class="text-end moneda">${formatMoney(c.saldo_total_anterior)}</td>
                <td class="text-end moneda fw-bold">${formatMoney(c.saldo_total_nuevo)}</td>
                <td class="text-end moneda fw-bold ${diferencia < 0 ? 'text-success' : diferencia > 0 ? 'text-danger' : ''}">
                    ${diferencia < 0 ? '' : '+'}${formatMoney(diferencia)}
                </td>
            </tr>
        `;
    }).join('');
}


function getTipoBadge(tipo) {
    const tipos = {
        'pago_total': { clase: 'badge-pago-total', texto: 'Pago total' },
        'cambio_saldo': { clase: 'badge-cambio-saldo', texto: 'Cambio saldo' },
        'nuevo': { clase: 'badge-nuevo', texto: 'Nuevo' }
    };
    return tipos[tipo] || { clase: 'bg-secondary', texto: tipo };
}


// ============================================================
// UTILIDADES
// ============================================================

function formatMoney(value) {
    if (value === 0 || value === null || value === undefined) return '$0';
    return '$' + Math.round(value).toLocaleString('es-AR');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
