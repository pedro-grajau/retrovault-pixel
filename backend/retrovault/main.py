from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from fastapi.middleware.cors import CORSMiddleware
from . import config
from . import commerce, pixel
from .db import connect, migrate
from .catalog import catalog
from .simulation import advance, history

@asynccontextmanager
async def lifespan(app):
    migrate()
    yield

app = FastAPI(title='RetroVault API', version='0.1.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[config.APP_ORIGIN], allow_credentials=True,
                   allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Content-Type'])

@app.middleware('http')
async def origin_check(request: Request, call_next):
    if request.method not in {'GET','HEAD','OPTIONS'}:
        origin=request.headers.get('origin')
        if origin and origin != config.APP_ORIGIN:
            return JSONResponse({'detail':'Origem não autorizada.'},status_code=403)
        if request.headers.get('sec-fetch-site')=='cross-site':
            return JSONResponse({'detail':'Origem não autorizada.'},status_code=403)
    return await call_next(request)

@app.exception_handler(commerce.DomainError)
async def domain_error(request, error):
    return JSONResponse({'detail':error.message},status_code=error.status)

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
    return {'status': 'ok', 'service': 'RetroVault', 'simulation_interval_seconds': config.SIMULATION_INTERVAL}

@app.post('/api/session')
def session_start(request:Request,response:Response):
    with connect() as db:
        existing=sid(request)
        if existing:
            try:
                session=commerce.require_session(db,existing,touch=True)
                return {'customer':session['customer'],'simulation_interval_seconds':config.SIMULATION_INTERVAL}
            except commerce.DomainError: pass
        session_id,customer=commerce.create_session(db)
    response.set_cookie('retrovault_session',session_id,httponly=True,secure=config.COOKIE_SECURE,
        samesite='lax',max_age=config.SESSION_TTL,path='/')
    return {'customer':customer,'simulation_interval_seconds':config.SIMULATION_INTERVAL}

@app.get('/api/state')
def state(request:Request):
    with connect() as db:
        session=commerce.require_session(db,sid(request),touch=True)
        return {'customer':session['customer'],'cart':commerce.cart(db,sid(request)),
                'orders':commerce.orders(db,sid(request)),'history':history(db,sid(request)),
                'messages':session['messages'],'simulation_interval_seconds':config.SIMULATION_INTERVAL}

@app.get('/api/catalog')
def get_catalog(request:Request,q:str='',platform:str=''):
    with connect() as db:
        session_id=sid(request)
        if session_id: commerce.require_session(db,session_id,lock=False)
        return catalog(db,session_id,q[:100],platform)

@app.put('/api/cart')
def edit_cart(body:CartEdit,request:Request):
    with connect() as db: return commerce.set_cart(db,sid(request),body.offer_id,body.mode,body.quantity)

@app.post('/api/checkout')
def checkout(request:Request):
    with connect() as db: return commerce.summary(db,sid(request))

@app.post('/api/confirm')
def confirm_order(body:Confirmation,request:Request):
    with connect() as db: return commerce.confirm(db,sid(request),body.checkout_id,body.confirmed,body.payment_success)

@app.post('/api/rentals/{rental_id}/return')
def rental_return(rental_id:str,request:Request):
    with connect() as db: return commerce.return_rental(db,sid(request),rental_id)

@app.post('/api/simulation')
def simulation(request:Request):
    with connect() as db: return advance(db,sid(request),f'manual:{uuid4()}',manual=True)

@app.post('/api/chat')
def chat(body:Message,request:Request):
    return pixel.chat(sid(request),body.message)
