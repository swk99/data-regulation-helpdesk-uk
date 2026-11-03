from fastapi.testclient import TestClient
from reghelp.api import create_app
from reghelp.config import Settings
from reghelp.agent import Agent
from reghelp.models import Ollama


def test_korean_followup_uses_previous_evidence_without_search(tmp_path, monkeypatch):
    quote='This is a synthetic supporting passage for a test, not actual regulatory guidance.'
    async def original(self,question,live):
        return {'as_of_date':'2026-11-03','timezone':'Europe/London','server_time':'2026-11-03T12:00:00+00:00',
                'mode':'references_only','sources':[{'citation':'S1','text':quote,'title':'Test fixture','section':'Scope','url':'https://www.bankofengland.co.uk/'}],
                'trace':[],'warnings':[],'claims':[],'message':'test'}
    seen=[]
    async def generate(self,evidence,question,as_of=None):
        seen.append((evidence,question))
        return {'claims':[{'text':'이 자료는 테스트용 근거입니다.','evidence_id':'S1','quote':quote}]}
    monkeypatch.setattr(Agent,'answer',original)
    monkeypatch.setattr(Ollama,'generate',generate)
    with TestClient(create_app(Settings(data_dir=tmp_path,api_token='a'*32))) as client:
        headers={'Authorization':'Bearer '+'a'*32}
        first=client.post('/api/chat',json={'question':'Original credit union question'},headers=headers).json()
        async def forbidden(*args,**kwargs):raise AssertionError('Must not start new research')
        monkeypatch.setattr(Agent,'answer',forbidden)
        second=client.post('/api/chat',json={'question':'Can you translate above answer in Korean with summary?','previous_answer_id':first['answer_id']},headers=headers)
        assert second.status_code==200,second.text
        answer=second.json()
        assert answer['claims'][0]['text'].startswith('이 자료')
        assert answer['sources']==first['sources']
        assert 'Original credit union question' in seen[0][1]
        missing=client.post('/api/chat',json={'question':'한국어로 번역해줘'},headers=headers)
        assert missing.status_code==409
