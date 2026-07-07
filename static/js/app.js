if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/sw.js');
}
const API = window.location.origin;
let fotoFile = null;
let faceFile = null;
let lastView = [];

function $(id) { return document.getElementById(id) }

function toast(msg) {
  const t = document.createElement('div'); t.className = 'toast'; t.textContent = msg;
  document.body.appendChild(t); setTimeout(() => t.remove(), 3000)
}

async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body instanceof FormData) { opts.body = body } else if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body) }
  const r = await fetch(API + path, opts);
  if (!r.ok) { const e = await r.text(); throw new Error(e || `HTTP ${r.status}`) }
  return r.status === 204 ? null : r.json()
}

function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.add('hide'));
  document.getElementById('page-' + name).classList.remove('hide');
  document.querySelectorAll('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.page === name));
  lastView = [name];
  if (name === 'home') cargarHome()
}

function previewFoto(e) {
  const f = e.target.files[0]; if (!f) return;
  fotoFile = f; const r = new FileReader();
  r.onload = function () { const img = $('camera-preview'); img.src = r.result; img.classList.remove('hide'); $('camera-placeholder').classList.add('hide') };
  r.readAsDataURL(f)
}

function previewFace(e) {
  const f = e.target.files[0]; if (!f) return;
  faceFile = f; const r = new FileReader();
  r.onload = function () { const img = $('face-preview'); img.src = r.result; img.classList.remove('hide'); $('face-placeholder').classList.add('hide') };
  r.readAsDataURL(f)
}

function latLngToUtm(lat, lng) {
  const a = 6378137, f = 1 / 298.257223563, k0 = 0.9996;
  const zone = Math.floor((lng + 180) / 6) + 1;
  const cm = (zone - 1) * 6 - 180 + 3;
  const latRad = lat * Math.PI / 180, cmRad = cm * Math.PI / 180;
  const e = Math.sqrt(2 * f - f * f), n = f / (2 - f), n2 = n * n, n3 = n2 * n;
  const sinLat = Math.sin(latRad), cosLat = Math.cos(latRad), tanLat = Math.sin(latRad) / Math.cos(latRad);
  const t = tanLat * tanLat, c = e * e * cosLat * cosLat / (1 - e * e);
  const A = cosLat * (lng - cm) * Math.PI / 180;
  const M = a * ((1 - e * e / 4 - 3 * e * e * e * e / 64 - 5 * e * e * e * e * e * e / 256) * latRad
    - (3 * e * e / 8 + 3 * e * e * e * e / 32 + 45 * e * e * e * e * e * e / 1024) * Math.sin(2 * latRad)
    + (15 * e * e * e * e / 256 + 45 * e * e * e * e * e * e / 1024) * Math.sin(4 * latRad)
    - (35 * e * e * e * e * e * e / 3072) * Math.sin(6 * latRad));
  const easting = k0 * A * (1 + A * A * ((1 - t + c) / 6 + A * A * (5 - 18 * t + t * t + 72 * c - 58 * e * e) / 120)) + 500000;
  const northing = k0 * (M + a * Math.pow(cosLat, 2) * tanLat * (A * A / 2 + A * A * A * A * (5 - t + 9 * c + 4 * c * c) / 120));
  return { este: Math.round(easting * 100) / 100, norte: Math.round(northing * 100) / 100, zona: zone }
}

function getGPS() {
  if (!navigator.geolocation) { toast('GPS no disponible'); return }
  $('reg-ubicacion').placeholder = 'Obteniendo ubicación...';
  navigator.geolocation.getCurrentPosition(
    p => {
      const u = latLngToUtm(p.coords.latitude, p.coords.longitude);
      $('reg-utmeste').value = u.este;
      $('reg-utmnorte').value = u.norte;
      $('reg-zona').value = u.zona;
      $('reg-hemisferio').value = p.coords.latitude >= 0 ? 'N' : 'S';
      $('reg-ubicacion').placeholder = 'Ubicación actual';
      toast('UTM: ' + u.zona + ' ' + u.este + ' ' + u.norte)
    },
    e => { toast('Error GPS: ' + e.message); $('reg-ubicacion').placeholder = 'Ingrese ubicación manualmente' },
    { enableHighAccuracy: true, timeout: 10000 }
  )
}

async function registrar() {
  const campos = ['cedula', 'nombre', 'apellido', 'salud', 'ubicacion', 'utmeste', 'utmnorte', 'zona', 'hemisferio', 'obs', 'por'];
  const v = {};
  campos.forEach(c => { v[c] = $('reg-' + c)?.value?.trim() || '' });
  const fecnac = $('reg-fecnac').value;
  if (!v.nombre || !v.apellido) { toast('Nombre y apellido son obligatorios'); return }

  const fd = new FormData();
  fd.append('cedula', v.cedula);
  fd.append('nombre', v.nombre);
  fd.append('apellido', v.apellido);
  if (fecnac) fd.append('fecha_nacimiento', fecnac);
  fd.append('estado_salud', v.salud);
  fd.append('ubicacion_actual', v.ubicacion);
  if (v.utmeste) fd.append('utm_este', v.utmeste);
  if (v.utmnorte) fd.append('utm_norte', v.utmnorte);
  if (v.zona) fd.append('zona_utm', v.zona);
  if (v.hemisferio) fd.append('hemisferio', v.hemisferio);
  fd.append('observaciones_medicas', v.obs);
  fd.append('registrado_por', v.por);
  if (fotoFile) fd.append('foto', fotoFile);

  try {
    await api('POST', '/ciudadanos/', fd);
    toast('Registrado correctamente');
    fotoFile = null; $('camera-preview').classList.add('hide'); $('camera-placeholder').classList.remove('hide'); $('foto-input').value = '';
    campos.forEach(c => { const el = $('reg-' + c); if (el) el.value = '' }); $('reg-fecnac').value = '';
    showPage('home')
  } catch (e) { toast('Error: ' + e.message) }
}

async function buscarCedula() {
  const ced = $('search-cedula').value.trim();
  if (!ced) { toast('Ingrese una cédula'); return }
  try {
    const r = await api('GET', '/busqueda/cedula/' + encodeURIComponent(ced));
    mostrarDetalle(r)
  } catch (e) { toast('No encontrado'); $('search-results').classList.add('hide') }
}

async function buscarFacial() {
  if (!faceFile) { toast('Seleccione una foto primero'); return }
  const fd = new FormData(); fd.append('foto', faceFile);
  try {
    const r = await api('POST', '/busqueda/facial?limite=20&umbral=0.3', fd);
    $('search-results').classList.remove('hide');
    const list = $('results-list');
    if (!r.resultados || r.resultados.length === 0) { list.innerHTML = '<div style="text-align:center;padding:20px;color:var(--gray)"><strong>No encontrado</strong><br><br>No se encontraron coincidencias faciales. Intente con otra foto o reduzca el umbral.</div>'; return }
    list.innerHTML = r.resultados.map(p => `<div class="result-item" onclick="mostrarDetalle({id:'${p.id}'})">
      <div style="display:flex;gap:12px;align-items:center">
        <div style="flex:1"><div class="result-name">${p.nombre || ''} ${p.apellido || ''}</div><div class="result-cedula">${p.cedula || ''}</div></div>
        <div><div class="similarity">${(p.similitud * 100).toFixed(1)}%</div><div class="result-status status-${p.estado_salud || 'estable'}">${p.estado_salud || 'N/A'}</div></div>
      </div>
    </div>`).join('')
  } catch (e) { toast('Error: ' + e.message) }
}

async function mostrarDetalle(p) {
  try {
    const r = p.id ? await api('GET', '/ciudadanos/' + p.id) : p;
    $('detail-content').innerHTML = `
      <div class="card">
        ${r.url_foto ? `<img src="/${r.url_foto}" style="width:100%;max-height:300px;object-fit:cover;border-radius:8px;margin-bottom:12px">` : ''}
        <div class="detail-row"><div class="detail-label">Cédula</div><div class="detail-value">${r.cedula || 'N/A'}</div></div>
        <div class="detail-row"><div class="detail-label">Nombre</div><div class="detail-value">${r.nombre || ''} ${r.apellido || ''}</div></div>
        <div class="detail-row"><div class="detail-label">Nacimiento</div><div class="detail-value">${r.fecha_nacimiento || 'N/A'}</div></div>
        <div class="detail-row"><div class="detail-label">Salud</div><div class="detail-value"><span class="result-status status-${r.estado_salud || 'estable'}">${r.estado_salud || 'N/A'}</span></div></div>
        <div class="detail-row"><div class="detail-label">Ubicación</div><div class="detail-value">${r.ubicacion_actual || 'N/A'}</div></div>
        ${r.utm_este ? `<div class="detail-row"><div class="detail-label">UTM</div><div class="detail-value">${r.zona_utm || '?'} ${r.hemisferio || ''} ${r.utm_este}E ${r.utm_norte}N</div></div>` : ''}
        ${r.observaciones_medicas ? `<div class="detail-row"><div class="detail-label">Observaciones</div><div class="detail-value">${r.observaciones_medicas}</div></div>` : ''}
        <div class="detail-row"><div class="detail-label">Registrado por</div><div class="detail-value">${r.registrado_por || 'N/A'}</div></div>
        <div class="detail-row"><div class="detail-label">Registrado</div><div class="detail-value">${new Date(r.creado_at).toLocaleString()}</div></div>
      </div>`;
    showPage('detail')
  } catch (e) { toast('Error: ' + e.message) }
}

function volver() {
  const prev = lastView.length > 1 ? lastView[lastView.length - 2] : 'home';
  showPage(prev)
}

async function cargarHome() {
  try {
    const r = await api('GET', '/ciudadanos/?limit=5');
    $('stat-total').textContent = r.length || 0;
    const hoy = new Date().toISOString().slice(0, 10);
    const hoyCount = r.filter(p => p.creado_at && p.creado_at.slice(0, 10) === hoy).length;
    $('stat-hoy').textContent = hoyCount;
    if (r.length === 0) { $('recent-list').innerHTML = '<div style="text-align:center;padding:20px;color:var(--gray)">No hay registros aún</div>'; return }
    $('recent-list').innerHTML = r.map(p => `<div class="result-item" onclick="mostrarDetalle({id:'${p.id}'})">
      <div class="result-name">${p.nombre || '?'} ${p.apellido || ''}</div>
      <div class="result-cedula">${p.cedula || 'Sin cédula'} · ${p.ubicacion_actual ? p.ubicacion_actual.slice(0, 30) : 'N/A'}</div>
    </div>`).join('')
  } catch (e) { $('recent-list').innerHTML = '<div style="text-align:center;padding:20px;color:var(--red)">Error al conectar</div>' }
}

cargarHome()
