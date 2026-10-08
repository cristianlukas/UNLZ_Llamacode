from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        route=self.path.split('?')[0]
        if route == '/vision-observation':
            body='''<!doctype html><meta charset="utf-8"><title>Visual Check</title>
<style>body{font:20px sans-serif;background:#f3f6fb;margin:48px}main{background:white;padding:32px;max-width:720px;border-radius:16px}button{background:rgb(20,96,220);color:white;border:0;border-radius:8px;padding:16px 28px;font-size:20px}</style>
<main><h1>Visual Check</h1><p>Use the primary action to continue.</p><button id="continue">Continue</button></main>'''.encode()
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
        if route == '/plans':
            body='''<!doctype html><meta charset="utf-8"><title>Atlas Plans</title>
<main><h1>Atlas Workbench plans</h1><p>Compare current subscription options. No changes are pending.</p>
<section aria-labelledby="starter"><h2 id="starter">Starter Monthly</h2><p>$12.00 per month</p><p>Renews October 14, 2026</p></section>
<section aria-labelledby="studio"><h2 id="studio">Studio Pro Annual</h2><p>$89.00 per year</p><p>Renews November 2, 2026</p></section>
<section aria-labelledby="lifetime"><h2 id="lifetime">Lifetime</h2><p>$249.00 one time</p><p>No renewal</p></section></main>'''.encode()
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
        name={'/northstar':'Northstar Audio — Plus Music monthly renews Oct 14.','/cloudbox':'CloudBox — Storage Plus annual plan renews Nov 2.','/fittrail':'FitTrail — TrailPlus Annual paid plan renews Oct 20.'}.get(route)
        if not name: self.send_error(404); return
        body=f'''<!doctype html><meta charset="utf-8"><title>{name.split(' — ')[0]}</title><main data-site="{route[1:]}"><h1>{name}</h1><p id="status">Auto-renew is on. Your account, files, purchases and training data are separate.</p><button id="manage">Manage plan</button></main><script>
const s=document.querySelector('#status'), b=document.querySelector('main');
document.querySelector('#manage').onclick=()=>{{s.textContent='Manage paid recurring plan. Access remains through the paid term.';b.insertAdjacentHTML('beforeend','<button id="cancel">Cancel renewal</button>')}};
b.addEventListener('click',e=>{{if(e.target.id==='cancel'){{s.textContent='Confirm cancellation of the paid plan only.';b.insertAdjacentHTML('beforeend','<button id="confirm">Confirm cancellation</button>')}}if(e.target.id==='confirm'){{s.textContent='Cancellation confirmed. Auto-renew is off. Account, files, purchases and free plan remain.';e.target.remove();document.querySelector('#cancel').remove()}}}});
</script>'''.encode()
        self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*a): pass
HTTPServer(('127.0.0.1',8777),H).serve_forever()
