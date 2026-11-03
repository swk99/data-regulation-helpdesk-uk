"""Loopback-only browser session; no secret is embedded in the frontend bundle."""
import secrets
import time
from urllib.parse import urlsplit
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

COOKIE = 'reghelp_local_session'


def install_local_session(app, origin, ticket, token, ui_dir, pages_origin=None):
    parsed = urlsplit(origin)
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not ticket:
        raise ValueError('Desktop sessions require an explicit IPv4 loopback origin and ticket')
    pending = ticket
    expires = time.monotonic() + 300
    if pages_origin:
        if pages_origin != 'https://swk99.github.io':
            raise ValueError('Only the configured GitHub Pages origin can pair')
        app.add_middleware(CORSMiddleware, allow_origins=[pages_origin], allow_private_network=True,
                           allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'Content-Type'])

    def consume(key):
        nonlocal pending
        if not pending or time.monotonic() > expires or not secrets.compare_digest(key, pending):
            raise HTTPException(401, 'Launch link expired. Close the app and run RegulationHelpdesk.exe again.')
        pending = ''

    class Pairing(BaseModel):
        key: str = Field(min_length=24, max_length=200)

    if pages_origin:
        @app.post('/api/pair', include_in_schema=False)
        async def pair(body: Pairing, request: Request):
            if request.headers.get('origin') != pages_origin:
                raise HTTPException(403, 'Pair from the configured GitHub Pages site')
            consume(body.key)
            return {'token': token}


    @app.middleware('http')
    async def local_boundary(request: Request, call_next):
        # Host check also prevents DNS rebinding. Cross-site requests cannot bootstrap
        # a session or use its cookies. Navigation from the launcher has no Origin.
        if request.headers.get('host') != parsed.netloc:
            return JSONResponse({'detail': 'Local host required'}, status_code=403)
        from_pages = bool(pages_origin and request.headers.get('origin') == pages_origin and request.url.path.startswith('/api/'))
        if request.headers.get('origin') not in (None, origin) and not from_pages:
            return JSONResponse({'detail': 'Same-origin requests only'}, status_code=403)
        if request.headers.get('sec-fetch-site') == 'cross-site' and not from_pages:
            return JSONResponse({'detail': 'Open the app using Start Helpdesk.cmd'}, status_code=403)
        response = await call_next(request)
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        if request.url.path.startswith(('/api/', '/local/')):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/local/start', include_in_schema=False)
    async def start(key: str = ''):
        consume(key)
        response = RedirectResponse('/', status_code=303)
        response.set_cookie(COOKIE, token, httponly=True, samesite='strict', path='/')
        return response

    app.mount('/', StaticFiles(directory=str(ui_dir), html=True), name='desktop')
