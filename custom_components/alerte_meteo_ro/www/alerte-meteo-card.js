/* Alerte Meteo România — card Lovelace (avertizări ANM + nowcasting).
 * Fără configurare: județul și entitățile vin din integrarea „Alerte Meteo România”.
 * Opțional: `judet: Mureș` (nume sau cod, ex. MS) sau alegere din editorul vizual.
 * Încărcat automat de integrare; apare în lista de carduri „Alerte Meteo România”.
 * Fișier generat din examples/lovelace_card_alerte_meteo.yaml. */
const JUDETE = {"AB": "Alba", "AR": "Arad", "AG": "Argeș", "BC": "Bacău", "BH": "Bihor", "BN": "Bistrița-Năsăud", "BT": "Botoșani", "BR": "Brăila", "BV": "Brașov", "B": "București", "BZ": "Buzău", "CL": "Călărași", "CS": "Caraș-Severin", "CJ": "Cluj", "CT": "Constanța", "CV": "Covasna", "DB": "Dâmbovița", "DJ": "Dolj", "GL": "Galați", "GR": "Giurgiu", "GJ": "Gorj", "HR": "Harghita", "HD": "Hunedoara", "IL": "Ialomița", "IS": "Iași", "IF": "Ilfov", "MM": "Maramureș", "MH": "Mehedinți", "MS": "Mureș", "NT": "Neamț", "OT": "Olt", "PH": "Prahova", "SJ": "Sălaj", "SM": "Satu Mare", "SB": "Sibiu", "SV": "Suceava", "TR": "Teleorman", "TM": "Timiș", "TL": "Tulcea", "VL": "Vâlcea", "VS": "Vaslui", "VN": "Vrancea"};
const norm = (x) => String(x || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
// `judet` din configurare: cod (MS) sau nume (Mureș / mures / Alba), cu sau fără diacritice
const resolveJudet = (v) => {
  const n = norm(v); if (!n) return null;
  for (const [cod, nume] of Object.entries(JUDETE)) if (norm(cod) === n || norm(nume) === n) return { cod, nume, slug: norm(nume) };
  return null;
};

const render = (states, cfg) => {
  const S = (id) => states[id] || {};
  const now = new Date();
  // Entitățile integrării se descoperă după prefix; județul vine din integrare.
  const keyBy = (p) => Object.keys(states).filter(k => k.startsWith(p));
  const SEL = resolveJudet(cfg && cfg.judet);   // județ ales în card (opțional)
  const JC = SEL ? SEL.cod : (((states[keyBy('sensor.culoare_harta_')[0]] || {}).attributes || {}).judet_cod || '');
  const MO = {ianuarie:0,februarie:1,martie:2,aprilie:3,mai:4,iunie:5,iulie:6,august:7,septembrie:8,octombrie:9,noiembrie:10,decembrie:11};
  const mkD = (x) => { let d = new Date(now.getFullYear(), MO[String(x[2]).toLowerCase()], parseInt(x[1], 10), parseInt(x[3], 10), 0, 0); if (d - now > 200 * 864e5) d = new Date(d.getFullYear() - 1, d.getMonth(), d.getDate(), d.getHours()); return d; };
  const parseIv = (s) => { const m = [...String(s || '').matchAll(/(\d+)\s+([a-zăâîșşțţ]+),\s*ora\s*(\d+)/gi)]; if (m.length < 2) return null; const a0 = mkD(m[0]); let e0 = mkD(m[1]); if (e0 < a0) e0 = new Date(e0.getFullYear() + 1, e0.getMonth(), e0.getDate(), e0.getHours()); return [a0, e0]; };
  const pad = (v) => String(v).padStart(2, '0');
  const hm = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  const dl = (d) => d.toDateString() === now.toDateString() ? 'azi' : d.toDateString() === new Date(now.getTime() + 864e5).toDateString() ? 'mâine' : `${['dum','lun','mar','mie','joi','vin','sâm'][d.getDay()]} ${pad(d.getDate())}.${pad(d.getMonth() + 1)}`;
  const rem = (ms) => { const m = Math.max(0, Math.round(ms / 60000)), h = Math.floor(m / 60); return h >= 24 ? `${Math.floor(h / 24)}z ${h % 24}h` : h > 0 ? `${h}h ${pad(m % 60)}m` : `${m} min`; };
  const cap = (s) => s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
  const emo = (s) => { const x = String(s || '').toLowerCase();
    if (/grindin/.test(x)) return '🌨️'; if (/descărc|descarc|oraj|furtun/.test(x)) return '⛈️'; if (/canicul|căldur|caldur|disconfort termic/.test(x)) return '🥵';
    if (/\bger\b|temperaturi scăzute|frig/.test(x)) return '🥶'; if (/viscol/.test(x)) return '🌬️'; if (/ninsor|zăpad|zapad/.test(x)) return '❄️';
    if (/inundați|inundati|viitur/.test(x)) return '🌊'; if (/averse|instabilit|ploa|precipitați|precipitati/.test(x)) return '🌧️';
    if (/vânt|vant|rafal|vijelii/.test(x)) return '💨'; if (/ceață|ceata/.test(x)) return '🌫️'; return '⚠️'; };
  const CN = ['', 'galben', 'portocaliu', 'roșu'], CC = ['', '#f1c40f', '#e67e22', '#e74c3c'], TX = ['', '#000', '#000', '#fff'];
  
  // --- Date: avertizări ANM pentru județul ales + nowcasting ---
  let ncC = 0, ncEnd = '', ncF = '';
  const wx = (((S('sensor.avertizari_meteo_anm').attributes || {}).avertizari) || [])
    .filter(w => w && typeof w === 'object' && JC && w.judet === JC)
    .map(w => { const p = parseIv(w.intervalul); return p ? { c: parseInt(w.culoare, 10) || 0, s: p[0], e: p[1], f: w.fenomene_vizate || '' } : null; })
    .filter(Boolean);
  const nks = keyBy('sensor.alerta_nowcasting_');
  const nk = (SEL && nks.find(k => k === 'sensor.alerta_nowcasting_' + SEL.slug)) || nks.find(k => (parseInt(((states[k] || {}).attributes || {})['Alerte active'], 10) || 0) > 0) || nks[0];
  const na = (states[nk] || {}).attributes || {};
  if ((parseInt(na['Alerte active'], 10) || 0) > 0) {
    const cc0 = String(na['Culoare'] || '').toLowerCase();
    ncC = /ro[sș]u/.test(cc0) ? 3 : /portocal/.test(cc0) ? 2 : /galben/.test(cc0) ? 1 : 0;
    ncEnd = String(na['Sfârșit'] || ''); ncF = String(na['semnalare'] || '');
  }
  const act = wx.filter(w => w.c >= 1 && w.s <= now && now < w.e).sort((p, q) => q.c - p.c || q.e - p.e);
  const nxt = wx.filter(w => w.c >= 1 && w.s > now && w.s - now < 48 * 36e5).sort((p, q) => p.s - q.s);
  
  // --- Mesajele ANM complete (folosite și pentru salt din rezumat) ---
  const me = states[(SEL && states['sensor.mesaj_meteo_' + SEL.slug]) ? 'sensor.mesaj_meteo_' + SEL.slug : keyBy('sensor.mesaj_meteo_')[0]] || {}, txt = (me.attributes || {}).mesaj_complet || '';
  const ids = String(S('sensor.anm_avertizare_id').state || '').split(',').map(x => x.trim()).filter(x => x && x !== '0' && !['unavailable', 'unknown', 'none'].includes(x)).reverse();
  const txtS = String(txt);
  const heads = [...txtS.matchAll(/MESAJ\s+(\d+)\s*\/\s*(\d+)/gi)].map(m => `${m[1]}/${m[2]}`);
  const blocks = txtS.split(/MESAJ\s+\d+\s*\/\s*\d+/i).map(b => b.trim()).filter(Boolean);
  const wxc = wx.filter(w => w.c >= 1);
  // există un mesaj complet pentru acest interval? (atunci blocul din rezumat devine clicabil)
  const hasMsg = (w) => blocks.some(b => { const iv = (b.match(/^\s*Interval[^:\n]*:\s*([^\n]+)/im) || [])[1]; const p = parseIv(iv); return !!(p && Math.abs(w.s - p[0]) < 6e4 && Math.abs(w.e - p[1]) < 6e4); });
  // salt la mesajul complet: deschide cardul, derulează până la mesaj și îl evidențiază scurt
  const GO = "(function(el){var d=el.closest('details');if(!d)return;var s=el.dataset.s,e=el.dataset.e,c=el.dataset.c;var t=[].slice.call(d.querySelectorAll('[data-msg]')).filter(function(m){return m.dataset.s===s&&m.dataset.e===e;});if(t.length>1){var t2=t.filter(function(m){return m.dataset.c===c;});if(t2.length)t=t2;}if(!t.length)t=[].slice.call(d.querySelectorAll('[data-msg]'));if(!t.length)return;d.open=true;var m=t[0];m.scrollIntoView({behavior:'smooth',block:'start'});m.style.transition='box-shadow .3s';m.style.boxShadow='0 0 0 2px var(--primary-color)';setTimeout(function(){m.style.boxShadow='';},2000);})(this)";
  
  const pill = (c) => `<span style="background:${CC[c]};color:${TX[c]};padding:2px 9px;border-radius:6px;font-weight:700;font-size:13px;letter-spacing:.3px;white-space:nowrap">COD ${CN[c].toUpperCase()}</span>`;
  const H3 = (t) => `<div style="font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--primary-text-color);opacity:.75;margin:12px 0 4px">${t}</div>`;
  const blk = (c, ic, head, sub, w) => { const go = !!(w && hasMsg(w)); return `<div ${go ? `data-s="${w.s.getTime()}" data-e="${w.e.getTime()}" data-c="${w.c}" onclick="${GO}" onpointerup="if(event.pointerType==='touch')${GO}" title="Mergi la mesajul complet ANM"` : ''} style="display:flex;gap:10px;align-items:flex-start;padding:8px 10px;margin:6px 0;border-left:4px solid ${CC[c]};background:color-mix(in srgb,${CC[c]} 13%,transparent);border-radius:0 8px 8px 0${go ? ';cursor:pointer' : ''}">
    <span style="font-size:22px;line-height:1.2;flex:none">${ic}</span>
    <div style="min-width:0;flex:1"><div style="display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px">${head}</div><div style="font-size:14px;margin-top:3px;overflow-wrap:anywhere">${sub}</div></div>${go ? '<ha-icon icon="mdi:arrow-down" style="--mdc-icon-size:18px;opacity:.5;flex:none;align-self:center"></ha-icon>' : ''}</div>`; };
  const T = (t, w) => `<span style="font-size:14px;font-weight:${w || 600}">${t}</span>`;
  
  // --- Corp: ACUM / URMEAZĂ ---
  let h = '';
  if (act.length || ncC >= 1) {
    h += H3('Acum');
    if (ncC >= 1) h += blk(ncC, '⚡', pill(ncC) + T(ncEnd ? `nowcasting · până ${ncEnd}` : 'nowcasting · acum'), cap(ncF) || 'Fenomen violent iminent');
    h += act.map(w => blk(w.c, emo(w.f), pill(w.c) + T(`până ${dl(w.e) === 'azi' ? '' : dl(w.e) + ' '}${hm(w.e)}`) + `<span style="font-size:13px;opacity:.75">încă ${rem(w.e - now)}</span>`, cap(w.f), w)).join('');
  }
  if (nxt.length) {
    h += H3('Urmează');
    h += nxt.map(w => blk(w.c, emo(w.f), pill(w.c) + T(`${dl(w.s)} ${hm(w.s)} → ${dl(w.e) === dl(w.s) ? '' : dl(w.e) + ' '}${hm(w.e)}`) + `<span style="font-size:13px;opacity:.75">în ${rem(w.s - now)}</span>`, cap(w.f), w)).join('');
  }
  if (!act.length && ncC < 1 && !nxt.length) h += `<div style="font-size:14px;padding:6px 2px">✅ Nicio avertizare activă sau în următoarele 48h.</div>`;
  
  // --- Detalii ANM: mesajul complet + harta ---
  const msgHtml = blocks.map((b, i) => {
    const typ = (b.match(/(ATEN[ȚT]IONARE|AVERTIZARE|INFORMARE)\s+METEOROLOGIC[ĂA]/i) || [])[0] || 'MESAJ METEOROLOGIC';
    const cm = b.match(/COD\s+(GALBEN|PORTOCALIU|RO[ȘS]U)/i);
    const cc = cm ? (/RO/i.test(cm[1]) ? 3 : /PORT/i.test(cm[1]) ? 2 : 1) : 0;
    const val = (re) => { const m = b.match(re); return m ? m[1].trim() : ''; };
    const iv = val(/^\s*Interval[^:\n]*:\s*([^\n]+)/im), fen = val(/^\s*Fenomene[^:\n]*:\s*([^\n]+)/im), zone = val(/^\s*Zone afectate:\s*([^\n]+)/im), nota = val(/^\s*Not[ăa]:\s*([^\n]+)/im);
    const body = b.split('\n').map(l => l.trim()).filter(l => l && !/^(ATEN[ȚT]IONARE|AVERTIZARE|INFORMARE|COD\s|Interval|Fenomene|Zone afectate|Not[ăa]:)/i.test(l)).join('<br><br>');
    const p = parseIv(iv);
    const rel = !!(p && wxc.some(w => Math.abs(w.s - p[0]) < 6e4 && Math.abs(w.e - p[1]) < 6e4));
    const col = CC[cc] || '#888', mid = ids[i];
    const img = mid ? `<img loading="lazy" src="https://images.weserv.nl/?url=${encodeURIComponent('https://www.meteoromania.ro/wp-content/plugins/meteo/harti/harta.svg.php?id_avertizare=' + mid)}" style="width:100%;max-width:380px;display:block;margin:10px auto 0;border-radius:8px;border:1.5px solid ${col}">` : '';
    return `<div data-msg="1" data-s="${p ? p[0].getTime() : ''}" data-e="${p ? p[1].getTime() : ''}" data-c="${cc}" style="scroll-margin-top:90px;margin:10px 0;padding:10px 12px;border-left:4px solid ${col};background:color-mix(in srgb,${col} ${rel ? 13 : 5}%,transparent);border-radius:0 8px 8px 0;${rel ? '' : 'opacity:.72'}">
      <div style="display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px"><b style="font-size:14px">MESAJ ${heads[i] || i + 1}</b>${cc ? pill(cc) : ''}${rel ? '<span style="font-size:13px;font-weight:700">📍 Zona ta</span>' : ''}</div>
      <div style="font-size:13px;opacity:.75;margin-top:2px">${typ}</div>
      ${iv ? `<div style="font-size:14px;margin-top:6px">🕒 <b>${iv}</b></div>` : ''}
      ${fen ? `<div style="font-size:14px;margin-top:4px"><b>Fenomene:</b> ${fen}</div>` : ''}
      ${zone ? `<div style="font-size:14px;margin-top:4px"><b>Zone afectate:</b> ${zone}</div>` : ''}
      ${body ? `<div style="font-size:14px;line-height:1.5;margin-top:8px">${body}</div>` : ''}
      ${nota ? `<div style="font-size:14px;margin-top:6px"><b>Notă:</b> ${nota}</div>` : ''}
      ${img}</div>`;
  }).join('');
  let det = H3('Informații ANM · mesaj complet') + msgHtml;
  det += `<div style="margin-top:14px;padding-top:10px;border-top:1px solid var(--divider-color);text-align:center"><a href="https://www.meteoromania.ro/avertizari/" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()" style="pointer-events:auto;font-size:14px;font-weight:600;color:var(--primary-color);text-decoration:none">🔗 Avertizări pe meteoromania.ro (ANM)</a></div>`;
  
  // --- Antet pliabil: titlu, culoare și stare deschis/închis după avertizare ---
  const top = Math.max(act.length ? act[0].c : 0, ncC, nxt.length ? nxt[0].c : 0);
  const has = top >= 1;
  const status = has ? 'alerta' : 'liniste';
  let open = has;                       // implicit: expandat cu avertizare, colapsat fără
  try {                                 // păstrează alegerea manuală cât timp starea nu se schimbă
    const st = JSON.parse(localStorage.getItem('alerte_meteo_ro_card') || 'null');
    if (st && st.status === status) open = !!st.open;
  } catch (e) {}
  const bg = has ? CC[top] : 'var(--secondary-background-color)';
  const fg = has ? TX[top] : 'var(--primary-text-color)';
  const title = has ? 'AVERTIZARE METEO ACTIVĂ' : 'NICIO AVERTIZARE METEO';
  const icon = has ? 'mdi:alert' : 'mdi:check-circle-outline';
  // Antet compact: un singur rând și pe telefon (text mic, fără text suplimentar;
  // codul culorii se vede din culoarea antetului și din pastilele din card).
  return `<style>.amr summary{list-style:none}.amr summary::-webkit-details-marker{display:none}.amr[open] .amr-chev{transform:rotate(180deg)}.amr-chev{transition:transform .2s}</style>
  <details class="amr" ${open ? 'open' : ''} ontoggle="try{localStorage.setItem('alerte_meteo_ro_card',JSON.stringify({status:'${status}',open:this.open}))}catch(e){}" style="text-align:left;pointer-events:auto">
    <summary style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:9px 12px;background:${bg};color:${fg};font-weight:800;font-size:12.5px;line-height:1.2;text-transform:uppercase;letter-spacing:.2px">
      <ha-icon icon="${icon}" style="--mdc-icon-size:20px;flex:none"></ha-icon>
      <span style="flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${title}</span>
      <ha-icon class="amr-chev" icon="mdi:chevron-down" style="--mdc-icon-size:20px;flex:none"></ha-icon>
    </summary>
    <div style="padding:6px 14px 14px">${h}${det}</div>
  </details>`;
  
};

class AlerteMeteoCard extends HTMLElement {
  setConfig(config) { this._config = config || {}; this._sig = null; this._build(); }
  _build() {
    if (this._card) return;
    this._card = document.createElement('ha-card');
    this._card.style.cssText = 'padding:0;border-radius:12px;overflow:hidden';
    this.appendChild(this._card);
  }
  set hass(hass) {
    this._hass = hass;
    if (!this._card) this._build();
    const st = hass.states, ids = Object.keys(st).filter(k => k.startsWith('sensor.avertizari_meteo_anm') || k.startsWith('sensor.mesaj_meteo_') || k.startsWith('sensor.culoare_harta_') || k.startsWith('sensor.alerta_nowcasting_') || k === 'sensor.anm_avertizare_id');
    const sig = ids.map(k => k + st[k].last_updated).join('|') + '|' + Math.floor(Date.now() / 60000);
    if (sig === this._sig) return;
    this._sig = sig;
    try { this._card.innerHTML = render(st, this._config); }
    catch (e) { this._card.innerHTML = '<div style="padding:12px">Alerte Meteo: eroare la randare (' + e.message + ')</div>'; }
  }
  getCardSize() { return 4; }
  static getStubConfig() { return {}; }
  static getConfigElement() { return document.createElement('alerte-meteo-card-editor'); }
}

class AlerteMeteoCardEditor extends HTMLElement {
  setConfig(config) { this._config = config || {}; this._render(); }
  set hass(hass) { this._hass = hass; if (this._form) this._form.hass = hass; }
  _render() {
    if (!this._form) {
      this._form = document.createElement('ha-form');
      this._form.computeLabel = (s) => s.label || s.name;
      this._form.addEventListener('value-changed', (e) => {
        const v = (e.detail.value || {}).judet;
        const cfg = Object.assign({}, this._config);
        if (v) cfg.judet = v; else delete cfg.judet;
        this._config = cfg;
        this.dispatchEvent(new CustomEvent('config-changed', { detail: { config: cfg }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    const opts = [{ value: '', label: 'Automat (județul din integrare)' }].concat(
      Object.entries(JUDETE).sort((a, b) => a[1].localeCompare(b[1], 'ro')).map(([cod, nume]) => ({ value: cod, label: nume })));
    this._form.schema = [{ name: 'judet', label: 'Județ', selector: { select: { options: opts, mode: 'dropdown' } } }];
    this._form.data = { judet: (resolveJudet(this._config.judet) || {}).cod || '' };
    if (this._hass) this._form.hass = this._hass;
  }
}
if (!customElements.get('alerte-meteo-card-editor')) customElements.define('alerte-meteo-card-editor', AlerteMeteoCardEditor);
if (!customElements.get('alerte-meteo-card')) customElements.define('alerte-meteo-card', AlerteMeteoCard);
window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === 'alerte-meteo-card')) {
  window.customCards.push({ type: 'alerte-meteo-card', name: 'Alerte Meteo România', description: 'Avertizări ANM + nowcasting pentru județul ales în integrare (fără configurare).' });
}
