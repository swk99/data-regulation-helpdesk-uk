"""Loopback-only browser session; no secret is embedded in the frontend bundle."""
import secrets
from urllib.parse import urlsplit
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

COOKIE = 'reghelp_local_session'


def install_local_session(app, origin, ticket, token, ui_dir):
    parsed = urlsplit(origin)
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not ticket:
        raise ValueError('Desktop sessions require an explicit IPv4 loopback origin and ticket')
    pending = ticket

    @app.middleware('http')
    async def local_boundary(request: Request, call_next):
        # Host check also prevents DNS rebinding. Cross-site requests cannot bootstrap
        # a session or use its cookies. Navigation from the launcher has no Origin.
        if request.headers.get('host') != parsed.netloc:
            return JSONResponse({'detail': 'Local host required'}, status_code=403)
        if request.headers.get('origin') not in (None, origin):
            return JSONResponse({'detail': 'Same-origin requests only'}, status_code=403)
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': 'Open the app using Start Helpdesk.cmd'}, status_code=403)
        response = await call_next(request)
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        if request.url.path.startswith(('/api/', '/local/')):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/local/start', include_in_schema=False)
    async def start(key: str = ''):
        nonlocal pending
        if not pending or not secrets.compare_digest(key, pending):
            raise HTTPException(401, 'Launch link expired. Close this app and run Start Helpdesk.cmd again.')
        pending = ''
        response = RedirectResponse('/', status_code=303)
        response.set_cookie(COOKIE, token, httponly=True, samesite='strict', path='/')
        return response

    app.mount('/', StaticFiles(directory=str(ui_dir), html=True), name='desktop')
