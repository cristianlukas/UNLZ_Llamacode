from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        route=self.path.split('?')[0]
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
