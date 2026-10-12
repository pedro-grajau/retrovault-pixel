from datetime import datetime, timezone
import hashlib
import random
from psycopg.types.json import Jsonb
from . import config, commerce

def advance(conn, sid, batch_id, manual=False):
    session = commerce.require_session(conn, sid)
    previous = conn.execute('SELECT events FROM batches WHERE session_id=%s AND id=%s', (sid, batch_id)).fetchone()
    if previous:
        return {'events': previous['events'], 'already_processed': True}
    now = datetime.now(timezone.utc)
    if manual and session['last_manual'] and (now-session['last_manual']).total_seconds() < 5:
        raise commerce.DomainError('Aguarde alguns segundos antes de avançar novamente.', 429)
    rng = random.Random(int.from_bytes(hashlib.sha256(f'{sid}:{batch_id}'.encode()).digest()[:8]))
    events = []
    offers = conn.execute('''SELECT o.*,g.title,p.name AS platform_name FROM offers o
        JOIN games g ON g.id=o.game_id JOIN platforms p ON p.slug=o.platform
        JOIN sale_stock s ON s.offer_id=o.id WHERE o.active AND s.session_id=%s ORDER BY o.id''', (sid,)).fetchall()
    for index in range(config.integer('SIMULATION_BATCH_SIZE', 3)):
        mode = rng.choice(['sale', 'rental', 'return'])
        event = {'type': mode, 'simulated': True, 'index': index}
        if mode == 'return':
            rental = conn.execute('''SELECT r.id,g.title FROM rentals r JOIN orders o ON o.id=r.order_id
                JOIN rental_copies rc ON rc.id=r.copy_id JOIN offers f ON f.id=rc.offer_id JOIN games g ON g.id=f.game_id
                WHERE o.session_id=%s AND o.actor='simulation' AND r.returned_at IS NULL ORDER BY r.due_at LIMIT 1''', (sid,)).fetchone()
            if rental:
                commerce.return_rental(conn, sid, rental['id'])
                event.update(status='complete', title=rental['title'], message='Exemplar devolvido pela demanda fictícia.')
            else:
                event.update(status='skipped', message='Nenhuma devolução fictícia elegível.')
        elif offers:
            offer = rng.choice(offers)
            price = offer['sale_price' if mode == 'sale' else 'rental_price']
            item = {'offer_id': offer['id'], 'platform': offer['platform'], 'platform_name': offer['platform_name'],
                    'title': offer['title'], 'mode': mode, 'quantity': 1, 'unit_price': price,
                    'subtotal': price, 'rental_days': config.RENTAL_DAYS if mode=='rental' else None}
            try:
                # Savepoint keeps a failed simulated transaction from poisoning the batch.
                with conn.transaction():
                    order = commerce.place_order(conn, sid, [item], actor='simulation')
                event.update(status='complete', title=offer['title'], platform=offer['platform_name'], order_id=order['order_id'],
                    message='Venda fictícia concluída.' if mode=='sale' else 'Aluguel fictício iniciado.')
            except commerce.DomainError:
                event.update(status='skipped', title=offer['title'], message='Estoque indisponível; evento não realizado.')
        else:
            event.update(status='skipped', message='Nenhuma oferta nesta sessão.')
        events.append(event)
    conn.execute('INSERT INTO batches(id,session_id,events) VALUES (%s,%s,%s)', (batch_id, sid, Jsonb(events)))
    if manual:
        conn.execute('UPDATE sessions SET last_manual=now() WHERE id=%s', (sid,))
    return {'events': events, 'already_processed': False}

def history(conn, sid):
    commerce.require_session(conn, sid, lock=False)
    return conn.execute('SELECT id,events,created_at FROM batches WHERE session_id=%s ORDER BY created_at DESC LIMIT 20', (sid,)).fetchall()
