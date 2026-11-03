import asyncio
import contextlib
import logging
import os
import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .config import Settings
from .storage import Store
from .models import Ollama, Vectors
from .ingestion import Ingestor
from .agent import Agent
from .clock import clock_context

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    live: bool = False


def create_app(settings=None):
    s = settings or Settings()
    state = {}

    @asynccontextmanager
    async def lifespan(app):
        if len(s.api_token) < 24:
            raise RuntimeError('Set API_TOKEN to a random secret of at least 24 characters before starting the backend')
        store, models, vectors = Store(s.data_dir), Ollama(s), Vectors(s)
        ingestor = Ingestor(s, store, models, vectors)
        state.update(store=store, ingestor=ingestor, agent=Agent(store, models, vectors, ingestor), busy=asyncio.Lock())
        async def scheduled():
            interval = max(3600, int(os.getenv('UPDATE_INTERVAL_SECONDS', '21600')))
            while True:
                await asyncio.sleep(interval)
                try:
                    await ingestor.update()
                except Exception:
                    logging.exception('Scheduled update failed')
        task = asyncio.create_task(scheduled())
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            await ingestor.fetcher.close()

    app = FastAPI(title='UK Regulation Helpdesk', version='0.1.0', lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=s.origins, allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'Content-Type'])

    async def auth(authorization: str = Header(default='')):
        if not s.api_token or not secrets.compare_digest(authorization, 'Bearer ' + s.api_token):
            raise HTTPException(401, 'A valid backend access token is required')

    @app.get('/api/time')
    def current_time():
        from fastapi.responses import JSONResponse
        return JSONResponse(clock_context(), headers={'Cache-Control': 'no-store'})

    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': 'uk-regulation-helpdesk', 'version': '0.1.0'}

    @app.get('/api/status', dependencies=[Depends(auth)])
    def status():
        return {**clock_context(), **state['store'].status(), 'catalog': state['ingestor'].sources, 'updating': state['ingestor'].lock.locked()}

    @app.post('/api/chat', dependencies=[Depends(auth)])
    async def chat(body: Question):
        if not body.question.strip():
            raise HTTPException(422, 'Please enter a question')
        if state['busy'].locked():
            raise HTTPException(429, 'Another research request is running; please try again shortly')
        async with state['busy']:
            try:
                return await asyncio.wait_for(state['agent'].answer(body.question, True), timeout=540)
            except TimeoutError:
                raise HTTPException(504, 'Research timed out. Indexed evidence is retained; retry without live check.')

    @app.post('/api/update', dependencies=[Depends(auth)])
    async def update():
        return {'trace': await state['ingestor'].update()}

    @app.get('/api/versions', dependencies=[Depends(auth)])
    def versions(url: str):
        return {'versions': state['store'].history(url)}

    return app


app = create_app()
