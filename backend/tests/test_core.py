import asyncio
from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient
from reghelp.config import Settings
from reghelp.fetch import canonical, Fetcher, Download
from reghelp.parsing import parse, chunk, Document, links_from
from reghelp.storage import Store
from reghelp.agent import validated_claims, Agent
from reghelp.api import create_app
from reghelp.models import Vectors


def document(text='A firm must review the model annually. ' * 20):
    return Document('Test document', [{'section':'Model review', 'page':0, 'text':text}])


@pytest.mark.parametrize('url', ['http://www.fca.org.uk/a', 'https://evil.com/', 'https://www.fca.org.uk.evil.com/', 'https://user@www.fca.org.uk/', 'https://www.fca.org.uk:444/a', 'file:///etc/passwd'])
def test_unapproved_urls_rejected(url):
    with pytest.raises(ValueError): canonical(url)


def test_canonical_preserves_version_query():
    assert canonical('https://handbook.fca.org.uk/abc?date=2020-01-01#x').endswith('?date=2020-01-01')


@pytest.mark.asyncio
async def test_robots_wildcards_and_redirect_policy(tmp_path):
    calls=[]
    def handler(request):
        calls.append(str(request.url))
        if request.url.path == '/robots.txt': return httpx.Response(200,text='User-agent: *\nDisallow: /*?\n')
        return httpx.Response(302,headers={'location':'https://evil.com/private'})
    client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    f=Fetcher(Settings(data_dir=tmp_path, request_delay=0),client)
    with pytest.raises(ValueError,match='robots'): await f.get('https://www.fca.org.uk/a?x=1')
    with pytest.raises(ValueError,match='approved'): await f.get('https://www.fca.org.uk/a')
    assert not any('evil' in c for c in calls)
    await f.close()


@pytest.mark.asyncio
async def test_robots_fail_closed(tmp_path):
    client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(503)))
    f=Fetcher(Settings(data_dir=tmp_path, request_delay=0),client)
    with pytest.raises(ValueError,match='Robots policy'): await f.get('https://www.fca.org.uk/a')
    await f.close()


def test_parse_preserves_heading_date_table():
    html=b'<html><head><title>Example</title><meta property="article:published_time" content="2024-01-01"></head><body><nav>Ignore navigation</nav><main><h1>Consultation</h1><h2>Scope</h2><p>'+b'Proposed approach. '*20+b'</p><table><tr><th>Type</th><th>Value</th></tr><tr><td>A</td><td>10</td></tr></table></main></body></html>'
    doc=parse(Download('https://www.fca.org.uk/publications/consultation',html,'text/html'))
    assert doc.published=='2024-01-01'
    assert doc.kind=='Consultation'
    assert doc.sections[0]['section']=='Scope'
    assert 'A | 10' in doc.sections[0]['text']
    assert 'Ignore navigation' not in doc.sections[0]['text']


def test_chunk_size_and_no_lost_text():
    doc=document('x'*5000)
    chunks=chunk(doc)
    assert all(len(c['text'])<=1600 for c in chunks)
    assert sum(len(c['text']) for c in chunks)==5000


def test_xml_discovery_ignores_external():
    links=links_from(b'<rss><channel><item><title>Policy</title><link>https://www.bankofengland.co.uk/publication/example</link></item><item><link>https://evil.com</link></item></channel></rss>', 'https://www.bankofengland.co.uk/', True)
    assert links==[('https://www.bankofengland.co.uk/publication/example','Policy')]


def test_versions_dedup_and_active_search(tmp_path):
    s=Store(tmp_path);doc=document();url='https://www.fca.org.uk/publications/test'
    d=Download(url,b'one','text/html')
    first=s.save(d,doc,chunk(doc),'fca');s.save(d,doc,chunk(doc),'fca')
    assert s.status()['versions']==1
    newer=document('Replacement guidance. '*20)
    second=s.save(Download(url,b'two','text/html'),newer,chunk(newer),'fca')
    assert first!=second and s.status()['documents']==1 and s.status()['versions']==2
    assert s.lexical('annually')==[]
    assert s.lexical('Replacement')
    assert len(s.history(url))==2
    # Content can revert without duplicate rows or inactive retrieval.
    s.save(d,doc,chunk(doc),'fca')
    assert s.active(url)['id']==first and s.status()['versions']==2


def test_reject_fabricated_citations_quotes_and_references():
    evidence=[{'citation':'S1','text':'A firm must review the model annually.', 'title':'Model review','section':'Scope'}]
    claim={'text':'Review the model annually.', 'quote':'must review the model annually.', 'evidence_id':'S1'}
    assert len(validated_claims({'claims':[claim]},evidence))==1
    for invalid in [{**claim,'evidence_id':'S9'},{**claim,'quote':'must validate every week.'},{**claim,'text':'SS99/88 requires review.'}]:
        assert validated_claims({'claims':[invalid]},evidence)==[]


def test_authentication_and_cors(tmp_path):
    s=Settings(data_dir=tmp_path,api_token='a'*32)
    with TestClient(create_app(s)) as client:
        assert client.get('/health').status_code==200
        assert client.get('/api/status').status_code==401
        assert client.get('/api/status',headers={'Authorization':'Bearer '+'a'*32}).status_code==200
        r=client.options('/api/chat',headers={'Origin':'https://evil.com','Access-Control-Request-Method':'POST'})
        assert 'access-control-allow-origin' not in r.headers
        assert client.post('/api/chat',json={'question':'  '},headers={'Authorization':'Bearer '+'a'*32}).status_code==422


def test_vector_persistence_and_model_separation(tmp_path):
    s=Settings(data_dir=tmp_path)
    v=Vectors(s);v.upsert([{'id':'test','url':'https://www.fca.org.uk/','version':'v1'}],[[1.,0.,0.]])
    assert Vectors(s).search([1.,0.,0.])==['test']
    assert Vectors(Settings(data_dir=tmp_path,embedding_model='bge-m3')).search([1.,0.,0.])==[]


@pytest.mark.asyncio
async def test_empty_corpus_never_invents_answer(tmp_path):
    class Unavailable:
        async def embed(self,*args,**kwargs): raise RuntimeError('offline')
    class Ingestor:
        sources=[{'name':'FCA','home':'https://www.fca.org.uk/'}]
    result=await Agent(Store(tmp_path),Unavailable(),None,Ingestor()).answer('What must a bank do?')
    assert result['mode']=='references_only'
    assert result['claims']==[] and result['sources']==[]
    assert result['official_sources']

@pytest.mark.asyncio
async def test_permission_gate_applies_to_cross_source_links(tmp_path,monkeypatch):
    from reghelp.ingestion import Ingestor
    monkeypatch.delenv('FCA_RETRIEVAL_PERMISSION',raising=False)
    ingest=Ingestor(Settings(data_dir=tmp_path),Store(tmp_path),None,None)
    try:
        with pytest.raises(ValueError,match='permission'):
            await ingest.ingest('https://www.fca.org.uk/publications/test','pra')
    finally:
        await ingest.fetcher.close()


@pytest.mark.asyncio
async def test_ingestion_to_answer_with_mocked_official_document(tmp_path):
    from reghelp.ingestion import Ingestor
    class Model:
        async def embed(self,texts,query=False): return [[1.,0.,0.] for _ in texts]
        async def generate(self,evidence,question,as_of=None):
            return {'claims':[{'text':'The publication describes annual model review.', 'evidence_id':'S1',
                               'quote':'This publication describes annual model review.'}]}
    s=Settings(data_dir=tmp_path,request_delay=0)
    store,model,vectors=Store(tmp_path),Model(),Vectors(s)
    ingestor=Ingestor(s,store,model,vectors)
    await ingestor.fetcher.close()
    html='<main><h1>Model review guidance</h1><h2>Review frequency</h2><p>'+'This publication describes annual model review. '*10+'</p></main>'
    def handler(r):
        return httpx.Response(200,text='User-agent: *\nAllow: /' if r.url.path=='/robots.txt' else html,
                              headers={'Content-Type':'text/plain' if r.url.path=='/robots.txt' else 'text/html'})
    ingestor.fetcher=Fetcher(s,httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        await ingestor.ingest('https://www.bankofengland.co.uk/publication/test','boe')
        await ingestor.ingest('https://www.bankofengland.co.uk/publication/test','boe')
        assert store.status()['versions']==1
        answer=await Agent(store,model,vectors,ingestor).answer('annual model review')
        assert answer['mode']=='grounded_summary'
        assert answer['claims'][0]['citation']=='S1'
        assert answer['sources'][0]['section']=='Review frequency'
        assert answer['sources'][0]['kind']=='Guidance'
    finally:
        await ingestor.fetcher.close()


def test_server_clock_and_freshness(tmp_path):
    from reghelp.clock import checked_since
    assert checked_since('2026-11-03T10:00:00+00:00','2026-11-03T09:00:00+00:00')
    assert not checked_since('2026-11-02T10:00:00+00:00','2026-11-03T09:00:00+00:00')
    assert not checked_since('2026-11-03T10:00:00','2026-11-03T09:00:00+00:00')
    with TestClient(create_app(Settings(data_dir=tmp_path,api_token='a'*32))) as client:
        r=client.get('/api/time')
        assert r.headers['cache-control']=='no-store'
        assert r.json()['timezone']=='Europe/London'
        assert len(r.json()['as_of_date'])==10


def test_web_chat_cannot_disable_today_check(tmp_path,monkeypatch):
    calls=[]
    async def answer(self,question,live=False):
        calls.append(live)
        return {'mode':'references_only'}
    monkeypatch.setattr(Agent,'answer',answer)
    with TestClient(create_app(Settings(data_dir=tmp_path,api_token='a'*32))) as client:
        r=client.post('/api/chat',json={'question':'Does this apply today?','live':False},headers={'Authorization':'Bearer '+'a'*32})
        assert r.status_code==200 and calls==[True]


@pytest.mark.asyncio
async def test_stale_evidence_cannot_become_a_current_summary(monkeypatch):
    import reghelp.agent as module
    row={'url':'https://www.bankofengland.co.uk/test','source':'boe','title':'Test', 'section':'Scope',
         'page':0,'text':'This evidence was retrieved in the past.', 'kind':'Guidance','reference':'',
         'published':'','checked':'2020-01-01T00:00:00+00:00','hash':'abc'}
    async def search(*args):return [row],[]
    monkeypatch.setattr(module,'retrieve',search)
    class Ingest:
        sources=[]
        async def update(self,*args):return ['Source unavailable']
    class Model:
        async def generate(self,*args,**kwargs):raise AssertionError('Stale evidence must not generate a current summary')
    response=await Agent(None,Model(),None,Ingest()).answer('Does this apply today?',True)
    assert response['mode']=='references_only'
    assert response['freshness']=='current_status_unverified'
    assert response['as_of_date'] in response['message']
