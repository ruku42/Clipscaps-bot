import os,hashlib,hmac,json,time
from fastapi import FastAPI,HTTPException,Header
from pydantic import BaseModel
from app.config import *
from app.db import *

app=FastAPI(title="Clipcaps API")
class WithdrawReq(BaseModel):
    user_id:int; method:str; number:str; coins:int
class RewardReq(BaseModel):
    user_id:int; event_id:str; reward:int; source:str
@app.on_event("startup")
def startup(): init()

# Production: validate Telegram WebApp initData server-side and use the verified
# user ID. Do not trust a client-supplied user_id in a public deployment.
@app.get("/health")
def health(): return {"ok":True,"service":"Clipcaps"}
@app.get("/balance/{uid}")
def balance(uid:int):
    r=user(uid)
    if not r: raise HTTPException(404,"User not found")
    return {"coins":r["coins"],"value_bdt":round(r["coins"]*COIN_TO_BDT,2)}
@app.post("/reward")
def reward(req:RewardReq):
    # This endpoint is intentionally NOT a SmartLink click counter.
    # Connect only to Monetag's documented verified rewarded-ad callback.
    if req.reward<=0 or req.reward>10000: raise HTTPException(400,"Invalid reward")
    if not req.event_id or len(req.event_id)>200: raise HTTPException(400,"Invalid event")
    ok=reward_once(req.user_id,req.event_id,req.reward,req.source)
    return {"ok":ok,"credited":req.reward if ok else 0}
@app.post("/withdraw")
def make_withdraw(req:WithdrawReq):
    if req.method not in ("bKash","Nagad"): raise HTTPException(400,"Invalid method")
    if req.coins<MIN_WITHDRAW_COINS: raise HTTPException(400,"Minimum withdrawal not reached")
    if not req.number.isdigit() or len(req.number)!=11 or not req.number.startswith("01"): raise HTTPException(400,"Invalid Bangladesh mobile number")
    r=user(req.user_id)
    if not r or r["coins"]<req.coins: raise HTTPException(400,"Insufficient balance")
    amount=round(req.coins*COIN_TO_BDT,2); withdraw(req.user_id,req.method,req.number,req.coins,amount)
    return {"ok":True,"status":"pending","amount_bdt":amount}
@app.get("/admin/stats")
def admin_stats(x_admin_id:int=Header(default=0)):
    if x_admin_id!=ADMIN_ID: raise HTTPException(403,"Forbidden")
    u,c,p,paid=stats(); return {"users":u,"coins":c,"pending":p,"paid_bdt":paid}
@app.get("/admin/withdrawals")
def admin_withdrawals(x_admin_id:int=Header(default=0)):
    if x_admin_id!=ADMIN_ID: raise HTTPException(403,"Forbidden")
    return [dict(r) for r in withdrawals()]
@app.post("/admin/withdrawals/{wid}/{status}")
def admin_status(wid:int,status:str,x_admin_id:int=Header(default=0)):
    if x_admin_id!=ADMIN_ID: raise HTTPException(403,"Forbidden")
    if status not in ("paid","rejected"): raise HTTPException(400,"Invalid status")
    set_status(wid,status); return {"ok":True}
