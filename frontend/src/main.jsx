import React, {useState, useEffect, useRef} from 'react';
import {createRoot} from 'react-dom/client';
import {ArrowUp, ArrowUpRight, BookOpen, Check, ChevronDown, Database, Globe2, History, Layers3, Link2, MessageSquare, Plus, Search, Settings2, ShieldCheck, Sparkles, X} from 'lucide-react';
import {request} from './api';
import {readConnection,saveConnection,pairConnection,createSessionBridge} from './connection';
import './style.css';
import {formatToday, websiteClock} from './clock';

const catalog = [
  {short:'FCA', name:'Financial Conduct Authority', url:'https://www.fca.org.uk/'},
  {short:'FCA', name:'FCA Handbook', url:'https://handbook.fca.org.uk/'},
  {short:'BoE', name:'Bank of England', url:'https://www.bankofengland.co.uk/'},
  {short:'PRA', name:'PRA publications', url:'https://www.bankofengland.co.uk/prudential-regulation'},
  {short:'PRA', name:'PRA Rulebook', url:'https://www.prarulebook.co.uk/'},
];
const suggestions = [
  {tag:'MODEL RISK', question:'What are the PRA expectations for model risk management?', icon:Layers3},
  {tag:'CUSTOMER OUTCOMES', question:'How does Consumer Duty apply to data-driven decisions?', icon:ShieldCheck},
  {tag:'OPERATIONAL RESILIENCE', question:'What should I check before using a third-party AI provider?', icon:Globe2},
];
function date(value) { return value ? new Date(value).toLocaleString('en-GB', {dateStyle:'medium', timeStyle:'short'}) : 'Not stated'; }
const downloadUrl = 'https://github.com/swk99/data-regulation-helpdesk-uk/releases/latest/download/RegulationHelpdesk.exe';
let initialConnection;
try { initialConnection=readConnection(window.location,window.history,window.sessionStorage); } catch(e) { initialConnection={error:e.message}; }
function App() {
 const [panel,setPanel]=useState('chat'), [settings,setSettings]=useState(false), [base,setBase]=useState(initialConnection.base||''), [token,setToken]=useState(initialConnection.token||'');
 const [connected,setConnected]=useState(false), [status,setStatus]=useState(null), [error,setError]=useState(initialConnection.error||''), [busy,setBusy]=useState(false), [connecting,setConnecting]=useState(Boolean(initialConnection.base));
 const connectionRef=useRef({...initialConnection,ready:false}), bridgeRef=useRef(null), attemptRef=useRef(false);
 const [question,setQuestion]=useState(''), [messages,setMessages]=useState([]);
 const [clockNow,setClockNow]=useState(Date.now()), [clockOffset,setClockOffset]=useState(0), [serverClock,setServerClock]=useState(false);
 useEffect(()=>{const id=setInterval(()=>setClockNow(Date.now()),1000);return ()=>clearInterval(id)},[]);
 useEffect(()=>{let active=true;async function sync(){try{let ms,source='website';if(connected){try{const time=await request(base,token,'/api/time');ms=Date.parse(time.server_time);source='backend';}catch{ms=undefined;}}if(!Number.isFinite(ms)){const response=await fetch(new URL(import.meta.env.BASE_URL+'index.html',window.location.href),{method:'HEAD',cache:'no-store',signal:AbortSignal.timeout(10000)});ms=websiteClock(response);source='website';}if(active){setClockOffset(ms-Date.now());setServerClock(source);}}catch{if(active){setServerClock(false);setClockOffset(0);}}}sync();const id=setInterval(sync,60000);return ()=>{active=false;clearInterval(id)}},[connected,base,token]);
 async function autoConnect() {
  if(attemptRef.current)return;attemptRef.current=true;setConnecting(true);setError('');
  try {
   let candidate=connectionRef.current;
   if(!candidate.base){
    candidate=await bridgeRef.current?.request()||{};
    if(!candidate.base)throw new Error('This tab has no connection yet. Use the GitHub tab opened by RegulationHelpdesk.exe. If it is closed, close the EXE window and reopen the EXE; no download is needed. Ollama running by itself is not enough.');
    connectionRef.current=candidate;setBase(candidate.base);
   }
   if(candidate.ticket){
    candidate.token=await pairConnection(candidate.base,candidate.ticket);delete candidate.ticket;
    saveConnection(window.sessionStorage,candidate.base,candidate.token);
   }
   setToken(candidate.token||'');
   const s=await request(candidate.base,candidate.token||'','/api/status',undefined,15000);
   candidate.ready=true;saveConnection(window.sessionStorage,candidate.base,candidate.token||'');
   setStatus(s);setConnected(true);setSettings(false);
  } catch(e) {
   connectionRef.current.ready=false;setConnected(false);
   setError(e instanceof TypeError||e.name==='TimeoutError'?'This tab could not reach the PC app. Keep RegulationHelpdesk.exe open, check that its console says "Helpdesk ready", and allow local device access for this site in your browser. Then retry.':e.message);
  } finally {attemptRef.current=false;setConnecting(false);}
 }
 useEffect(()=>{
  bridgeRef.current=createSessionBridge(()=>connectionRef.current.ready?connectionRef.current:null);
  autoConnect();return()=>bridgeRef.current?.close();
 },[]);

 async function ask(e) {e?.preventDefault();if(!question.trim()||busy)return;if(!connected){setSettings(true);return;}const q=question.trim();setQuestion('');setError('');setBusy(true);setMessages(old=>[...old,{role:'user',text:q}]);try {const answer=await request(base,token,'/api/chat',{question:q,live:true});setMessages(old=>[...old,{role:'assistant',answer}]);setStatus(await request(base,token,'/api/status'));}catch(e){setMessages(old=>[...old,{role:'error',text:e.message}]);}finally{setBusy(false);}}
 async function refresh(){if(!connected){setSettings(true);return;}setBusy(true);setError('');try{await request(base,token,'/api/update',{});setStatus(await request(base,token,'/api/status'));}catch(e){setError(e.message);}finally{setBusy(false);}}
 return <div className="app-shell">
  <aside className="sidebar">
   <a className="brand" href="#" onClick={e=>{e.preventDefault();setPanel('chat')}}><span className="brand-mark"><Layers3 size={23}/></span><span>regulation<span className="brand-second">helpdesk <span className="uk">UK</span></span></span></a>
   <button className="new-chat" disabled={busy} onClick={()=>{setMessages([]);setPanel('chat');setQuestion('')}}><Plus size={17}/> New research</button>
   <div className="nav-label">WORKSPACE</div>
   <nav><button className={panel==='chat'?'selected':''} onClick={()=>setPanel('chat')}><MessageSquare size={18}/> Research chat</button><button className={panel==='sources'?'selected':''} onClick={()=>setPanel('sources')}><BookOpen size={18}/> Source library <span className="count">5</span></button><button className={panel==='activity'?'selected':''} onClick={()=>setPanel('activity')}><History size={18}/> Index activity</button></nav>
   <div className="sidebar-note"><ShieldCheck size={19}/><strong>Evidence comes first.</strong><p>Official sources. Traceable references. Uncertainty made clear.</p></div>
   <div className="side-bottom"><button onClick={()=>setSettings(true)}><Settings2 size={17}/> Run on this PC <span className={'dot '+(connected?'green':'')}/></button><div className="profile"><span className="avatar">SK</span><div>Seonwoo’s workspace<small>Regulatory research</small></div></div></div>
  </aside>
  <div className="workspace">
   <header><div className="breadcrumb">Workspace <span>/</span> <strong>{panel==='chat'?'Research chat':panel==='sources'?'Source library':'Index activity'}</strong></div><button className={'connection '+(connected?'online':'')} onClick={()=>setSettings(true)}><span className={'dot '+(connected?'green':'')}/>{connected?'Local research ready':connecting?'Starting local session…':'Run on your PC'}<ArrowUpRight size={14}/></button></header>
   <div className="editor-tabs"><span className="editor-tab"><span className="file-symbol">{panel==='chat'?'PY':'MD'}</span>{panel==='chat'?'regulatory_research.py':panel==='sources'?'sources.md':'index_activity.log'}</span><span className="tab-note">UK regulation / research workspace</span></div>
   <main>
    {!connected&&<section className="launch-banner" aria-label="PC connection"><div><strong>{connecting?'Checking your PC connection…':'This browser tab is not connected yet'}</strong><p>{connecting?'Looking for a linked tab and checking the PC app.':'Already running? Use the tab opened by the EXE, or retry to connect through another linked tab in this browser. You do not need to download the app again.'}</p></div><button className="primary" disabled={connecting} onClick={autoConnect}>{connecting?'Checking…':'Retry connection'}</button></section>}


    {panel==='chat' && <>
     {!messages.length && <section className="welcome"><div className="eyebrow"><span/> UK REGULATORY INTELLIGENCE</div><h1>Clarity, backed by<br/><span>the source.</span></h1><p className="intro">Ask a regulatory question. Get a clear explanation,<br className="desktop"/> the supporting evidence, and what to check next.</p>
      <div className="source-pills"><span>FCA</span><span>FCA Handbook</span><span>Bank of England</span><span>PRA</span><span>PRA Rulebook</span></div>
      <div className="suggestion-head"><Sparkles size={15}/> A starting point for your research</div><div className="suggestions">{suggestions.map(({tag,question,icon:Icon})=><button key={tag} onClick={()=>setQuestion(question)}><Icon size={20}/><span className="tag">{tag}</span><p>{question}</p><ArrowUpRight className="card-arrow" size={17}/></button>)}</div>
     </section>}
     {!!messages.length && <section className="conversation" aria-live="polite">{messages.map((m,i)=>m.role==='user'?<div className="user-message" key={i}><span className="small-label">YOUR QUESTION</span><h2>{m.text}</h2></div>:m.role==='error'?<div role="alert" className="error" key={i}>{m.text}</div>:<Answer key={i} answer={m.answer}/>)}</section>}
     {busy&&<div className="working" role="status"><span className="pulse"/> Checking evidence. Live requests can take several minutes.</div>}
     <section className="composer-section"><form className="composer" onSubmit={ask}><div className="editor-input-label"><span>›_</span> research_query <small>Enter to run · Shift+Enter for a new line</small></div><label className="sr-only" htmlFor="question">Regulatory question</label><textarea id="question" value={question} maxLength={2000} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask();}}} placeholder="Ask about UK financial regulation…" rows="2"/><div className="composer-controls"><span className="live-toggle enabled" title="Every question requests a fresh source check using the backend’s current UK date."><Globe2 size={15}/>Always check as of today<Check size={13}/></span><span className="composer-hint">Public regulatory questions only</span><button className="send" type="submit" disabled={busy||!question.trim()} aria-label={connected?'Research question':'Connect backend to research'}><ArrowUp size={21}/></button></div></form><p className="footnote"><ShieldCheck size={13}/> Research support, not a legal determination. Always verify applicability and effective dates.</p></section>
    </>}
    {panel==='sources'&&<section className="library"><div className="eyebrow">YOUR EVIDENCE BASE</div><h1>Official sources.<br/><span>One workspace.</span></h1><p className="intro">Coverage and source availability are reported individually.</p>{catalog.map((s,i)=><a className="source-row" key={s.name} href={s.url} target="_blank" rel="noreferrer"><span className="source-logo">{s.short}</span><div><strong>{s.name}</strong><small>{s.url}</small></div><span className="source-state">{status?.sources?.find(x=>x.source===['fca','handbook','boe','pra','rulebook'][i])?.status||'Not checked'}</span><ArrowUpRight size={18}/></a>)}<p className="footnote">FCA Handbook may require JavaScript/API access. Unavailable sources are never treated as verified.</p></section>}
    {panel==='activity'&&<section className="library"><div className="eyebrow">INDEX HEALTH</div><h1>Know what’s<br/><span>behind the answer.</span></h1><div className="stats"><div><strong>{status?.documents??'—'}</strong><span>Indexed documents</span></div><div><strong>{status?.versions??'—'}</strong><span>Preserved versions</span></div></div><button className="primary" disabled={busy} onClick={refresh}><Database size={16}/>{busy?'Updating…':'Check for updates'}</button>{!status&&<p className="intro">Run RegulationHelpdesk.exe to inspect source checks and index activity.</p>}{status?.sources?.map(s=><div className="activity-row" key={s.source}><strong>{s.source.toUpperCase()} · {s.status}</strong><small>{date(s.checked)}</small><p>{s.detail}</p></div>)}</section>}
    {error&&!settings&&<div className="error" role="alert">{error}</div>}
   </main>
   <div className="today-date"><strong>Today is {formatToday(new Date(clockNow+clockOffset))}</strong><span>Europe/London · {serverClock==='backend'?'Backend clock synced · refreshed every minute':serverClock==='website'?'Website server clock · refreshed every minute':'Device clock · server time not verified'}</span></div>
   <footer><span><span className="tiny-square"/> INDEPENDENT RESEARCH TOOL</span><a href="https://github.com/swk99/data-regulation-helpdesk-uk" target="_blank" rel="noreferrer">View source code <ArrowUpRight size={13}/></a></footer>
  </div>
  {settings&&<div className="modal-backdrop" onClick={()=>setSettings(false)}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="connection-title" onClick={e=>e.stopPropagation()} onKeyDown={e=>{if(e.key==='Escape')setSettings(false)}}><button className="close" onClick={()=>setSettings(false)} aria-label="Close settings"><X size={20}/></button><div className="modal-icon"><Link2 size={25}/></div><h2 id="connection-title">{connected?'Running on your PC':connecting?'Checking connection…':'Connect the running app'}</h2>{connected?<p>Your PC app is connected. Models and the document index run on your PC.</p>:<><p>The app may already be running. This tab has not established a connection; this does not mean you need to reinstall it.</p><ol className="setup-steps"><li>Keep <strong>RegulationHelpdesk.exe</strong> open. Its console should say <strong>Helpdesk ready</strong>. Ollama alone does not start this app.</li><li>Use the GitHub tab the EXE opened. If another tab is connected in this browser, click Retry connection below.</li><li>If the browser blocked local device access, allow it for this site, then retry. If the original tab is closed, close the EXE window and reopen it.</li></ol>{error&&<div className="error" role="alert">{error}</div>}<button className="primary" disabled={connecting} onClick={autoConnect}>{connecting?'Checking…':'Retry connection'}</button><details className="first-install"><summary>First time here? Install the PC app</summary><p>Install Ollama once, then open RegulationHelpdesk.exe. Python is included. Missing models download on first use.</p><a className="primary" href={downloadUrl}>Download Windows .exe <ArrowUpRight size={16}/></a></details></>}<a className="setup-link" href="https://github.com/swk99/data-regulation-helpdesk-uk/blob/main/docs/local-windows.md" target="_blank" rel="noreferrer">Windows setup & troubleshooting ↗</a><p className="footnote">Chat here on GitHub Pages while the PC app runs. Model inference and indexed documents stay on your PC.</p></section></div>}

 </div>
}
function Answer({answer:a}) {return <article className="answer"><div className="answer-label"><span className="answer-icon"><Sparkles size={17}/></span>{a.mode==='welcome'?'Ready to research':a.mode==='grounded_summary'?'Evidence-led summary':'References to help you investigate'}<span className="answer-time">{date(a.answered_at)}</span></div><p className="assessment-date">Assessment date: {a.as_of_date||'Not supplied by backend'} · {a.timezone||'Europe/London'}<br/>{a.mode==='welcome'?'No regulatory check needed for this greeting.':a.freshness==='sources_rechecked'?'Sources rechecked for this request; legal applicability still requires evidence.':'Current applicability has not been verified.'}</p><p className="answer-intro">{a.message}</p>{a.claims.map((c,i)=><div className="claim" key={i}><p>{c.text} <a className="citation" href={a.sources.find(s=>s.citation===c.citation)?.url} target="_blank" rel="noreferrer">{c.citation}</a></p>{c.quote&&<details><summary>Supporting passage</summary><blockquote>{c.quote}</blockquote></details>}</div>)}{a.sources.length>0&&<><h3 className="evidence-title"><BookOpen size={16}/> Supporting sources</h3><div className="evidence-grid">{a.sources.map(s=><a key={s.citation} className="evidence" href={s.url} target="_blank" rel="noreferrer"><span className="evidence-meta">{s.citation} · {s.kind}</span><strong>{s.title}<ArrowUpRight size={14}/></strong><p>{s.section}{s.page?` · Page ${s.page}`:''}</p><small>Published: {s.published||'Not stated'}<br/>Checked: {date(s.checked)}</small></a>)}</div></>}{!a.sources.length&&<div className="official-links">{a.official_sources.map(s=><a key={s.name} href={s.url} target="_blank" rel="noreferrer">{s.name} ↗</a>)}</div>}<details className="research-notes"><summary>Research activity & limitations</summary><ul>{a.trace.map((t,i)=><li key={i}>{t}</li>)}</ul>{a.warnings.map((w,i)=><p key={i}>{w}</p>)}</details></article>}
createRoot(document.getElementById('root')).render(<App/>);
