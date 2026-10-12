from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4
from fastapi import FastAPI, Request, Response, Depends, APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from fastapi.middleware.cors import CORSMiddleware
from . import config
from . import commerce, pixel
from .db import connect, migrate
from .catalog import catalog, search_titles, add_title, review_titles, set_offer_active, IntegrationError
from .simulation import advance, history
from . import admin_auth, journey, admin_data

@asynccontextmanager
async def lifespan(app):
    migrate()
    yield

app = FastAPI(title='RetroVault API', version='0.1.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.APP_ORIGINS, allow_credentials=True,
                   allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Content-Type'])

@app.middleware('http')
async def origin_check(request: Request, call_next):
    if request.method not in {'GET','HEAD','OPTIONS'}:
        origin=request.headers.get('origin')
        if origin and origin not in config.APP_ORIGINS:
            return JSONResponse({'detail':'Origem não autorizada.'},status_code=403)
        if request.headers.get('sec-fetch-site')=='cross-site':
            return JSONResponse({'detail':'Origem não autorizada.'},status_code=403)
    return await call_next(request)

@app.exception_handler(commerce.DomainError)
async def domain_error(request, error):
    return JSONResponse({'detail':error.message},status_code=error.status)

@app.exception_handler(IntegrationError)
async def integration_error(request,error):
    return JSONResponse({'detail':str(error)},status_code=503)

class CartEdit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    offer_id:int=Field(gt=0)
    mode:Literal['sale','rental']
    quantity:int=Field(ge=0,le=10)

class Confirmation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    checkout_id:str=Field(max_length=100)
    confirmed:bool
    payment_success:bool=True

class Message(BaseModel):
    model_config = ConfigDict(extra='forbid')
    message:str=Field(min_length=1,max_length=2000)

def sid(request):
    return request.cookies.get('retrovault_session')

@app.get('/api/health')
def health():
    return {'status': 'ok', 'service': 'RetroVault', 'simulation_mode':'manual'}

@app.post('/api/session')
def session_start(request:Request,response:Response):
    with connect() as db:
        existing=sid(request)
        if existing:
            try:
                session=commerce.require_session(db,existing,touch=True)
                return {'customer':session['customer'],'simulation_mode':'manual'}
            except commerce.DomainError: pass
        session_id,customer=commerce.create_session(db)
    response.set_cookie('retrovault_session',session_id,httponly=True,secure=config.COOKIE_SECURE,
        samesite='lax',max_age=config.SESSION_TTL,path='/')
    return {'customer':customer,'simulation_mode':'manual'}

@app.get('/api/state')
def state(request:Request):
    with connect() as db:
        session=commerce.require_session(db,sid(request),touch=True)
        return {'customer':session['customer'],'cart':commerce.cart(db,sid(request)),
                'orders':commerce.orders(db,sid(request)),'history':history(db,sid(request)),
                'messages':session['messages'],'simulation_mode':'manual'}

@app.get('/api/catalog')
def get_catalog(request:Request,q:str='',platform:str=''):
    with connect() as db:
        session_id=sid(request)
        if session_id: commerce.require_session(db,session_id,lock=False)
        return catalog(db,session_id,q[:100],platform)

@app.put('/api/cart')
def edit_cart(body:CartEdit,request:Request):
    return journey.run(sid(request),'interface','cart',lambda db: commerce.set_cart(db,sid(request),body.offer_id,body.mode,body.quantity))

@app.post('/api/checkout')
def checkout(request:Request):
    return journey.run(sid(request),'interface','checkout',lambda db: commerce.summary(db,sid(request)))

@app.post('/api/confirm')
def confirm_order(body:Confirmation,request:Request):
    return journey.run(sid(request),'interface','order',lambda db: commerce.confirm(db,sid(request),body.checkout_id,body.confirmed,body.payment_success))

@app.post('/api/rentals/{rental_id}/return')
def rental_return(rental_id:str,request:Request):
    with connect() as db: return commerce.return_rental(db,sid(request),rental_id)

@app.post('/api/simulation')
def simulation(request:Request):
    with connect() as db: return advance(db,sid(request),f'manual:{uuid4()}',manual=True)

@app.post('/api/chat')
def chat(body:Message,request:Request):
    return pixel.chat(sid(request),body.message)

class AdminLogin(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username:str=Field(min_length=1,max_length=100)
    password:str=Field(min_length=1,max_length=512)

@app.post('/api/admin/login')
def admin_login(body:AdminLogin,request:Request,response:Response):
    token=admin_auth.login(body.username,body.password,request.client.host if request.client else 'unknown')
    response.set_cookie(admin_auth.COOKIE,token,httponly=True,secure=config.COOKIE_SECURE,samesite='strict',path='/api/admin',max_age=config.integer('ADMIN_SESSION_TTL_SECONDS',28800))
    return {'authenticated':True}

admin_router=APIRouter(prefix='/api/admin',dependencies=[Depends(admin_auth.require_admin)])

@admin_router.get('/session')
def admin_session(): return {'authenticated':True}

@admin_router.post('/logout')
def admin_logout(request:Request,response:Response):
    admin_auth.logout(request)
    response.delete_cookie(admin_auth.COOKIE,path='/api/admin')
    return {'authenticated':False}

@admin_router.get('/dashboard')
def admin_dashboard(start:str='',end:str='',platform:str='',actor:str='',origin:str='',page:int=Query(default=0,ge=0,le=100000)):
    with connect() as db: return admin_data.commercial(db,start,end,platform,actor,origin,page)

@admin_router.get('/conversations')
def admin_conversations(start:str='',end:str='',page:int=Query(default=0,ge=0,le=100000)):
    with connect() as db: return admin_data.conversations(db,start,end,page)

@admin_router.get('/orders/{order_id}')
def admin_order(order_id:str):
    with connect() as db:
        order=db.execute('SELECT * FROM orders WHERE id=%s',(order_id,)).fetchone()
        if not order: raise commerce.DomainError('Pedido não encontrado.',404)
        return order

@admin_router.get('/conversations/{conversation_id}')
def admin_conversation(conversation_id:str):
    with connect() as db: return admin_data.detail(db,conversation_id)

class TitleSelection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    game_id:int=Field(gt=0)
    platform:Literal['snes','gba','ps1','ps2','psp','nds']

class OfferStatus(BaseModel):
    model_config=ConfigDict(extra='forbid')
    active:bool

@admin_router.get('/catalog/search')
def admin_search(q:str=Query(default='',max_length=100),platform:str='psp',page:int=Query(default=0,ge=0,le=100)):
    return search_titles(q,platform,page)

@admin_router.post('/catalog/add')
def admin_add(body:TitleSelection): return add_title(body.game_id,body.platform)

@admin_router.post('/catalog/review')
def admin_review(): return review_titles()

@admin_router.post('/catalog/{offer_id}/status')
def admin_offer_status(offer_id:int,body:OfferStatus):
    with connect() as db: return set_offer_active(db,offer_id,body.active)

app.include_router(admin_router)
