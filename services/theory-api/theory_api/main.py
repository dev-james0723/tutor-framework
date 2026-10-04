"""Regional internal HTTP boundary, not a public unauthenticated theory service."""
import hmac
import os
import uuid
from importlib.metadata import version
from typing import Callable
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from defusedxml.common import DefusedXmlException
from xml.etree.ElementTree import ParseError
from . import engine
from .schemas import OperationRequest, ScoreRequest, PracticeRequest, CurriculumRequest, ReconcileRequest, Envelope

ENGINE_VERSION = version("tutor-framework")
app = FastAPI(title="Super Theory API", version="0.1.0", docs_url=None, redoc_url=None)

class BoundedBodyMiddleware:
    def __init__(self, wrapped):
        self.app = wrapped

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST':
            return await self.app(scope,receive,send)
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            body.extend(message.get('body',b''))
            if len(body) > 3_000_000:
                return await JSONResponse({'code':'input_too_large'},status_code=413)(scope,receive,send)
            if not message.get('more_body',False):
                break
        sent = False
        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {'type':'http.request','body':bytes(body),'more_body':False}
            return await receive()
        async def safe_send(message):
            if message['type'] == 'http.response.start':
                message['headers'].append((b'cache-control',b'no-store'))
            await send(message)
        await self.app(scope,replay,safe_send)

app.add_middleware(BoundedBodyMiddleware)

def authorize(request: Request):
    token = os.environ.get("THEORY_API_TOKEN","")
    region = os.environ.get("THEORY_HOME_REGION","")
    if not token or region not in {"global","cn"}:
        raise HTTPException(503,detail={"code":"regional_configuration_unavailable"})
    if not hmac.compare_digest(request.headers.get("authorization",""),"Bearer "+token):
        raise HTTPException(401,detail={"code":"service_authentication_required"})
    if request.headers.get("x-home-region") != region:
        raise HTTPException(403,detail={"code":"regional_boundary_blocked"})

@app.get("/health")
def health():
    return {"status":"ok","service":"theory-api"}

@app.get("/version")
def api_version():
    return {"engine_version":ENGINE_VERSION,"api_version":"0.1.0"}

def respond(request: Request, execute: Callable):
    request_id = str(uuid.uuid4())
    try:
        payload = execute()
    except PermissionError as error:
        raise HTTPException(409,detail={"code":"assessment_withheld","request_id":request_id,"message":str(error)}) from error
    except (ValueError, TypeError, KeyError, ParseError, DefusedXmlException) as error:
        raise HTTPException(422,detail={"code":"invalid_input","request_id":request_id,"message":str(error)[:300]}) from error
    status = payload.get("state","unsupported")
    review = bool(payload.get("review_required") or status == "review_required" or "requires_version_review" in status)
    claim_ids = payload.get("claim_ids",[]) or ([payload["claim_id"]] if payload.get("claim_id") else [])
    sources = [payload["source_id"]] if payload.get("source_id") else []
    return Envelope(request_id=request_id,engine_version=ENGINE_VERSION,status=status,payload=payload,
                    warnings=payload.get("warnings",[]),claim_ids=claim_ids,source_ids=sources,review_required=review)

@app.post("/v1/theory/{operation}", dependencies=[Depends(authorize)], response_model=Envelope)
def theory(operation: str, body: OperationRequest, request: Request):
    return respond(request,lambda:engine.operation(operation,body))

@app.post("/v1/score/analyze", dependencies=[Depends(authorize)], response_model=Envelope)
def score(body: ScoreRequest, request: Request):
    return respond(request,lambda:engine.score(body))

@app.post("/v1/practice/generate", dependencies=[Depends(authorize)], response_model=Envelope)
def practice(body: PracticeRequest, request: Request):
    return respond(request,lambda:engine.generate(body))

@app.post("/v1/practice/check", dependencies=[Depends(authorize)], response_model=Envelope)
def check(body: PracticeRequest, request: Request):
    return respond(request,lambda:engine.check(body))

@app.post("/v1/curricula/compare", dependencies=[Depends(authorize)], response_model=Envelope)
def curricula(body: CurriculumRequest, request: Request):
    return respond(request,lambda:engine.compare_curricula(**body.model_dump()))

@app.post("/v1/evidence/reconcile", dependencies=[Depends(authorize)], response_model=Envelope)
def reconcile(body: ReconcileRequest, request: Request):
    return respond(request,lambda:engine.reconcile_claims(body.records))
