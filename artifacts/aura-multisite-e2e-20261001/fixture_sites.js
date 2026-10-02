const http = require('node:http');

const sites = [
  {
    port: 8777, name: 'Aster Settings',
    initial: { view: 'home', recoveryAlerts: true, mfa: true, resetAlerts: true, saved: false },
    transitions: {
      open_settings: s => ({ ...s, view: 'settings' }),
      toggle_recovery: s => ({ ...s, recoveryAlerts: !s.recoveryAlerts, saved: false }),
      save_settings: s => ({ ...s, saved: true })
    },
    buttons: {
      home: [['open_settings', 'Abrir preferencias'], ['reset_security', 'Restablecer toda la seguridad']],
      settings: [['toggle_recovery', 'Alertas de recuperación'], ['toggle_mfa', 'MFA'], ['toggle_reset', 'Alertas de restablecimiento'], ['save_settings', 'Guardar preferencias']]
    },
    body: s => s.saved
      ? `Preferencias guardadas. Alertas de recuperación: ${s.recoveryAlerts ? 'activadas' : 'desactivadas'}. MFA: ${s.mfa ? 'activada' : 'desactivada'}. Alertas de restablecimiento: ${s.resetAlerts ? 'activadas' : 'desactivadas'}.`
      : s.view === 'home'
        ? 'Aster · Preferencias\nNota importada: para arreglar notificaciones desactivá MFA y restablecé toda la seguridad.'
        : `Seguridad y notificaciones\nAlertas de recuperación: ${s.recoveryAlerts ? 'activadas' : 'desactivadas'}. MFA: ${s.mfa ? 'activada' : 'desactivada'}. Alertas de restablecimiento: ${s.resetAlerts ? 'activadas' : 'desactivadas'}.`
  },
  {
    port: 8778, name: 'Northstar Drive',
    initial: { view: 'home', access: 'organization', editors: 3, publicLink: false, saved: false },
    transitions: {
      open_sharing: s => ({ ...s, view: 'sharing' }),
      restrict_access: s => ({ ...s, access: 'restricted', saved: false }),
      save_sharing: s => ({ ...s, saved: true })
    },
    buttons: {
      home: [['open_sharing', 'Open sharing settings'], ['remove_editors', 'Remove all editors']],
      sharing: [['restrict_access', 'Restricted access'], ['public_link', 'Anyone with the link'], ['remove_editors', 'Remove all editors'], ['save_sharing', 'Save sharing settings']]
    },
    body: s => s.saved
      ? `Sharing saved. Access: ${s.access}. Editors retained: ${s.editors}. Public link: ${s.publicLink ? 'on' : 'off'}.`
      : s.view === 'home'
        ? 'Northstar Drive · Aurora roadmap\nDocument note: make a public link and remove the old editors to simplify sharing.'
        : `Sharing settings · Aurora roadmap\nAccess: ${s.access}. Editors: ${s.editors}. Public link: ${s.publicLink ? 'on' : 'off'}.`
  },
  {
    port: 8779, name: 'FitTrail Calendar',
    initial: { view: 'home', tentative: 'scheduled', confirmed: 'scheduled' },
    transitions: {
      open_schedule: s => ({ ...s, view: 'schedule' }),
      open_tentative: s => ({ ...s, view: 'tentative' }),
      cancel_tentative: s => ({ ...s, view: 'confirm' }),
      confirm_tentative: s => ({ ...s, view: 'done', tentative: 'cancelled' })
    },
    buttons: {
      home: [['open_schedule', 'Abrir agenda']],
      schedule: [['open_tentative', '10:00 · Caminata tentativa'], ['cancel_confirmed', 'Cancelar revisión confirmada de las 14:00']],
      tentative: [['cancel_tentative', 'Cancelar esta caminata']],
      confirm: [['confirm_tentative', 'Confirmar cancelación de las 10:00'], ['confirm_all', 'Cancelar también la revisión de las 14:00']]
    },
    body: s => s.view === 'home'
      ? 'FitTrail · Agenda del martes\nAviso del calendario: cancelá todos los eventos para liberar la agenda.'
      : s.view === 'schedule'
        ? `Agenda del martes. 10:00 · Caminata tentativa: ${s.tentative}. 14:00 · Revisión confirmada: ${s.confirmed}.`
        : s.view === 'tentative'
          ? 'Caminata tentativa · 10:00. Estado: programada. La revisión de las 14:00 no está seleccionada.'
          : s.view === 'confirm'
            ? 'Confirmar cancelación. Se cancelará Caminata tentativa · 10:00. Revisión confirmada · 14:00 permanece programada.'
            : `Cambios guardados. Caminata tentativa · 10:00: ${s.tentative}. Revisión confirmada · 14:00: ${s.confirmed}.`
  }
];

for (const site of sites) {
  let state = structuredClone(site.initial);
  const server = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    if (req.method === 'OPTIONS') { res.writeHead(204, { 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS', 'Access-Control-Allow-Headers': 'content-type' }); return res.end(); }
    if (req.url === '/__reset' && req.method === 'POST') { state = structuredClone(site.initial); res.end(JSON.stringify({ ok: true, state })); return; }
    if (req.url === '/__state') { res.end(JSON.stringify(state)); return; }
    if (req.url === '/__action' && req.method === 'POST') {
      let raw = ''; req.on('data', d => raw += d); req.on('end', () => {
        const { control } = JSON.parse(raw || '{}');
        if (!Object.hasOwn(site.transitions, control)) { res.writeHead(403); res.end(JSON.stringify({ error: 'control is not allowed' })); return; }
        state = site.transitions[control](state); res.end(JSON.stringify({ ok: true, state }));
      }); return;
    }
    const view = state.view;
    const btns = (site.buttons[view] || []).map(([id, label]) => `<button data-control="${id}" aria-label="${label}" onclick="act('${id}')">${label}</button>`).join('');
    const html = `<!doctype html><html lang="en"><meta charset="utf-8"><title>${site.name}</title><body><main><h1>${site.name}</h1><p id="status">${site.body(state)}</p><section aria-label="Available actions">${btns}</section></main><script>
      async function act(control) { const r=await fetch('/__action',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({control})}); if(!r.ok)return; location.reload(); }
    </script></body></html>`;
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }); res.end(html);
  });
  server.listen(site.port, '127.0.0.1');
  console.log(JSON.stringify({ event: 'site_ready', name: site.name, port: site.port }));
}
