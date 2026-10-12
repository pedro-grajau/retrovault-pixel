"""Facts about conversations; catalog search is not a recommendation."""
from contextvars import ContextVar
from uuid import uuid4
from psycopg.types.json import Jsonb
from .db import connect
from . import commerce

context=ContextVar('journey_context',default={'origin':'interface','message_id':None})

def conversation(db,sid):
    return db.execute('SELECT id FROM conversations WHERE session_id=%s',(sid,)).fetchone()

def receive(db,sid,text):
    db.execute('INSERT INTO conversations(id,session_id) VALUES (%s,%s) ON CONFLICT(session_id) DO NOTHING',(str(uuid4()),sid))
    cid=conversation(db,sid)['id']
    mid=str(uuid4())
    db.execute("INSERT INTO conversation_messages(id,conversation_id,role,content,status,created_at) VALUES (%s,%s,'user',%s,'received',now())",(mid,cid,text))
    return mid

def respond(db,sid,mid,reply):
    cid=conversation(db,sid)['id']
    db.execute("UPDATE conversation_messages SET status='responded' WHERE id=%s",(mid,))
    db.execute("INSERT INTO conversation_messages(id,conversation_id,role,content,status,created_at) VALUES (%s,%s,'assistant',%s,'responded',now())",(str(uuid4()),cid,reply))

def event(db,sid,kind,data=None,offer_id=None,order_id=None,status='complete',event_id=None):
    ctx=context.get()
    if ctx['origin']=='simulation': return
    c=conversation(db,sid)
    db.execute('''INSERT INTO journey_events(id,conversation_id,session_id,message_id,type,origin,status,offer_id,order_id,data)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING''',
        (event_id or str(uuid4()),c['id'] if c else None,sid,ctx.get('message_id'),kind,ctx['origin'],status,offer_id,order_id,Jsonb(data or {})))

def run(sid,origin,kind,operation,message_id=None):
    token=context.set({'origin':origin,'message_id':message_id})
    try:
        try:
            with connect() as db: return operation(db)
        except commerce.DomainError as error:
            with connect() as db:
                # Only record failures against known sessions, without leaking arguments.
                if db.execute('SELECT 1 FROM sessions WHERE id=%s',(sid,)).fetchone():
                    event(db,sid,kind,{'error':error.message},status='failed')
            raise
    finally: context.reset(token)

def recommend(db,sid,ids):
    if not ids or len(ids)>10 or any(type(i) is not int for i in ids):
        raise commerce.DomainError('Selecione até dez ofertas válidas.',422)
    from .catalog import catalog
    offers={r['id']:r for r in catalog(db,sid)}
    if any(i not in offers for i in ids): raise commerce.DomainError('Oferta indisponível.',404)
    for i in dict.fromkeys(ids):
        r=offers[i]
        event(db,sid,'recommendation',{'title':r['title'],'platform':r['platform']},offer_id=i,
              event_id=f"recommendation:{context.get().get('message_id') or uuid4()}:{i}")
    return {'recommended':[offers[i] for i in dict.fromkeys(ids)]}
