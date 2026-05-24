/**
 * Cuentas Corrientes - Pantalla Principal
 */

let clientes = [];
let filtroActual = '';
let filtroContacto = '';  // '', 'si', 'no'
let busquedaActual = '';
let sortColumn = 'saldo_total';
let sortDirection = 'desc';

// ============================================================
// INICIALIZACION
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
    await verificarEstado();

    // Buscador con debounce
    const buscador = document.getElementById('buscador');
    let timeout;
    buscador.addEventListener('input', (e) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            busquedaActual = e.target.value;
            cargarClientes();
        }, 300);
    });

    // Filtros de antiguedad
    document.querySelectorAll('.filtro-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filtro-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filtroActual = btn.dataset.filtro;
            cargarClientes();
        });
    });

    // Ordenamiento de columnas
    document.querySelectorAll('.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const col = th.dataset.sort;
            if (sortColumn === col) {
                sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                sortColumn = col;
                sortDirection = col === 'nombre' || col === 'codigo' ? 'asc' : 'desc';
            }
            renderClientes();
        });
    });
});


async function verificarEstado() {
    try {
        const resp = await fetch('/api/info');
        const info = await resp.json();

        if (!info.ultima_carga) {
            document.getElementById('pantalla-primera-carga').style.display = 'block';
            document.getElementById('pantalla-principal').style.display = 'none';
            document.getElementById('fab-container').style.display = 'none';
        } else {
            document.getElementById('pantalla-primera-carga').style.display = 'none';
            document.getElementById('pantalla-principal').style.display = 'block';
            document.getElementById('fab-container').style.display = 'block';

            const fecha = new Date(info.ultima_carga.fecha_carga);
            document.getElementById('info-carga').innerHTML =
                `<i class="bi bi-calendar-check me-1"></i>Ultima carga: ${fecha.toLocaleDateString('es-AR')} ${fecha.toLocaleTimeString('es-AR', {hour: '2-digit', minute: '2-digit'})} | ${info.total_clientes} clientes`;

            await cargarClientes();
            await actualizarInfoBackup();
        }
    } catch (error) {
        console.error('Error:', error);
    }
}


async function actualizarInfoBackup() {
    try {
        const resp = await fetch('/api/backup-status');
        const data = await resp.json();

        const el = document.getElementById('info-backup');
        if (!data.last_backup) {
            el.innerHTML = `<i class="bi bi-cloud-slash me-1"></i>Sin backup aun`;
            return;
        }

        const fecha = new Date(data.last_backup);
        const ahora = new Date();
        const diffHs = Math.floor((ahora - fecha) / (1000 * 60 * 60));

        let texto, color;
        if (diffHs < 1) {
            texto = 'hace minutos';
            color = '#86efac';
        } else if (diffHs < 24) {
            texto = `hace ${diffHs}h`;
            color = '#86efac';
        } else {
            const dias = Math.floor(diffHs / 24);
            texto = `hace ${dias}d`;
            color = dias > 3 ? '#fca5a5' : '#fde68a';
        }

        const icono = data.last_status === 'error' ? 'cloud-slash' : 'cloud-check';
        el.innerHTML = `<i class="bi bi-${icono} me-1"></i><span style="color:${color}">Backup ${texto}</span>`;
    } catch (e) {
        console.error('Error backup status:', e);
    }
}


async function hacerBackupManual() {
    const btn = document.getElementById('btn-backup');
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

    try {
        const resp = await fetch('/api/backup-manual', { method: 'POST' });
        const data = await resp.json();

        if (resp.ok) {
            alert('Backup iniciado en segundo plano. Tarda unos segundos. Recargar la pagina en un momento para ver el estado.');
            setTimeout(actualizarInfoBackup, 10000);  // Actualizar despues de 10s
        } else {
            alert('Error: ' + (data.error || 'desconocido'));
        }
    } catch (error) {
        alert('Error de conexion: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
}


// ============================================================
// FILTROS POR CONTACTO (clic en stat cards)
// ============================================================

function filtrarPorContacto(tipo) {
    // Si ya esta activo, desactivar
    if (filtroContacto === tipo) {
        limpiarFiltroContacto();
        return;
    }

    filtroContacto = tipo;

    // Actualizar UI
    document.getElementById('card-contactados').classList.remove('active');
    document.getElementById('card-sin-contactar').classList.remove('active');

    const badge = document.getElementById('badge-filtro-contacto');
    const texto = document.getElementById('texto-filtro-contacto');

    if (tipo === 'si') {
        document.getElementById('card-contactados').classList.add('active');
        texto.textContent = 'Mostrando: Contactados';
    } else if (tipo === 'no') {
        document.getElementById('card-sin-contactar').classList.add('active');
        texto.textContent = 'Mostrando: Sin contactar';
    }

    badge.style.display = 'inline-block';
    cargarClientes();
}


function limpiarFiltroContacto() {
    filtroContacto = '';
    document.getElementById('card-contactados').classList.remove('active');
    document.getElementById('card-sin-contactar').classList.remove('active');
    document.getElementById('badge-filtro-contacto').style.display = 'none';
    cargarClientes();
}


// ============================================================
// CARGA Y RENDERIZADO DE CLIENTES
// ============================================================

async function cargarClientes() {
    try {
        const params = new URLSearchParams();
        if (filtroActual) params.set('filtro', filtroActual);
        if (busquedaActual) params.set('busqueda', busquedaActual);
        if (filtroContacto) params.set('contacto', filtroContacto);

        const resp = await fetch(`/api/clientes?${params}`);
        clientes = await resp.json();
        renderClientes();
    } catch (error) {
        console.error('Error cargando clientes:', error);
    }
}


function renderClientes() {
    const sorted = [...clientes].sort((a, b) => {
        let valA = a[sortColumn];
        let valB = b[sortColumn];

        if (valA === null || valA === undefined) valA = '';
        if (valB === null || valB === undefined) valB = '';

        if (typeof valA === 'string') {
            valA = valA.toLowerCase();
            valB = (valB || '').toString().toLowerCase();
        }

        if (sortDirection === 'asc') {
            return valA > valB ? 1 : valA < valB ? -1 : 0;
        } else {
            return valA < valB ? 1 : valA > valB ? -1 : 0;
        }
    });

    const tbody = document.getElementById('tbody-clientes');
    const sinResultados = document.getElementById('sin-resultados');

    if (sorted.length === 0) {
        tbody.innerHTML = '';
        sinResultados.style.display = 'block';
    } else {
        sinResultados.style.display = 'none';

        tbody.innerHTML = sorted.map(c => `
            <tr onclick="window.location='/cliente/${encodeURIComponent(c.codigo)}'">
                <td class="text-center">
                    <span class="contactado-check ${c.contactado ? 'si' : 'no'}">
                        <i class="bi bi-${c.contactado ? 'check-circle-fill' : 'circle'}"></i>
                    </span>
                </td>
                <td><code>${escapeHtml(c.codigo)}</code></td>
                <td class="fw-semibold">${escapeHtml(c.nombre)}</td>
                <td class="small text-muted">${formatFecha(c.fecha_ultimo_movimiento)}</td>
                <td class="text-end moneda">${formatMoney(c.saldo_0_30)}</td>
                <td class="text-end moneda">${formatMoney(c.saldo_31_60)}</td>
                <td class="text-end moneda">${formatMoney(c.saldo_61_90)}</td>
                <td class="text-end moneda">${formatMoney(c.saldo_91_mas)}</td>
                <td class="text-end moneda fw-bold ${c.saldo_total > 0 ? 'saldo-positivo' : c.saldo_total < 0 ? 'saldo-negativo' : 'saldo-cero'}">${formatMoney(c.saldo_total)}</td>
            </tr>
        `).join('');
    }

    // Actualizar stats (usando todos los clientes, no solo los filtrados)
    actualizarStats();
}


async function actualizarStats() {
    // Obtener todos los clientes sin filtro para los stats globales
    try {
        const resp = await fetch('/api/clientes');
        const todos = await resp.json();

        const totalClientes = todos.length;
        const saldoTotal = todos.reduce((sum, c) => sum + (c.saldo_total > 0 ? c.saldo_total : 0), 0);
        const contactados = todos.filter(c => c.contactado).length;
        const sinContactar = totalClientes - contactados;

        document.getElementById('stat-total').textContent = totalClientes;
        document.getElementById('stat-saldo').textContent = formatMoney(saldoTotal);
        document.getElementById('stat-contactados').textContent = contactados;
        document.getElementById('stat-sin-contactar').textContent = sinContactar;
    } catch (e) {
        console.error('Error stats:', e);
    }
}


// ============================================================
// CARGA DE EXCEL
// ============================================================

function abrirModalCarga() {
    document.getElementById('input-excel').value = '';
    document.getElementById('carga-progress').style.display = 'none';
    document.getElementById('carga-error').style.display = 'none';
    document.getElementById('btn-cargar').disabled = false;
    new bootstrap.Modal(document.getElementById('modalCarga')).show();
}


async function cargarExcel() {
    const input = document.getElementById('input-excel');
    if (!input.files.length) {
        document.getElementById('carga-error').textContent = 'Selecciona un archivo primero.';
        document.getElementById('carga-error').style.display = 'block';
        return;
    }

    const formData = new FormData();
    formData.append('archivo', input.files[0]);

    document.getElementById('carga-progress').style.display = 'block';
    document.getElementById('carga-error').style.display = 'none';
    document.getElementById('btn-cargar').disabled = true;

    try {
        const resp = await fetch('/api/cargar-excel', {
            method: 'POST',
            body: formData
        });

        const data = await resp.json();

        if (!resp.ok) {
            throw new Error(data.error || 'Error al cargar el archivo');
        }

        bootstrap.Modal.getInstance(document.getElementById('modalCarga')).hide();
        mostrarResultado(data);
        await verificarEstado();

    } catch (error) {
        document.getElementById('carga-error').textContent = error.message;
        document.getElementById('carga-error').style.display = 'block';
        document.getElementById('carga-progress').style.display = 'none';
        document.getElementById('btn-cargar').disabled = false;
    }
}


function mostrarResultado(data) {
    const body = document.getElementById('resultado-body');
    const btnCambios = document.getElementById('btn-ver-cambios');

    if (data.es_primera_carga) {
        body.innerHTML = `
            <div class="text-center">
                <i class="bi bi-check-circle text-success display-4"></i>
                <h5 class="mt-3">Carga inicial completada</h5>
                <p class="text-muted">Se cargaron <strong>${data.total_clientes}</strong> clientes correctamente.</p>
            </div>
        `;
        btnCambios.style.display = 'none';
    } else {
        body.innerHTML = `
            <div class="text-center">
                <i class="bi bi-arrow-repeat text-info display-4"></i>
                <h5 class="mt-3">Actualizacion completada</h5>
                <p>Se procesaron <strong>${data.total_clientes}</strong> clientes.</p>
                <p>Se detectaron <strong class="text-primary">${data.total_cambios}</strong> cambios.</p>
            </div>
        `;
        if (data.total_cambios > 0) {
            btnCambios.style.display = 'inline-block';
            btnCambios.href = `/actualizaciones/${data.carga_id}`;
        } else {
            btnCambios.style.display = 'none';
        }
    }

    new bootstrap.Modal(document.getElementById('modalResultado')).show();
}


// ============================================================
// EXPORTAR
// ============================================================

function exportarExcel() {
    window.location = '/api/exportar';
}


// ============================================================
// HISTORIAL DE CARGAS
// ============================================================

async function verHistorialCargas() {
    try {
        const resp = await fetch('/api/historial-cargas');
        const cargas = await resp.json();

        const tbody = document.getElementById('tbody-historial-cargas');
        tbody.innerHTML = cargas.map(c => {
            const fecha = new Date(c.fecha_carga);
            return `
                <tr>
                    <td>${fecha.toLocaleDateString('es-AR')} ${fecha.toLocaleTimeString('es-AR', {hour: '2-digit', minute: '2-digit'})}</td>
                    <td>${escapeHtml(c.nombre_archivo)}</td>
                    <td>${c.cantidad_clientes}</td>
                    <td>
                        <a href="/actualizaciones/${c.id}" class="btn btn-sm btn-outline-primary">
                            <i class="bi bi-eye"></i> Ver
                        </a>
                    </td>
                </tr>
            `;
        }).join('');

        new bootstrap.Modal(document.getElementById('modalHistorialCargas')).show();
    } catch (error) {
        console.error('Error:', error);
    }
}


// ============================================================
// UTILIDADES
// ============================================================

function formatMoney(value) {
    if (value === 0 || value === null || value === undefined) return '$0';
    return '$' + Math.round(value).toLocaleString('es-AR');
}

function formatFecha(fechaStr) {
    if (!fechaStr) return '-';
    try {
        const f = new Date(fechaStr.replace(' ', 'T'));
        return f.toLocaleDateString('es-AR');
    } catch {
        return '-';
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
