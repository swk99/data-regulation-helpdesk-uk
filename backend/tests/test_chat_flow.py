"""Exercise the real chat, discovery, SQL, parsing and retrieval path.
Only external HTTP/Ollama responses are simulated; no agent/ingestor stubs.
"""
import secrets
from fastapi.testclient import TestClient
import pytest
from reghelp.api import create_app
from reghelp.config import Settings
from reghelp.models import Ollama
from reghelp.fetch import Fetcher, Download
from reghelp.storage import Store
from reghelp.parsing import Document, chunk


def test_candidate_query_handles_empty_and_existing_corpus(tmp_path):
    store=Store(tmp_path)
    assert store.candidates('Hello.', 'boe', 2)==[]
    old='https://www.bankofengland.co.uk/publication/old-model'
    new='https://www.bankofengland.co.uk/publication/new-model'
    other='https://www.prarulebook.co.uk/pra-rules/model'
    store.add_candidates([(old,'Model review'),(new,'Model review')],'boe')
    store.add_candidates([(other,'Model review')],'rulebook')
    doc=Document('Old model review',[{'section':'Scope','page':0,'text':'Model review test text.'}])
    store.save(Download(old,b'old','text/html'),doc,chunk(doc),'boe')
    assert [r['url'] for r in store.candidates('model','boe',2)]==[new,old]
    assert store.candidates('unrelated','boe',2)==[]


def test_chat_ingests_and_retrieves_document_with_real_sql(tmp_path,monkeypatch):
    seed='https://www.bankofengland.co.uk/rss/publications'
    doc_url='https://www.bankofengland.co.uk/publication/test-fixture-model-review'
    passage='This synthetic test fixture describes model review documentation and the evidence recorded when a model is reviewed. It is test data only, not a statement of actual regulatory requirements.'
    sources=tmp_path/'sources.yaml'
    sources.write_text(f'sources:\n  - id: boe\n    name: Bank of England\n    home: https://www.bankofengland.co.uk/\n    seeds: [{seed}]\n')
    async def fetch(self,url,*args,**kwargs):
        if url==seed:
            return Download(url,f'<rss><channel><item><title>Model review fixture</title><link>{doc_url}</link></item></channel></rss>'.encode(),'application/xml')
        assert url==doc_url
        return Download(url,f'<main><h1>Model review fixture</h1><h2>Review documentation</h2><p>{passage}</p></main>'.encode(),'text/html')
    async def embed(self,*args,**kwargs):raise RuntimeError('External model unavailable in test')
    async def generate(self,evidence,question,as_of=None):
        return {'claims':[{'text':'The fixture discusses recording model review evidence.', 'evidence_id':evidence[0]['citation'], 'quote':passage}]}
    monkeypatch.setattr(Fetcher,'get',fetch)
    monkeypatch.setattr(Ollama,'embed',embed)
    monkeypatch.setattr(Ollama,'generate',generate)
    token=secrets.token_urlsafe(32)
    settings=Settings(data_dir=tmp_path/'data',source_file=sources,api_token=token,request_delay=0)
    with TestClient(create_app(settings)) as client:
        headers={'Authorization':'Bearer '+token,'Origin':'https://swk99.github.io'}
        response=client.post('/api/chat',json={'question':'What does the model review document say?'},headers=headers)
        assert response.status_code==200,response.text
        result=response.json()
        assert result['mode']=='grounded_summary'
        assert result['sources'][0]['url']==doc_url
        assert result['sources'][0]['section']=='Review documentation'
        assert result['claims'][0]['quote']==passage
        assert result['freshness']=='sources_rechecked'
        # Recheck the same source: no duplicate document versions.
        assert client.post('/api/chat',json={'question':'What does the model review document say?'},headers=headers).status_code==200
        assert client.get('/api/status',headers=headers).json()['versions']==1


@pytest.mark.parametrize('greeting',['Hello.','Hi','안녕'])
def test_hello_returns_immediately_without_network_or_models(tmp_path,monkeypatch,greeting):
    async def forbidden(*args,**kwargs):raise AssertionError('Greeting must not crawl or load a model')
    monkeypatch.setattr(Fetcher,'get',forbidden)
    monkeypatch.setattr(Ollama,'embed',forbidden)
    token=secrets.token_urlsafe(32)
    with TestClient(create_app(Settings(data_dir=tmp_path,api_token=token))) as client:
        response=client.post('/api/chat',json={'question':greeting},headers={'Authorization':'Bearer '+token})
        assert response.status_code==200
        assert response.json()['mode']=='welcome'
        assert response.json()['sources']==[]


def test_unexpected_chat_error_is_readable_by_pages(tmp_path,monkeypatch):
    def broken(*args,**kwargs):raise RuntimeError('test internal failure')
    monkeypatch.setattr(Store,'lexical',broken)
    ui=tmp_path/'ui';ui.mkdir();(ui/'index.html').write_text('test')
    origin='https://swk99.github.io';token=secrets.token_urlsafe(32)
    app=create_app(Settings(data_dir=tmp_path/'data',api_token=token),local_origin='http://127.0.0.1:8123',launch_ticket=secrets.token_urlsafe(32),ui_dir=ui,pages_origin=origin)
    with TestClient(app,base_url='http://127.0.0.1:8123',raise_server_exceptions=False) as client:
        response=client.post('/api/chat',json={'question':'PRA model risk'},headers={'Origin':origin,'Authorization':'Bearer '+token})
        assert response.status_code==500
        assert response.headers['access-control-allow-origin']==origin
        assert response.headers['cache-control']=='no-store'
        assert response.json()['error_id'] in response.json()['detail']
        assert 'test internal failure' not in response.text
        denied=client.post('/api/chat',json={'question':'PRA model risk'},headers={'Origin':'https://evil.example','Authorization':'Bearer '+token})
        assert denied.status_code==403 and 'access-control-allow-origin' not in denied.headers
