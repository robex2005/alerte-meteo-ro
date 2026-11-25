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

// județele pentru nowcasting adăugate în integrare (senzori care nu sunt indisponibili)
const integCounties = (states) => {
  const seen = {};
  Object.keys(states).filter(k => /^sensor\.alerta_nowcasting_/.test(k) && !['unavailable', 'unknown'].includes(states[k].state))
    .forEach(k => { const j = resolveJudet(k.replace(/^sensor\.alerta_nowcasting_/, '')); if (j) seen[j.cod] = j; });
  return Object.values(seen).sort((a, b) => a.nume.localeCompare(b.nume, 'ro'));
};

const render = (states, cfg) => {
  const S = (id) => states[id] || {};
  const now = new Date();
  // Entitățile integrării se descoperă după prefix; județul vine din integrare.
  const keyBy = (p) => Object.keys(states).filter(k => k.startsWith(p));
  // entitățile rămase „indisponibile” (de ex. după schimbarea județului în integrare) sunt ignorate
  const okKeys = (p) => keyBy(p).filter(k => !['unavailable', 'unknown'].includes((states[k] || {}).state));
  const autoJC = ((states[okKeys('sensor.culoare_harta_')[0]] || {}).attributes || {}).judet_cod || '';
  // avertizări ANM: un singur județ (cel ales în integrare); nowcasting: județele bifate în card
  const ANMJ = resolveJudet(autoJC);
  const INTEG = integCounties(states);
  let SELS = [].concat((cfg && (cfg.judete || cfg.judet)) || []).map(resolveJudet).filter(Boolean);
  if (!SELS.length) SELS = INTEG;
  const multi = SELS.length > 1;
  const SEL = ANMJ || SELS[0] || null;
  const JC = SEL ? SEL.cod : autoJC;
  const MO = {ianuarie:0,februarie:1,martie:2,aprilie:3,mai:4,iunie:5,iulie:6,august:7,septembrie:8,octombrie:9,noiembrie:10,decembrie:11};
  const mkD = (x) => { let d = new Date(now.getFullYear(), MO[String(x[2]).toLowerCase()], parseInt(x[1], 10), parseInt(x[3], 10), 0, 0); if (d - now > 200 * 864e5) d = new Date(d.getFullYear() - 1, d.getMonth(), d.getDate(), d.getHours()); return d; };
  const parseIv = (s) => { const m = [...String(s || '').matchAll(/(\d+)\s+([a-zăâîșşțţ]+),\s*ora\s*(\d+)/gi)]; if (m.length < 2) return null; const a0 = mkD(m[0]); let e0 = mkD(m[1]); if (e0 < a0) e0 = new Date(e0.getFullYear() + 1, e0.getMonth(), e0.getDate(), e0.getHours()); return [a0, e0]; };
  const pad = (v) => String(v).padStart(2, '0');
  const hm = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  const dl = (d) => d.toDateString() === now.toDateString() ? 'azi' : d.toDateString() === new Date(now.getTime() + 864e5).toDateString() ? 'mâine' : `${['dum','lun','mar','mie','joi','vin','sâm'][d.getDay()]} ${pad(d.getDate())}.${pad(d.getMonth() + 1)}`;
  const rem = (ms) => { const m = Math.max(0, Math.round(ms / 60000)), h = Math.floor(m / 60); return h >= 24 ? `${Math.floor(h / 24)}z ${h % 24}h` : h > 0 ? `${h}h ${pad(m % 60)}m` : `${m} min`; };
  const cap = (s) => s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
  const emo = (s) => { const x = String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[șş]/g, 's').toLowerCase() + ' ' + String(s || '').toLowerCase();
    if (/grindin/.test(x)) return '🌨️'; if (/descărc|descarc|oraj|furtun/.test(x)) return '⛈️'; if (/canicul|căldur|caldur|disconfort termic/.test(x)) return '🥵';
    if (/\bger\b|temperaturi scăzute|frig/.test(x)) return '🥶'; if (/viscol/.test(x)) return '🌬️'; if (/ninsor|zăpad|zapad/.test(x)) return '❄️';
    if (/inundați|inundati|viitur/.test(x)) return '🌊'; if (/polei/.test(x)) return '🧊'; if (/averse|instabilit|ploa|ploi|torenț|torent|precipitați|precipitati/.test(x)) return '🌧️';
    if (/vânt|vant|rafal|vijeli/.test(x)) return '💨'; if (/ceață|ceata/.test(x)) return '🌫️'; return '⚠️'; };
  const CN = ['', 'galben', 'portocaliu', 'roșu'], CC = ['', '#f1c40f', '#e67e22', '#e74c3c'], TX = ['', '#000', '#000', '#fff'];
  
  // --- Date: avertizări ANM pentru județul ales + nowcasting ---
  const colOf = (x) => /ro[sș]u/.test(x) ? 3 : /portocal/.test(x) ? 2 : /galben/.test(x) ? 1 : 0;
  // `avertizari` e listă doar când există avertizări; altfel ANM trimite textul "Nu exista avertizari"
  const allWRaw = (S('sensor.avertizari_meteo_anm').attributes || {}).avertizari;
  const allW = Array.isArray(allWRaw) ? allWRaw : [];
  const wx = [], ncs = [];
  if (ANMJ) {
    const mapSt = states['sensor.culoare_harta_' + ANMJ.slug] || {};
    const mapC = colOf(String(mapSt.state || '').toLowerCase());
    // zone parțiale (munte / altitudine / litoral) colorate pe hartă, când județul întreg nu e colorat
    const zA = (mapSt.attributes || {}).zone_partiale || {};
    const zoneC = colOf(String((mapSt.attributes || {}).culoare_zona || '').toLowerCase());
    const ZN = { munte: 'zone de munte', litoral: 'litoral' };
    const zoneNames = [...new Set(Object.values(zA).flatMap(z => (z && typeof z === 'object') ? Object.keys(z) : []))].map(k => ZN[k] || (/^alt(\d+)$/.test(k) ? 'peste ' + k.replace('alt', '') + ' m' : k)).join(', ');
    allW.filter(w => w && typeof w === 'object' && w.judet === ANMJ.cod).forEach(w => {
      let p = parseIv(w.intervalul);
      // ANM scrie uneori „conform textelor” în loc de interval: folosim datele de apariție/expirare din listă
      if (!p) { const a = new Date(w.data_aparitiei), e = new Date(w.data_expirarii); if (!isNaN(a) && !isNaN(e) && e > a) p = [a, e]; }
      if (!p) return;
      let c = parseInt(w.culoare, 10) || 0;
      // ANM trimite uneori `culoare: 0` pentru intervalul activ; atunci folosim culoarea județului de pe hartă
      let loc = '';
      if (!c && p[0] <= now && now < p[1]) {
        c = mapC;
        if (!c && zoneC) { c = zoneC; loc = zoneNames || 'zone locale'; }
      }
      wx.push({ c, s: p[0], e: p[1], f: w.fenomene_vizate || '', j: ANMJ.nume, loc });
    });
  }
  SELS.forEach(J => {
    const na = (states['sensor.alerta_nowcasting_' + J.slug] || {}).attributes || {};
    if ((parseInt(na['Alerte active'], 10) || 0) > 0) {
      const c = colOf(String(na['Culoare'] || '').toLowerCase());
      if (c) ncs.push({ c, end: String(na['Sfârșit'] || ''), f: String(na['semnalare'] || ''), j: J.nume });
    }
  });
  ncs.sort((x, y) => y.c - x.c);
  const ncC = ncs.length ? ncs[0].c : 0;
  const act = wx.filter(w => w.c >= 1 && w.s <= now && now < w.e).sort((p, q) => q.c - p.c || q.e - p.e);
  const nxt = wx.filter(w => w.c >= 1 && w.s > now && w.s - now < 48 * 36e5).sort((p, q) => p.s - q.s);
  
  // --- Mesajele ANM complete (folosite și pentru salt din rezumat) ---
  const me = states[[SEL].filter(Boolean).map(J => 'sensor.mesaj_meteo_' + J.slug).find(id => states[id] && !['unavailable', 'unknown'].includes(states[id].state)) || okKeys('sensor.mesaj_meteo_')[0]] || {}, txt = (me.attributes || {}).mesaj_complet || '';
  const ids = String(S('sensor.anm_avertizare_id').state || '').split(',').map(x => x.trim()).filter(x => x && x !== '0' && !['unavailable', 'unknown', 'none'].includes(x)).reverse();
  const txtS = String(txt);
  const heads = [...txtS.matchAll(/MESAJ\s+(\d+)\s*\/\s*(\d+)/gi)].map(m => `${m[1]}/${m[2]}`);
  // fără avertizări ANM trimite doar „Nu exista avertizari”: nu e un mesaj de afișat
  const blocks = txtS.split(/MESAJ\s+\d+\s*\/\s*\d+/i).map(b => b.trim()).filter(b => b && /ATEN[ȚT]IONARE|AVERTIZARE|INFORMARE|\bCOD\s|Interval/i.test(b));
  // ANM scrie uneori „conform textelor” în loc de fenomen: îl luăm din mesajul complet cu același interval
  // textul mesajelor vine cu entități HTML (ex. v&acirc;ntului): le decodăm
  const dec = (t) => { try { const e = document.createElement('textarea'); e.innerHTML = t; return String(e.value).replace(/[<>]/g, ''); } catch (x) { return t; } };
  const fenOf = (b) => dec(((b.match(/^\s*Fenomene[^:\n]*:\s*([^\n]+)/im) || [])[1] || '').trim());
  const ivOf = (b) => parseIv((b.match(/^\s*Interval[^:\n]*:\s*([^\n]+)/im) || [])[1]);
  wx.forEach(w => {
    if (w.f && !/conform\s+text/i.test(w.f)) return;
    const b = blocks.find(x => { const p = ivOf(x); return p && Math.abs(w.s - p[0]) < 6e4 && Math.abs(w.e - p[1]) < 6e4; });
    w.f = (b && fenOf(b)) || '';
  });
  const wxc = wx.filter(w => w.c >= 1);
  // există un mesaj complet pentru acest interval? (atunci blocul din rezumat devine clicabil)
  const hasMsg = (w) => blocks.some(b => { const iv = (b.match(/^\s*Interval[^:\n]*:\s*([^\n]+)/im) || [])[1]; const p = parseIv(iv); return !!(p && Math.abs(w.s - p[0]) < 6e4 && Math.abs(w.e - p[1]) < 6e4); });
  // salt la mesajul complet: deschide cardul, derulează până la mesaj și îl evidențiază scurt
  // numărul mesajului ANM (ex. „2/2”) care corespunde intervalului unei alerte, sau '' dacă nu are text detaliat
  const msgNo = (w) => { const i = blocks.findIndex(b => { const iv = (b.match(/^\s*Interval[^:\n]*:\s*([^\n]+)/im) || [])[1]; const p = parseIv(iv); return !!(p && Math.abs(w.s - p[0]) < 6e4 && Math.abs(w.e - p[1]) < 6e4); }); return i >= 0 ? (heads[i] || String(i + 1)) : ''; };
  const GO = "(function(el){var d=el.closest('details');if(!d)return;var s=el.dataset.s,e=el.dataset.e,c=el.dataset.c;var t=[].slice.call(d.querySelectorAll('[data-msg]')).filter(function(m){return m.dataset.s===s&&m.dataset.e===e;});if(t.length>1){var t2=t.filter(function(m){return m.dataset.c===c;});if(t2.length)t=t2;}if(!t.length)t=[].slice.call(d.querySelectorAll('[data-msg]'));if(!t.length)return;d.open=true;var m=t[0];m.scrollIntoView({behavior:'smooth',block:'start'});m.style.transition='box-shadow .3s';m.style.boxShadow='0 0 0 2px var(--primary-color)';setTimeout(function(){m.style.boxShadow='';},2000);})(this)";
  
  const pill = (c) => `<span style="background:${CC[c]};color:${TX[c]};padding:1px 7px;border-radius:5px;font-weight:700;font-size:12px;white-space:nowrap;flex:none">COD ${CN[c].toUpperCase()}</span>`;
  const H3 = (t) => `<div style="font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--primary-text-color);opacity:.75;margin:12px 0 4px">${t}</div>`;
  const NW = 'white-space:nowrap;overflow:hidden;text-overflow:ellipsis';
  const fenList = (f) => String(dec(String(f || ''))).split(/,|;|\s+și\s+/).map(x => x.trim().replace(/\.$/, '')).filter(Boolean);
  // rând cu iconiță în stânga; textul lung trece pe rândul următor, aliniat după iconiță
  const row = (ic, tx) => `<div style="display:flex;gap:6px;align-items:baseline;font-size:13px;margin-top:3px"><span style="flex:none;width:20px;text-align:center">${ic}</span><span style="min-width:0;overflow-wrap:anywhere">${tx}</span></div>`;
  const fenRows = (f) => (fenList(f).length ? fenList(f) : ['fenomen violent iminent']).map(x => row(emo(x), cap(x))).join('');
  const head = (c, nc, zone) => `<div style="display:flex;align-items:center;gap:8px">${pill(c)}${nc ? '<span style="font-size:12px;font-weight:700;white-space:nowrap;flex:none">⚡ Nowcasting</span>' : ''}<span style="flex:1;min-width:0;text-align:right;font-size:13px;font-weight:600;${NW}">${zone}</span></div>`;
  // bloc scurt: cod (+ nowcasting) · zonă / ora / fenomene una sub alta
  // fundal în culoarea alertei: 'a' = activă acum (mai intens), 'n' = urmează (mai discret)
  const NEW = true;
  const BGK = (c, k) => NEW && k ? `background:color-mix(in srgb, ${CC[c]} ${k === 'a' ? 15 : 6}%, transparent);` : '';
  const item = (o) => { const go = !!(o.w && hasMsg(o.w)); return `<div ${go ? `data-s="${o.w.s.getTime()}" data-e="${o.w.e.getTime()}" data-c="${o.w.c}" onclick="${GO}" onpointerup="if(event.pointerType==='touch')${GO}" title="Mergi la mesajul complet ANM"` : ''} style="${BGK(o.c, o.k)}border:1.5px solid ${CC[o.c]};border-radius:10px;padding:7px 10px;margin:8px 0${go ? ';cursor:pointer' : ''}">${head(o.c, o.nc, o.zone)}<div style="font-size:13px;margin-top:4px;${NW}">🕒 ${o.time}${NEW && o.w && blocks.length ? (go ? ` · 📄 Mesaj ${msgNo(o.w)}` : ' · fără text ANM') : ''}</div>${fenRows(o.f)}</div>`; };
  const ncEnd = (s) => { const m = String(s).match(/(\d{1,2}):(\d{2})/); if (!m) return null; const d = new Date(now); d.setHours(+m[1], +m[2], 0, 0); if (d < now - 36e5) d.setDate(d.getDate() + 1); return d; };
  const zn = (w) => w.loc ? `📍 ${w.loc}` : w.j;
  const tEnd = (e) => `${dl(e) === 'azi' ? 'până la' : 'până ' + dl(e) + ' la'} ${hm(e)}`;
  const tNext = (w) => `${dl(w.s)} ${hm(w.s)} → ${dl(w.e) === dl(w.s) ? '' : dl(w.e) + ' '}${hm(w.e)}`;

  // --- Corp: ACUM / URMEAZĂ ---
  let h = '';
  if (act.length || ncC >= 1) {
    h += H3('Acum');
    h += ncs.map(n => { const e = ncEnd(n.end); return item({ c: n.c, k: 'a', nc: true, zone: n.j, time: e ? tEnd(e) : 'acum', f: n.f }); }).join('');
    h += act.map(w => item({ c: w.c, k: 'a', zone: zn(w), time: tEnd(w.e), f: w.f, w })).join('');
  }
  if (nxt.length) { h += H3('Urmează'); h += nxt.map(w => item({ c: w.c, k: 'n', zone: zn(w), time: tNext(w), f: w.f, w })).join(''); }
  if (!act.length && ncC < 1 && !nxt.length) h += `<div style="font-size:13.5px;padding:6px 2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">✅ Fără avertizări acum sau în următoarele 48h</div>`;

  // --- Detalii ANM: mesajul complet + harta ---
  const msgHtml = blocks.map((b, i) => {
    const typ = (b.match(/(ATEN[ȚT]IONARE|AVERTIZARE|INFORMARE)\s+METEOROLOGIC[ĂA]/i) || [])[1] || 'Mesaj';
    const cm = b.match(/COD\s+(GALBEN|PORTOCALIU|RO[ȘS]U)/i);
    const cc = cm ? (/RO/i.test(cm[1]) ? 3 : /PORT/i.test(cm[1]) ? 2 : 1) : 0;
    const val = (re) => { const m = b.match(re); return m ? m[1].trim() : ''; };
    const iv = val(/^\s*Interval[^:\n]*:\s*([^\n]+)/im), fen = dec(val(/^\s*Fenomene[^:\n]*:\s*([^\n]+)/im)), zone = val(/^\s*Zone afectate:\s*([^\n]+)/im), nota = val(/^\s*Not[ăa]:\s*([^\n]+)/im);
    const body = b.split('\n').map(l => l.trim()).filter(l => l && !/^(ATEN[ȚT]IONARE|AVERTIZARE|INFORMARE|COD\s|Interval|Fenomene|Zone afectate|Not[ăa]:)/i.test(l)).join('<br><br>');
    const p = parseIv(iv);
    const mw = p ? wxc.find(w => Math.abs(w.s - p[0]) < 6e4 && Math.abs(w.e - p[1]) < 6e4) : null;
    const rel = !!mw;
    const kMsg = mw ? (act.indexOf(mw) >= 0 ? 'a' : nxt.indexOf(mw) >= 0 ? 'n' : '') : '';   // același fundal ca în rezumat
    const col = CC[cc] || '#888', mid = ids[i];
    const J = ANMJ ? ANMJ.nume : (SEL ? SEL.nume : '');
    const zr = rel ? `📍 Zona ta${mw.loc ? ' · ' + mw.loc : ''}` : `Nu afectează ${J}`;
    const ivS = p ? tNext({ s: p[0], e: p[1] }) : iv;
    const img = mid ? `<img loading="lazy" src="https://images.weserv.nl/?url=${encodeURIComponent('https://www.meteoromania.ro/wp-content/plugins/meteo/harti/harta.svg.php?id_avertizare=' + mid)}" style="width:100%;max-width:380px;display:block;margin:8px auto 2px;border-radius:8px">` : '';
    return `<div data-msg="1" data-s="${p ? p[0].getTime() : ''}" data-e="${p ? p[1].getTime() : ''}" data-c="${cc}" style="scroll-margin-top:90px;${BGK(cc, kMsg)}border:1.5px solid ${col};border-radius:10px;padding:7px 10px;margin:8px 0;${rel ? '' : 'opacity:.6'}">
      <div style="display:flex;align-items:center;gap:8px">${cc ? pill(cc) : '<b style="font-size:13px">MESAJ</b>'}<span style="flex:1;min-width:0;text-align:right;font-size:13px;font-weight:600;${NW}">${zr}</span></div>
      ${NEW && (kMsg || (p && p[1] <= now))
        ? `<div style="display:flex;align-items:center;gap:6px;font-size:12px;margin-top:4px;${NW}"><span style="background:${kMsg ? CC[cc] || '#888' : 'rgba(127,127,127,.35)'};color:${kMsg ? TX[cc] || '#fff' : 'var(--primary-text-color)'};padding:0 7px;border-radius:5px;font-weight:700;flex:none">${kMsg === 'a' ? 'ACUM' : kMsg === 'n' ? 'URMEAZĂ' : 'EXPIRAT'}</span><span style="opacity:.75;${NW}">${cap(typ.toLowerCase())} · Mesaj ${heads[i] || i + 1}</span></div>`
        : `<div style="font-size:12px;opacity:.75;margin-top:4px;${NW}">${cap(typ.toLowerCase())} · Mesaj ${heads[i] || i + 1}</div>`}
      ${ivS ? `<div style="font-size:13px;margin-top:3px">🕒 ${ivS}</div>` : ''}
      ${fen ? fenRows(fen) : ''}
      ${zone ? row('🗺️', zone) : ''}
      ${body ? `<div style="font-size:13px;line-height:1.45;margin-top:6px">${body}</div>` : ''}
      ${nota ? `<div style="font-size:13px;line-height:1.45;margin-top:6px"><b>Notă:</b> ${nota}</div>` : ''}
      ${img}</div>`;
  }).join('');
  let det = msgHtml ? H3('Informații ANM · mesaj complet') + msgHtml : '';
  if (act.length || ncC >= 1 || nxt.length || msgHtml) det += `<div style="margin-top:14px;padding-top:10px;border-top:1px solid var(--divider-color);text-align:center"><a href="https://www.meteoromania.ro/avertizari/" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()" style="pointer-events:auto;font-size:14px;font-weight:600;color:var(--primary-color);text-decoration:none">🔗 Avertizări pe meteoromania.ro (ANM)</a></div>`;
  
  // --- Antet pliabil: titlu, culoare și stare deschis/închis după avertizare ---
  const top = Math.max(act.length ? act[0].c : 0, ncC, nxt.length ? nxt[0].c : 0);
  const has = top >= 1;
  const status = has ? 'alerta' : 'liniste';
  const SK = 'alerte_meteo_ro_card' + (cfg && cfg.collapsed ? '_c' : ''); let open = cfg && cfg.collapsed ? false : has;                       // implicit: expandat cu avertizare, colapsat fără
  try {                                 // păstrează alegerea manuală cât timp starea nu se schimbă
    const st = JSON.parse(localStorage.getItem(SK) || 'null');
    if (st && st.status === status) open = !!st.open;
  } catch (e) {}
  const bg = has ? CC[top] : 'var(--secondary-background-color)';
  const fg = has ? TX[top] : 'var(--primary-text-color)';
  const title = has ? 'AVERTIZARE METEO ACTIVĂ' : 'NICIO AVERTIZARE METEO';
  const icon = has ? 'mdi:alert' : 'mdi:check-circle-outline';
  // --- Footer (jos de tot, mereu vizibil, și când cardul e colapsat) ---
  // Rândul 1: bulină API ANM (sensor.anm_api): verde = online, roșie cu fade = căzut, + sursa (API/XML) și cât de proaspete sunt datele.
  // Rândul 2: o informație utilă după situație: cât mai durează alerta, când începe următoarea sau „cod verde”.
  const apiE = S('sensor.anm_api'), apiS = apiE.state, apiA = apiE.attributes || {};
  let ftL1 = '';
  if (apiS === 'online' || apiS === 'offline') {
    const off = apiS === 'offline';
    let luD = null; try { if (apiA.ultima_reusita) { luD = new Date(apiA.ultima_reusita); if (isNaN(luD)) luD = null; } } catch (e) {}
    const ago = luD ? (now - luD < 6e4 ? 'chiar acum' : 'acum ' + rem(now - luD)) : '';
    // Două surse, fiecare cu bulina ei: ANM (API JSON) și XML (rezerva de pe site).
    // verde = online, roșu clipind = căzut, gri = încă neverificat. Dacă senzorul vechi nu are atributele json/xml, folosim starea generală.
    const stOf = (v, fb) => (v === 'online' ? 1 : v === 'offline' ? 0 : fb);
    const jOk = stOf(apiA.json, apiA.sursa === 'json' ? 1 : (off ? 0 : null));
    const xOk = stOf(apiA.xml, apiA.sursa === 'xml' ? 1 : (off ? 0 : null));
    const dot = (ok) => `<span style="flex:none;width:9px;height:9px;border-radius:50%;background:${ok === 1 ? '#2ecc71' : ok === 0 ? '#e53935' : '#9e9e9e'};box-shadow:0 0 0 2px var(--card-background-color,#fff),0 0 0 3px rgba(127,127,127,.5)${ok === 0 ? ';animation:amr-blink 1.4s ease-in-out infinite' : ''}"></span>`;
    // sursa folosită acum pentru date (sensor.anm_api › sursa): eticheta ei primește fundal colorat; cealaltă e estompată.
    // Când ambele sunt online, ANM (API) are prioritate; XML intră când API-ul nu răspunde.
    const used = off ? '' : (apiA.sursa === 'xml' ? 'xml' : apiA.sursa === 'json' ? 'json' : '');
    const src = (ok, lbl, tip, key) => { const on = used === key; return `<span title="${tip}${on ? ' · sursa folosită acum' : ''}" style="display:inline-flex;align-items:center;gap:5px;font-weight:${on ? 800 : 600};${on ? 'background:color-mix(in srgb, #2ecc71 24%, transparent);border-radius:6px;padding:1px 8px 1px 5px' : (used ? 'opacity:.6' : '')}">${dot(ok)}${lbl}</span>`; };
    const tJ = jOk === 1 ? 'API-ul ANM răspunde normal.' : jOk === 0 ? 'API-ul ANM (JSON) nu răspunde' + (apiA.cod_http && apiA.sursa !== 'xml' ? ' (HTTP ' + apiA.cod_http + ')' : '') + '.' : 'API-ul ANM: încă neverificat.';
    const tX = xOk === 1 ? 'Fluxul XML de pe meteoromania.ro răspunde' + (apiA.sursa === 'xml' ? ' și e sursa folosită acum.' : ' (rezervă disponibilă).') : xOk === 0 ? 'Fluxul XML de pe meteoromania.ro nu răspunde.' : 'Fluxul XML: încă neverificat (se verifică doar când API-ul ANM nu merge sau periodic).';
    // scurt: ora ultimei actualizări reușite (🕒 20:20); dacă ANM e căzut, adaugă „salvate” (date din cache)
    const tail = luD ? `🕒 ${dl(luD) === 'azi' ? '' : dl(luD) + ' '}${hm(luD)}${off ? ' · cache' : ''}` : (off ? 'fără date' : '');
    ftL1 = `<div style="display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:4px 14px">${src(jOk, 'API', tJ, 'json')}${src(xOk, 'XML', tX, 'xml')}${tail ? `<span style="opacity:.8;min-width:0;white-space:nowrap">${tail}</span>` : ''}</div>`;
  }
  let ftFact;
  if (act.length) {
    ftFact = '';   // avertizare activă: fără rând suplimentar (starea se vede deja în antet)
  } else if (ncC >= 1) {
    const e = ncEnd(ncs[0].end);
    ftFact = `⚡ Nowcasting cod ${CN[ncC]} activ${e ? ' până la <b>' + hm(e) + '</b>' : ''}`;
  } else if (nxt.length) {
    ftFact = `🕒 Următoarea avertizare (cod ${CN[nxt[0].c]}) începe în <b>${rem(nxt[0].s - now)}</b> (${dl(nxt[0].s)} ${hm(nxt[0].s)})`;
  } else {
    ftFact = '';   // cod verde: doar rândul API/XML + ora
  }
  const footerH = `<div style="display:flex;flex-direction:column;gap:3px;padding:7px 12px 8px;border-top:1px solid var(--divider-color);background:color-mix(in srgb, var(--primary-text-color) 4%, transparent);font-size:12px;line-height:1.35;text-align:center">${ftL1}${ftFact ? `<div style="opacity:.85;min-width:0;overflow-wrap:anywhere">${ftFact}</div>` : ''}</div>`;
  // Antet compact: un singur rând și pe telefon (text mic, fără text suplimentar;
  // codul culorii se vede din culoarea antetului și din pastilele din card).
  return `<style>.amr summary{list-style:none}.amr summary::-webkit-details-marker{display:none}.amr[open] .amr-chev{transform:rotate(180deg)}.amr-chev{transition:transform .2s}@keyframes amr-blink{50%{opacity:.35}}</style>
  <details class="amr" ${open ? 'open' : ''} ontoggle="try{localStorage.setItem('${SK}',JSON.stringify({status:'${status}',open:this.open}))}catch(e){}" style="text-align:left;pointer-events:auto">
    <summary style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:9px 12px;background:${bg};color:${fg};font-weight:800;font-size:12.5px;line-height:1.2;text-transform:uppercase;letter-spacing:.2px">
      <ha-icon icon="${icon}" style="--mdc-icon-size:20px;flex:none"></ha-icon>
      <span style="flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${title}</span>
      <ha-icon class="amr-chev" icon="mdi:chevron-down" style="--mdc-icon-size:20px;flex:none"></ha-icon>
    </summary>
    <div style="padding:6px 14px 14px">${h}${det}</div>
    ${footerH}
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
    const st = hass.states, ids = Object.keys(st).filter(k => k.startsWith('sensor.avertizari_meteo_anm') || k.startsWith('sensor.mesaj_meteo_') || k.startsWith('sensor.culoare_harta_') || k.startsWith('sensor.alerta_nowcasting_') || k === 'sensor.anm_avertizare_id' || k === 'sensor.anm_api');
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
  constructor() { super(); this._config = {}; }
  setConfig(config) { this._config = config || {}; this._render(); }
  set hass(hass) { this._hass = hass; this._render(); }
  _render() {
    if (!this._hass) return;
    const list = integCounties(this._hass.states);
    const key = list.map(j => j.cod).join(',');
    if (!this._form) {
      this._form = document.createElement('ha-form');
      this._form.computeLabel = (sc) => sc.label || sc.name;
      this._form.addEventListener('value-changed', (e) => {
        const v = e.detail.value || {};
        const all = integCounties(this._hass.states);
        const checked = all.filter(j => v[j.cod]).map(j => j.cod);
        const cfg = Object.assign({}, this._config); delete cfg.judet;
        if (checked.length && checked.length < all.length) cfg.judete = checked; else delete cfg.judete;
        this._config = cfg;
        this.dispatchEvent(new CustomEvent('config-changed', { detail: { config: cfg }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    const sel = [].concat(this._config.judete || this._config.judet || []).map(resolveJudet).filter(Boolean).map(j => j.cod);
    this._form.hass = this._hass;
    this._form.schema = list.map(j => ({ name: j.cod, label: j.nume, selector: { boolean: {} } }));
    const data = {}; list.forEach(j => { data[j.cod] = sel.length ? sel.includes(j.cod) : true; });
    this._form.data = data;
  }
}
if (!customElements.get('alerte-meteo-card-editor')) customElements.define('alerte-meteo-card-editor', AlerteMeteoCardEditor);
if (!customElements.get('alerte-meteo-card')) customElements.define('alerte-meteo-card', AlerteMeteoCard);
window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === 'alerte-meteo-card')) {
  window.customCards.push({ type: 'alerte-meteo-card', name: 'Alerte Meteo România', description: 'Avertizări ANM + nowcasting pentru județul ales în integrare (fără configurare).' });
}
