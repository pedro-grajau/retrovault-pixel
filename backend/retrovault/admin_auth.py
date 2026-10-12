"""Independent, server-side administrative credentials and opaque sessions."""
import hashlib
import hmac
import os
import secrets
from fastapi import Request
from . import config, commerce
from .db import connect

COOKIE='retrovault_admin'

def password_hash(password, salt=None):
    salt=salt or secrets.token_hex(16)
    digest=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    return f'scrypt${salt}${digest}'

def verify(password, encoded):
    try:
        method,salt,_=encoded.split('$')
        return method=='scrypt' and hmac.compare_digest(password_hash(password,salt),encoded)
    except (ValueError,TypeError): return False

def fingerprint(value): return hashlib.sha256(value.encode()).hexdigest()

def login(username,password,peer):
    token=None
    with connect() as db:
        # One bucket per peer, irrespective of guessed username.
        key=fingerprint(peer)
        db.execute('SELECT pg_advisory_xact_lock(%s)',(int(key[:15],16),))
        row=db.execute('SELECT * FROM admin_attempts WHERE key=%s',(key,)).fetchone()
        from datetime import datetime,timezone
        if row and (datetime.now(timezone.utc)-row['window_at']).total_seconds()<900 and row['count']>=5:
            raise commerce.DomainError('Muitas tentativas. Aguarde 15 minutos.',429)
        db.execute("INSERT INTO admin_attempts VALUES (%s,1,now()) ON CONFLICT(key) DO UPDATE SET count=CASE WHEN admin_attempts.window_at<now()-interval '15 minutes' THEN 1 ELSE admin_attempts.count+1 END,window_at=CASE WHEN admin_attempts.window_at<now()-interval '15 minutes' THEN now() ELSE admin_attempts.window_at END",(key,))
        configured=os.getenv('ADMIN_PASSWORD_HASH','')
        valid=verify(password,configured or password_hash('unconfigured', '00'*16))
        if configured and os.getenv('ADMIN_USERNAME') and hmac.compare_digest(username.encode(),os.getenv('ADMIN_USERNAME','').encode()) and valid:
            token=secrets.token_urlsafe(32)
            db.execute("INSERT INTO admin_sessions VALUES (%s,now()+(%s * interval '1 second'))",(fingerprint(token),config.integer('ADMIN_SESSION_TTL_SECONDS',28800)))
            db.execute('DELETE FROM admin_attempts WHERE key=%s',(key,))
    # Outside transaction so unsuccessful attempts are committed.
    if not token: raise commerce.DomainError('Credenciais inválidas.',401)
    return token

def require_admin(request: Request):
    token=request.cookies.get(COOKIE)
    if token:
        with connect() as db:
            if db.execute('SELECT 1 FROM admin_sessions WHERE token_hash=%s AND expires_at>now()',(fingerprint(token),)).fetchone():
                return True
    raise commerce.DomainError('Entre como administrador para continuar.',401)

def logout(request):
    token=request.cookies.get(COOKIE)
    if token:
        with connect() as db: db.execute('DELETE FROM admin_sessions WHERE token_hash=%s',(fingerprint(token),))
