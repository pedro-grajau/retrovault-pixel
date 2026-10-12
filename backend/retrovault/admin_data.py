"""Administrative aggregates over frozen commercial facts."""
from datetime import date,datetime,time,timedelta
from zoneinfo import ZoneInfo
from . import commerce

PAGE_SIZE=20

def bounds(start='',end=''):
    try:
        tz=ZoneInfo('America/Fortaleza')
        a=datetime.combine(date.fromisoformat(start),time.min,tz) if start else None
        b=datetime.combine(date.fromisoformat(end)+timedelta(days=1),time.min,tz) if end else None
        if a and b and a>=b: raise ValueError()
        return a,b
    except ValueError: raise commerce.DomainError('Período inválido.',422)

def filters(start='',end='',platform='',actor='',origin=''):
    if actor not in {'','visitor','simulation'} or origin not in {'','pixel','interface','legacy','simulation'}:
        raise commerce.DomainError('Filtro inválido.',422)
    a,b=bounds(start,end)
    return a,b,platform,actor,origin

def commercial(db,start='',end='',platform='',actor='',origin='',page=0):
    a,b,platform,actor,origin=filters(start,end,platform,actor,origin)
    where='(%s::timestamptz IS NULL OR o.created_at>=%s) AND (%s::timestamptz IS NULL OR o.created_at<%s) AND (%s=\'\' OR o.actor=%s) AND (%s=\'\' OR o.origin=%s)'
    params=(a,a,b,b,actor,actor,origin,origin)
    # One row per frozen item; never join rentals into revenue aggregates.
    cte=f'''WITH selected AS (SELECT o.*,i.value AS item FROM orders o CROSS JOIN LATERAL jsonb_array_elements(o.items) i WHERE {where} AND (%s='' OR i.value->>'platform'=%s))'''
    args=params+(platform,platform)
    stats=db.execute(cte+''' SELECT COALESCE(sum((item->>'quantity')::int) FILTER(WHERE item->>'mode'='sale'),0) AS units_sold,
        COALESCE(sum((item->>'subtotal')::bigint) FILTER(WHERE item->>'mode'='sale'),0) AS sale_revenue,
        COALESCE(sum((item->>'subtotal')::bigint) FILTER(WHERE item->>'mode'='rental'),0) AS rental_revenue,
        COALESCE(sum((item->>'subtotal')::bigint),0) AS total_revenue FROM selected''',args).fetchone()
    top=db.execute(cte+''' SELECT item->>'title' title,item->>'platform' platform,sum((item->>'quantity')::int) quantity
        FROM selected WHERE item->>'mode'='sale' GROUP BY item->>'offer_id',item->>'title',item->>'platform' ORDER BY quantity DESC,title LIMIT 10''',args).fetchall()
    rows=db.execute(cte+''' SELECT id,session_id,actor,origin,created_at,jsonb_agg(item) items,sum((item->>'subtotal')::bigint) total
        FROM selected GROUP BY id,session_id,actor,origin,created_at ORDER BY created_at DESC,id LIMIT %s OFFSET %s''',args+(PAGE_SIZE,page*PAGE_SIZE)).fetchall()
    count=db.execute(cte+' SELECT count(DISTINCT id) n FROM selected',args).fetchone()['n']
    rentals=db.execute(f'''SELECT r.id,r.order_id,o.session_id,s.customer,o.created_at started_at,r.due_at,r.returned_at,g.title,f.platform,
        CASE WHEN r.returned_at IS NOT NULL THEN 'returned' WHEN r.due_at<now() THEN 'overdue' ELSE 'open' END status
        FROM rentals r JOIN orders o ON o.id=r.order_id JOIN sessions s ON s.id=o.session_id
        JOIN rental_copies rc ON rc.id=r.copy_id JOIN offers f ON f.id=rc.offer_id JOIN games g ON g.id=f.game_id
        WHERE {where} AND (%s='' OR f.platform=%s) ORDER BY o.created_at DESC,r.id LIMIT %s OFFSET %s''',args+(PAGE_SIZE,page*PAGE_SIZE)).fetchall()
    rental_count=db.execute(f'''SELECT count(*) n FROM rentals r JOIN orders o ON o.id=r.order_id
        JOIN rental_copies rc ON rc.id=r.copy_id JOIN offers f ON f.id=rc.offer_id
        WHERE {where} AND (%s='' OR f.platform=%s)''',args).fetchone()['n']
    return {'stats':stats,'top':top,'orders':rows,'order_count':count,'rentals':rentals,'rental_count':rental_count,'page':page,'page_size':PAGE_SIZE}

def conversations(db,start='',end='',page=0):
    a,b=bounds(start,end)
    cte='''WITH cohort AS (SELECT c.*,s.customer FROM conversations c JOIN sessions s ON s.id=c.session_id
        WHERE (%s::timestamptz IS NULL OR c.started_at>=%s) AND (%s::timestamptz IS NULL OR c.started_at<%s)), stages AS (
        SELECT c.*, EXISTS(SELECT 1 FROM journey_events e WHERE e.conversation_id=c.id AND e.status='complete' AND e.type='recommendation') recommended,
        EXISTS(SELECT 1 FROM journey_events e WHERE e.conversation_id=c.id AND e.status='complete' AND e.type='cart' AND (e.data->>'quantity')::int>0) cart,
        EXISTS(SELECT 1 FROM journey_events e WHERE e.conversation_id=c.id AND e.status='complete' AND e.type='order' AND e.origin!='simulation') ordered
        FROM cohort c)'''
    args=(a,a,b,b)
    stats=db.execute(cte+''' SELECT count(*) conversations,count(*) FILTER(WHERE recommended) recommended,
        count(*) FILTER(WHERE cart) cart,count(*) FILTER(WHERE ordered) ordered FROM stages''',args).fetchone()
    rows=db.execute(cte+' SELECT * FROM stages ORDER BY started_at DESC,id LIMIT %s OFFSET %s',args+(PAGE_SIZE,page*PAGE_SIZE)).fetchall()
    n=stats['conversations']
    stats['conversion_percent']=round(100*stats['ordered']/n,1) if n else 0
    return {'stats':stats,'rows':rows,'page':page,'page_size':PAGE_SIZE}

def detail(db,cid):
    c=db.execute('SELECT c.*,s.customer FROM conversations c JOIN sessions s ON s.id=c.session_id WHERE c.id=%s',(cid,)).fetchone()
    if not c: raise commerce.DomainError('Conversa não encontrada.',404)
    messages=db.execute('SELECT * FROM conversation_messages WHERE conversation_id=%s ORDER BY sequence',(cid,)).fetchall()
    events=db.execute('SELECT e.*,g.title,f.platform FROM journey_events e LEFT JOIN offers f ON f.id=e.offer_id LEFT JOIN games g ON g.id=f.game_id WHERE conversation_id=%s ORDER BY created_at,id',(cid,)).fetchall()
    return {'conversation':c,'messages':messages,'events':events}
