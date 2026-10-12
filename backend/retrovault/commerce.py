"""Authoritative transactions shared by the web, Pixel and simulator."""
from datetime import datetime, timedelta, timezone
import secrets
from uuid import uuid4
from psycopg.types.json import Jsonb
from . import config

class DomainError(Exception):
    def __init__(self, message, status=409):
        self.message, self.status = message, status

def require_session(conn, sid, lock=True, touch=False):
    if not sid:
        raise DomainError('Inicie uma demonstração para continuar.', 401)
    row = conn.execute('SELECT * FROM sessions WHERE id=%s' + (' FOR UPDATE' if lock else ''), (sid,)).fetchone()
    if not row or row['expired_at'] or (datetime.now(timezone.utc) - row['last_seen']).total_seconds() > config.SESSION_TTL:
        raise DomainError('Sua sessão expirou. Inicie uma nova demonstração.', 401)
    if touch:
        conn.execute('UPDATE sessions SET last_seen=now() WHERE id=%s', (sid,))
    return row

def create_session(conn):
    conn.execute('SELECT pg_advisory_xact_lock(172906)')
    sid = secrets.token_urlsafe(32)
    customer = secrets.choice(['Alex', 'Sam', 'Charlie', 'Robin', 'Taylor']) + ' · cliente fictício'
    conn.execute('INSERT INTO sessions(id,customer) VALUES (%s,%s)', (sid, customer))
    for offer in conn.execute('SELECT id FROM offers WHERE active').fetchall():
        initialize_offer(conn,sid,offer['id'])
    return sid, customer

def initialize_offer(conn,sid,offer_id):
    created=conn.execute('INSERT INTO sale_stock VALUES (%s,%s,%s) ON CONFLICT DO NOTHING RETURNING offer_id',(sid,offer_id,config.SALE_STOCK)).fetchone()
    if created:
        for _ in range(config.RENTAL_STOCK):
            conn.execute('INSERT INTO rental_copies(session_id,offer_id) VALUES (%s,%s)',(sid,offer_id))

def items(conn, sid):
    result = conn.execute('''SELECT c.offer_id,c.mode,c.quantity,o.platform,p.name AS platform_name,g.title,
        CASE WHEN c.mode='sale' THEN o.sale_price ELSE o.rental_price END AS unit_price
        FROM carts c JOIN offers o ON o.id=c.offer_id JOIN games g ON g.id=o.game_id
        JOIN platforms p ON p.slug=o.platform WHERE c.session_id=%s ORDER BY c.offer_id,c.mode''', (sid,)).fetchall()
    for item in result:
        if item['mode'] == 'sale':
            stock = conn.execute('SELECT quantity FROM sale_stock WHERE session_id=%s AND offer_id=%s', (sid, item['offer_id'])).fetchone()
            item['available'] = stock['quantity'] if stock else 0
        else:
            item['available'] = conn.execute('SELECT count(*) AS n FROM rental_copies WHERE session_id=%s AND offer_id=%s AND available', (sid, item['offer_id'])).fetchone()['n']
        item['rental_days'] = config.RENTAL_DAYS if item['mode'] == 'rental' else None
        item['subtotal'] = item['quantity'] * item['unit_price']
    return result

def cart(conn, sid):
    session = require_session(conn, sid, lock=False)
    rows = items(conn, sid)
    return {'items': rows, 'total': sum(i['subtotal'] for i in rows), 'version': session['version']}

def set_cart(conn, sid, offer_id, mode, quantity):
    require_session(conn, sid)
    if mode not in {'sale', 'rental'} or type(quantity) is not int or not 0 <= quantity <= 10:
        raise DomainError('Modalidade ou quantidade inválida.', 422)
    if not conn.execute('SELECT 1 FROM sale_stock WHERE session_id=%s AND offer_id=%s', (sid, offer_id)).fetchone():
        raise DomainError('Oferta indisponível nesta sessão.', 404)
    previous=conn.execute('SELECT quantity FROM carts WHERE session_id=%s AND offer_id=%s AND mode=%s',(sid,offer_id,mode)).fetchone()
    if (previous['quantity'] if previous else 0)==quantity:
        return cart(conn,sid)
    if quantity == 0:
        conn.execute('DELETE FROM carts WHERE session_id=%s AND offer_id=%s AND mode=%s', (sid, offer_id, mode))
    else:
        if not conn.execute('SELECT 1 FROM offers WHERE id=%s AND active FOR SHARE',(offer_id,)).fetchone():
            raise DomainError('Oferta não está mais disponível.',409)
        conn.execute('INSERT INTO carts VALUES (%s,%s,%s,%s) ON CONFLICT(session_id,offer_id,mode) DO UPDATE SET quantity=excluded.quantity', (sid, offer_id, mode, quantity))
    conn.execute('UPDATE sessions SET version=version+1 WHERE id=%s', (sid,))
    from . import journey
    journey.event(conn,sid,'cart',{'mode':mode,'quantity':quantity},offer_id=offer_id)
    return cart(conn, sid)

def validate_stock(conn, sid, rows):
    for item in rows:
        if not conn.execute('SELECT 1 FROM offers WHERE id=%s AND active FOR SHARE',(item['offer_id'],)).fetchone():
            raise DomainError('Oferta não está mais disponível. Atualize o carrinho.')
        if item['mode'] == 'sale':
            stock = conn.execute('SELECT quantity FROM sale_stock WHERE session_id=%s AND offer_id=%s FOR UPDATE', (sid, item['offer_id'])).fetchone()
            n = stock['quantity'] if stock else 0
        else:
            n = len(conn.execute('SELECT id FROM rental_copies WHERE session_id=%s AND offer_id=%s AND available FOR UPDATE', (sid, item['offer_id'])).fetchall())
        if item['quantity'] > n:
            raise DomainError(f'{item["title"]}: estoque insuficiente para {"venda" if item["mode"] == "sale" else "locação"}.')

def summary(conn, sid):
    session = require_session(conn, sid)
    rows = items(conn, sid)
    if not rows:
        raise DomainError('Seu carrinho está vazio.')
    validate_stock(conn, sid, rows)
    result = {'items': rows, 'total': sum(i['subtotal'] for i in rows), 'pickup': 'Retirada fictícia na loja', 'payment': 'Pagamento simulado'}
    cid = str(uuid4())
    conn.execute('INSERT INTO checkouts(id,session_id,version,summary) VALUES (%s,%s,%s,%s)', (cid, sid, session['version'], Jsonb(result)))
    from . import journey
    journey.event(conn,sid,'checkout',{'checkout_id':cid},event_id='checkout:'+cid)
    return {**result, 'checkout_id': cid}

def place_order(conn, sid, rows, actor='visitor', checkout_id=None):
    validate_stock(conn, sid, rows)
    oid = str(uuid4())
    conn.execute('INSERT INTO orders(id,session_id,checkout_id,actor,items,total) VALUES (%s,%s,%s,%s,%s,%s)',
        (oid, sid, checkout_id, actor, Jsonb(rows), sum(i['subtotal'] for i in rows)))
    from . import journey
    origin='simulation' if actor=='simulation' else journey.context.get()['origin']
    conn.execute('UPDATE orders SET origin=%s WHERE id=%s',(origin,oid))
    if actor!='simulation':
        journey.event(conn,sid,'order',{'items':rows},order_id=oid,event_id='order:'+oid)
    for item in rows:
        if item['mode'] == 'sale':
            conn.execute('UPDATE sale_stock SET quantity=quantity-%s WHERE session_id=%s AND offer_id=%s', (item['quantity'], sid, item['offer_id']))
        else:
            copies = conn.execute('SELECT id FROM rental_copies WHERE session_id=%s AND offer_id=%s AND available ORDER BY id LIMIT %s FOR UPDATE', (sid, item['offer_id'], item['quantity'])).fetchall()
            for copy in copies:
                conn.execute('UPDATE rental_copies SET available=false WHERE id=%s', (copy['id'],))
                conn.execute('INSERT INTO rentals(id,order_id,copy_id,due_at) VALUES (%s,%s,%s,%s)',
                    (str(uuid4()), oid, copy['id'], datetime.now(timezone.utc) + timedelta(days=item.get('rental_days') or config.RENTAL_DAYS)))
    return {'order_id': oid, 'total': sum(i['subtotal'] for i in rows), 'simulated': True}

def confirm(conn, sid, checkout_id, confirmed, payment_success=True):
    session = require_session(conn, sid)
    if confirmed is not True:
        raise DomainError('Confirme explicitamente o resumo antes de concluir.', 422)
    checkout = conn.execute('SELECT * FROM checkouts WHERE id=%s AND session_id=%s FOR UPDATE', (checkout_id, sid)).fetchone()
    if not checkout:
        raise DomainError('Resumo não encontrado nesta sessão.', 404)
    existing = conn.execute('SELECT id,total FROM orders WHERE checkout_id=%s AND session_id=%s', (checkout_id, sid)).fetchone()
    if existing:
        return {'order_id': existing['id'], 'total': existing['total'], 'simulated': True, 'already_processed': True}
    if (datetime.now(timezone.utc) - checkout['created_at']).total_seconds() > 600:
        raise DomainError('Resumo expirado. Prepare um novo resumo.')
    rows = items(conn, sid)
    if session['version'] != checkout['version'] or rows != checkout['summary']['items']:
        raise DomainError('O carrinho ou suas condições mudaram. Prepare um novo resumo.')
    if not payment_success:
        raise DomainError('Pagamento simulado recusado. Nenhum pedido foi concluído.')
    order = place_order(conn, sid, rows, checkout_id=checkout_id)
    conn.execute('UPDATE checkouts SET consumed=true WHERE id=%s', (checkout_id,))
    conn.execute('DELETE FROM carts WHERE session_id=%s', (sid,))
    conn.execute('UPDATE sessions SET version=version+1 WHERE id=%s', (sid,))
    return order

def orders(conn, sid):
    require_session(conn, sid, lock=False)
    rows = conn.execute('SELECT * FROM orders WHERE session_id=%s ORDER BY created_at DESC LIMIT 100', (sid,)).fetchall()
    for row in rows:
        row.pop('session_id')
        row['rentals'] = conn.execute('''SELECT r.id,r.due_at,r.returned_at,g.title,p.name AS platform_name
            FROM rentals r JOIN rental_copies rc ON rc.id=r.copy_id JOIN offers o ON o.id=rc.offer_id
            JOIN games g ON g.id=o.game_id JOIN platforms p ON p.slug=o.platform WHERE r.order_id=%s''', (row['id'],)).fetchall()
    return rows

def return_rental(conn, sid, rental_id):
    require_session(conn, sid)
    rental = conn.execute('''SELECT r.* FROM rentals r JOIN orders o ON o.id=r.order_id
        WHERE r.id=%s AND o.session_id=%s FOR UPDATE OF r''', (rental_id, sid)).fetchone()
    if not rental:
        raise DomainError('Aluguel não encontrado nesta sessão.', 404)
    if rental['returned_at']:
        return {'returned': True, 'already_processed': True}
    conn.execute('UPDATE rentals SET returned_at=now() WHERE id=%s', (rental_id,))
    conn.execute('UPDATE rental_copies SET available=true WHERE id=%s', (rental['copy_id'],))
    return {'returned': True}
