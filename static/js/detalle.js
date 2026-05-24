/**
 * Cuentas Corrientes - Pantalla Detalle Cliente
 */

let clienteData = null;
let infoApp = null;
let emailsEquipo = [];

// ============================================================
// INICIALIZACION
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
    const respInfo = await fetch('/api/info');
    infoApp = await respInfo.json();

    await cargarCliente();
    await cargarHistorial();
    await cargarEmailsEquipo();

    llenarSelects();
    document.getElementById('contacto-fecha').value = new Date().toISOString().split('T')[0];

    // Enter en el input de nuevo email
    document.getElementById('nuevo-email').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            agregarEmail();
        }
    });
});


async function cargarCliente() {
    try {
        const resp = await fetch(`/api/cliente/${encodeURIComponent(CODIGO_CLIENTE)}`);
        if (!resp.ok) {
            document.body.innerHTML = '<div class="alert alert-danger m-5">Cliente no encontrado</div>';
            return;
        }
        clienteData = await resp.json();
        renderCliente();
    } catch (error) {
        console.error('Error:', error);
    }
}


function renderCliente() {
    document.getElementById('titulo-cliente').innerHTML =
        `<i class="bi bi-person me-2"></i>${escapeHtml(clienteData.nombre)}`;
    document.title = `${clienteData.nombre} - Cuentas Corrientes`;

    document.getElementById('cliente-codigo').textContent = clienteData.codigo;
    document.getElementById('cliente-nombre').textContent = clienteData.nombre;
    document.getElementById('cliente-email').value = clienteData.email || '';
    document.getElementById('cliente-telefono').value = clienteData.telefono || '';
    document.getElementById('cliente-notas').value = clienteData.notas || '';

    document.getElementById('saldo-0-30').textContent = formatMoney(clienteData.saldo_0_30);
    document.getElementById('saldo-31-60').textContent = formatMoney(clienteData.saldo_31_60);
    document.getElementById('saldo-61-90').textContent = formatMoney(clienteData.saldo_61_90);
    document.getElementById('saldo-91-mas').textContent = formatMoney(clienteData.saldo_91_mas);
    document.getElementById('saldo-total').textContent = formatMoney(clienteData.saldo_total);

    const saldoEl = document.getElementById('saldo-total');
    if (clienteData.saldo_total > 0) {
        saldoEl.classList.add('text-danger');
    } else if (clienteData.saldo_total < 0) {
        saldoEl.classList.add('text-success');
    }
}


function llenarSelects() {
    const selectPor = document.getElementById('contacto-por');
    selectPor.innerHTML = '<option value="">Seleccionar...</option>' +
        infoApp.equipo.map(p => `<option value="${p}">${p}</option>`).join('');

    const selectResp = document.getElementById('contacto-respuesta');
    selectResp.innerHTML = '<option value="">Seleccionar...</option>' +
        infoApp.respuestas.map(r => `<option value="${r}">${r}</option>`).join('');
}


// ============================================================
// DATOS DE CONTACTO
// ============================================================

async function guardarContacto() {
    const data = {
        email: document.getElementById('cliente-email').value.trim(),
        telefono: document.getElementById('cliente-telefono').value.trim(),
        notas: document.getElementById('cliente-notas').value.trim()
    };

    try {
        const resp = await fetch(`/api/cliente/${encodeURIComponent(CODIGO_CLIENTE)}/contacto`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });

        if (resp.ok) {
            clienteData.email = data.email;
            clienteData.telefono = data.telefono;
            clienteData.notas = data.notas;
            mostrarToast('Datos guardados correctamente', 'success');
        }
    } catch (error) {
        mostrarToast('Error al guardar', 'danger');
    }
}


// ============================================================
// HISTORIAL DE CONTACTO
// ============================================================

async function cargarHistorial() {
    try {
        const resp = await fetch(`/api/cliente/${encodeURIComponent(CODIGO_CLIENTE)}/historial`);
        const historial = await resp.json();
        renderHistorial(historial);
    } catch (error) {
        console.error('Error:', error);
    }
}


function renderHistorial(historial) {
    const container = document.getElementById('historial-lista');
    const vacio = document.getElementById('historial-vacio');

    if (historial.length === 0) {
        container.innerHTML = '';
        vacio.style.display = 'block';
        return;
    }

    vacio.style.display = 'none';

    container.innerHTML = historial.map(h => {
        const fecha = new Date(h.fecha_contacto);
        const fechaStr = fecha.toLocaleDateString('es-AR', {
            weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
        });

        let proximaStr = '';
        if (h.proxima_fecha && !h.borrado) {
            const proxima = new Date(h.proxima_fecha);
            const hoy = new Date();
            const esVencida = proxima < hoy;
            proximaStr = `
                <span class="badge ${esVencida ? 'bg-danger' : 'bg-info'} ms-2">
                    <i class="bi bi-calendar-event me-1"></i>
                    Prox: ${proxima.toLocaleDateString('es-AR')}
                    ${esVencida ? '(vencido)' : ''}
                </span>
            `;
        }

        const respuestaBadge = getRespuestaBadge(h.respuesta);
        const esBorrado = h.borrado === 1;

        return `
            <div class="contacto-card fade-in ${esBorrado ? 'borrado' : ''}">
                ${esBorrado
                    ? `<span class="badge-borrado"><i class="bi bi-trash-fill me-1"></i>BORRADO</span>`
                    : `<button class="btn-borrar" onclick="borrarContacto(${h.id})" title="Borrar este contacto">
                           <i class="bi bi-trash"></i>
                       </button>`
                }
                <div class="d-flex justify-content-between align-items-start" style="padding-right: 40px;">
                    <div>
                        <span class="fecha">${fechaStr}</span>
                        <span class="persona ms-2">${escapeHtml(h.contactado_por)}</span>
                        ${proximaStr}
                    </div>
                    <span class="badge ${respuestaBadge.clase} respuesta-badge">
                        ${respuestaBadge.icono} ${escapeHtml(h.respuesta)}
                    </span>
                </div>
                ${h.comentario ? `<div class="mt-2 text-muted small comentario"><i class="bi bi-chat-quote me-1"></i>${escapeHtml(h.comentario)}</div>` : ''}
            </div>
        `;
    }).join('');
}


async function borrarContacto(id) {
    if (!confirm('Seguro que queres borrar este registro de contacto?\n\nQuedara marcado como BORRADO pero podras verlo en el historial.')) {
        return;
    }

    try {
        const resp = await fetch(`/api/historial/${id}`, { method: 'DELETE' });
        if (resp.ok) {
            mostrarToast('Contacto marcado como borrado', 'success');
            await cargarHistorial();
        }
    } catch (error) {
        mostrarToast('Error al borrar', 'danger');
    }
}


function getRespuestaBadge(respuesta) {
    const badges = {
        'Va a pagar': { clase: 'bg-success', icono: '<i class="bi bi-check"></i>' },
        'Que vuelva a contactar': { clase: 'bg-warning text-dark', icono: '<i class="bi bi-arrow-repeat"></i>' },
        'Me contacte y no tuve respuesta': { clase: 'bg-secondary', icono: '<i class="bi bi-x"></i>' },
        'Deje mensaje': { clase: 'bg-info', icono: '<i class="bi bi-envelope"></i>' },
        'No me pude contactar': { clase: 'bg-danger', icono: '<i class="bi bi-telephone-x"></i>' },
        'Pago parcial': { clase: 'bg-primary', icono: '<i class="bi bi-cash"></i>' },
        'En disputa': { clase: 'bg-dark', icono: '<i class="bi bi-exclamation-triangle"></i>' },
    };
    return badges[respuesta] || { clase: 'bg-secondary', icono: '' };
}


// ============================================================
// NUEVO CONTACTO
// ============================================================

function abrirModalContacto() {
    document.getElementById('contacto-fecha').value = new Date().toISOString().split('T')[0];
    document.getElementById('contacto-por').value = '';
    document.getElementById('contacto-respuesta').value = '';
    document.getElementById('contacto-comentario').value = '';
    document.getElementById('contacto-proxima').value = '';
    new bootstrap.Modal(document.getElementById('modalContacto')).show();
}


async function guardarNuevoContacto() {
    const fecha = document.getElementById('contacto-fecha').value;
    const por = document.getElementById('contacto-por').value;
    const respuesta = document.getElementById('contacto-respuesta').value;
    const comentario = document.getElementById('contacto-comentario').value;
    const proxima = document.getElementById('contacto-proxima').value;

    if (!fecha || !por || !respuesta) {
        mostrarToast('Completa fecha, quien contacto y respuesta', 'warning');
        return;
    }

    const data = {
        fecha_contacto: fecha,
        contactado_por: por,
        respuesta: respuesta,
        comentario: comentario,
        proxima_fecha: proxima
    };

    try {
        const resp = await fetch(`/api/cliente/${encodeURIComponent(CODIGO_CLIENTE)}/historial`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });

        if (resp.ok) {
            bootstrap.Modal.getInstance(document.getElementById('modalContacto')).hide();
            mostrarToast('Contacto registrado', 'success');
            await cargarHistorial();
        }
    } catch (error) {
        mostrarToast('Error al guardar el contacto', 'danger');
    }
}


// ============================================================
// EMAILS DEL EQUIPO
// ============================================================

async function cargarEmailsEquipo() {
    try {
        const resp = await fetch('/api/emails-equipo');
        emailsEquipo = await resp.json();
    } catch (error) {
        console.error('Error:', error);
    }
}


function renderEmailsRecordatorio() {
    const container = document.getElementById('recordatorio-emails');

    let html = '';

    // Email del cliente (si tiene)
    if (clienteData.email) {
        html += `
            <div class="email-item">
                <input class="form-check-input email-check me-2" type="checkbox" value="${clienteData.email}" id="email-cliente">
                <label class="form-check-label flex-grow-1" for="email-cliente">
                    <i class="bi bi-person-circle text-primary me-1"></i>
                    ${escapeHtml(clienteData.email)}
                    <span class="badge bg-light text-dark ms-1">cliente</span>
                </label>
            </div>
        `;
    }

    // Emails del equipo (todos marcados por defecto)
    emailsEquipo.forEach((e, idx) => {
        html += `
            <div class="email-item">
                <input class="form-check-input email-check me-2" type="checkbox" value="${e.email}" id="email-eq-${e.id}" checked>
                <label class="form-check-label flex-grow-1" for="email-eq-${e.id}">
                    <i class="bi bi-person-fill text-success me-1"></i>
                    ${escapeHtml(e.email)}
                </label>
                <button class="btn-eliminar-email" onclick="eliminarEmailEquipo(${e.id})" title="Quitar de la lista">
                    <i class="bi bi-x-lg"></i>
                </button>
            </div>
        `;
    });

    container.innerHTML = html;
}


async function agregarEmail() {
    const input = document.getElementById('nuevo-email');
    const email = input.value.trim();

    if (!email || !email.includes('@')) {
        mostrarToast('Email invalido', 'warning');
        return;
    }

    try {
        const resp = await fetch('/api/emails-equipo', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ email })
        });

        if (resp.ok) {
            input.value = '';
            await cargarEmailsEquipo();
            renderEmailsRecordatorio();
            mostrarToast('Email agregado a la lista', 'success');
        }
    } catch (error) {
        mostrarToast('Error al agregar email', 'danger');
    }
}


async function eliminarEmailEquipo(id) {
    if (!confirm('Quitar este email de la lista del equipo?')) return;

    try {
        const resp = await fetch(`/api/emails-equipo/${id}`, { method: 'DELETE' });
        if (resp.ok) {
            await cargarEmailsEquipo();
            renderEmailsRecordatorio();
        }
    } catch (error) {
        mostrarToast('Error', 'danger');
    }
}


// ============================================================
// RECORDATORIO (envio automatico)
// ============================================================

function abrirModalRecordatorio() {
    if (!infoApp.smtp_configurado) {
        mostrarToast('Falta configurar SMTP. Edita el archivo smtp_config.json con tu app password de Gmail.', 'warning');
        return;
    }

    document.getElementById('recordatorio-titulo').value =
        `Contactar: ${clienteData.nombre} (${clienteData.codigo})`;
    document.getElementById('recordatorio-descripcion').value =
        `Saldo total: ${formatMoney(clienteData.saldo_total)}`;
    document.getElementById('recordatorio-fecha').value = '';

    renderEmailsRecordatorio();
    new bootstrap.Modal(document.getElementById('modalRecordatorio')).show();
}


async function enviarRecordatorio() {
    const titulo = document.getElementById('recordatorio-titulo').value.trim();
    const descripcion = document.getElementById('recordatorio-descripcion').value.trim();
    const fecha = document.getElementById('recordatorio-fecha').value;

    if (!titulo || !fecha) {
        mostrarToast('Completa titulo y fecha', 'warning');
        return;
    }

    const emailsSeleccionados = [];
    document.querySelectorAll('.email-check:checked').forEach(el => {
        emailsSeleccionados.push(el.value);
    });

    if (emailsSeleccionados.length === 0) {
        mostrarToast('Selecciona al menos un email', 'warning');
        return;
    }

    const data = {
        titulo,
        descripcion,
        fecha,
        emails: emailsSeleccionados
    };

    const btn = document.querySelector('#modalRecordatorio .btn-warning');
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando...';

    try {
        const resp = await fetch('/api/enviar-recordatorio', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });

        const result = await resp.json();

        if (resp.ok && result.ok) {
            bootstrap.Modal.getInstance(document.getElementById('modalRecordatorio')).hide();
            mostrarToast(`Invitacion enviada a ${emailsSeleccionados.length} destinatarios`, 'success');
        } else {
            mostrarToast(result.error || 'Error al enviar', 'danger');
        }
    } catch (error) {
        mostrarToast('Error de conexion al enviar', 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
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

function mostrarToast(mensaje, tipo) {
    const toastContainer = document.getElementById('toast-container') || crearToastContainer();
    const toast = document.createElement('div');
    toast.className = `alert alert-${tipo} alert-dismissible fade show`;
    toast.innerHTML = `${mensaje}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function crearToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = 'position:fixed;top:70px;right:20px;z-index:9999;max-width:350px;';
    document.body.appendChild(container);
    return container;
}
