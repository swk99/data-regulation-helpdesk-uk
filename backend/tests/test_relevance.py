import pytest
from reghelp.query import plan_query, rank_passage
from reghelp.storage import Store, PARSER_VERSION
from reghelp.parsing import Document, chunk, current_publication_links
from reghelp.fetch import Download
from reghelp.retrieval import retrieve

QUESTION="Hi I'm working in a UK's credit union in london(It's authorised) Could you tell me if we can open a new fintech compnay with parent company or daughter company?"


def row(text,section='18.2',title='SS2/23 Supervising credit unions',url='https://www.bankofengland.co.uk/supervisory-statement/test'):
    return {'text':text,'section':section,'title':title,'url':url,'kind':'Supervisory statement'}


def test_plan_preserves_tail_and_expands_ownership_with_region():
    p=plan_query(QUESTION)
    assert p.jurisdiction=='Great Britain' and p.institution=='credit_union'
    assert p.intent=='ownership_structure'
    assert 'subsidiary' in p.terms and 'holding company' in p.terms
    assert 'daughter' in p.terms  # beyond the previous 30-word boundary
    assert len(p.clarification)==2
    assert plan_query('Northern Ireland credit union subsidiary').jurisdiction=='Northern Ireland'
    assert plan_query('Compare London and Northern Ireland credit union subsidiaries').jurisdiction=='UK / cross-jurisdiction'


def test_rejects_report_boilerplate_wrong_jurisdiction_and_bond_passage():
    p=plan_query(QUESTION)
    distractors=[row('Credit unions responded to this consultation.','Your personal information'),
                 row('Credit unions and subsidiaries in Northern Ireland.','Overview','Northern Ireland Credit Unions consultation'),
                 row('Financial services AI survey companies responded.','1.2 Methodology','AI in financial services'),
                 row('Credit unions may hold bonds as investments.','Investment','Credit Unions'),
                 row('CUSO and subsidiaries 25 26 27','Contents 3')]
    assert all(rank_passage(r,p)[0]==0 for r in distractors)
    assert rank_passage(row('Synthetic fixture: Great Britain credit unions must assess subsidiary ownership and controlling interests.'),p)[0]>0
    # Privacy questions must still be able to retrieve privacy provisions.
    assert rank_passage(row('Personal data privacy rules for credit unions.','Privacy notice'),plan_query('Credit union personal data privacy'))[0]>0


@pytest.mark.asyncio
async def test_real_index_retrieves_cuso_passage_and_excludes_noise_without_embeddings(tmp_path):
    store=Store(tmp_path)
    fixtures=[('good','18.2','SS2/23 Supervising credit unions','Synthetic fixture: Credit unions in Great Britain must assess subsidiary ownership and a controlling interest in a CUSO.'),
              ('noise','Your personal information','PRA consultation','Credit unions and subsidiaries: personal information and consent for responses.'),
              ('ni','Overview','Northern Ireland Credit Unions consultation','Credit unions and subsidiaries in Northern Ireland consultation.'),
              ('bonds','Investment','Credit Unions','Credit unions may hold investments in corporate company bonds.')]
    for suffix,section,title,text in fixtures:
        doc=Document(title,[{'section':section,'page':0,'text':text}])
        store.save(Download('https://www.bankofengland.co.uk/publication/'+suffix,suffix.encode(),'text/html'),doc,chunk(doc),'pra')
    class Offline:
        async def embed(self,*args,**kwargs):raise RuntimeError('offline fixture')
    selected,warnings=await retrieve(QUESTION,store,Offline(),None)
    assert len(selected)==1 and selected[0]['section']=='18.2'
    assert any('Excluded' in warning for warning in warnings)
    # An unsupported topic is not padded with marginal source excerpts.
    empty,_=await retrieve('What are mortgage affordability requirements?',store,Offline(),None)
    assert empty==[]


def test_current_pdf_discovery_excludes_past_version():
    html=b'<h1>SS2/23 Supervising credit unions</h1><h2>Current version</h2><ul><li><a href="/current.pdf">PDF</a></li></ul><h2>Past version</h2><a href="/old.pdf">Old PDF</a>'
    result=current_publication_links(html,'https://www.bankofengland.co.uk/publication/test')
    assert len(result)==1 and result[0][0].endswith('/current.pdf')
    assert 'credit unions' in result[0][1]


def test_existing_version_is_reparsed_without_duplicate_document(tmp_path):
    store=Store(tmp_path);url='https://www.bankofengland.co.uk/publication/test'
    doc=Document('Test',[{'section':'Old section','page':1,'text':'Old passage.'}])
    download=Download(url,b'unchanged source','text/html')
    version=store.save(download,doc,chunk(doc),'pra')
    with store.connect() as db:db.execute('UPDATE versions SET parser_version=0,vector_model=?',('old-model',))
    updated=Document('Test',[{'section':'Paragraph 18.2','page':1,'text':'New structured passage.'}])
    assert store.save(download,updated,chunk(updated),'pra')==version
    assert store.status()['versions']==1
    assert store.rows(version=version)[0]['section']=='Paragraph 18.2'
    assert store.active(url)['parser_version']==PARSER_VERSION
    assert store.active(url)['vector_model']==''


@pytest.mark.asyncio
async def test_model_diagnostic_distinguishes_http_and_json_failures(tmp_path):
    import httpx
    import respx
    from reghelp.models import Ollama,GenerationError
    from reghelp.config import Settings
    models=Ollama(Settings(data_dir=tmp_path))
    url='http://127.0.0.1:11434/api/chat'
    with respx.mock as mock:
        route=mock.post(url).mock(return_value=httpx.Response(404,json={'error':'model missing'}))
        with pytest.raises(GenerationError,match='ollama_http_404'):await models.generate([], 'test')
        route.mock(return_value=httpx.Response(200,json={'message':{'content':'not JSON'}}))
        with pytest.raises(GenerationError,match='invalid_model_json'):await models.generate([], 'test')
        route.mock(side_effect=httpx.ReadTimeout('test'))
        with pytest.raises(GenerationError,match='ollama_timeout'):await models.generate([], 'test')
