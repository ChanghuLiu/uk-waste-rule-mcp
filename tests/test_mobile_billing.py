from __future__ import annotations

import sqlite3
import asyncio
import json
import time
from unittest.mock import Mock

from uk_waste_rule_mcp.mobile_api import GooglePlayVerifier, MobilePlayReports, register_mobile_routes
from uk_waste_rule_mcp.case_state import DurableCaseStore


class FakeVerifier:
    configured = True
    def __init__(self): self.verify_calls=0; self.consume_calls=0; self.consume_ok=False
    def verify(self, _token): self.verify_calls+=1; return True
    def consume(self, _token): self.consume_calls+=1; return self.consume_ok


def test_play_report_persists_token_digest_binds_case_and_retries_consume(tmp_path):
    verifier=FakeVerifier(); reports=MobilePlayReports(tmp_path/"play.sqlite3",verifier); runs=[]
    granted=[]
    factory=lambda:runs.append(1) or {"decision":{"status":"SCREENING_COMPLETE_REVIEW_REQUIRED"}}
    expiry=int(time.time())+86400
    status,first=reports.redeem(case_ref="case-a",token="secret-play-token",expires_at_epoch=expiry,report_factory=factory,on_grant=lambda:granted.append(1))
    assert status==200 and first["report_granted"] and first["consume_pending"]
    status,retry=reports.redeem(case_ref="case-a",token="secret-play-token",expires_at_epoch=expiry,report_factory=factory,on_grant=lambda:granted.append(2))
    assert status==200 and retry["report"]==first["report"] and runs==[1]
    assert verifier.verify_calls==1 and verifier.consume_calls==2
    assert granted==[1]
    verifier.consume_ok=True
    reopened=MobilePlayReports(tmp_path/"play.sqlite3",verifier)
    assert reopened.recover(case_ref="case-a",token="secret-play-token")[1]["consume_pending"] is False
    assert reports.redeem(case_ref="case-b",token="secret-play-token",expires_at_epoch=expiry,report_factory=factory)[0]==409
    with sqlite3.connect(reports.db_path) as db: digest=db.execute("SELECT token_hash FROM mobile_play_reports").fetchone()[0]
    assert digest==reports.token_hash("secret-play-token")
    assert "secret-play-token" not in reports.db_path.read_bytes().decode("latin-1")


def test_missing_play_verifier_returns_503_before_report_generation(tmp_path,monkeypatch):
    monkeypatch.delenv("WASTE_PLAY_SERVICE_ACCOUNT_JSON",raising=False)
    monkeypatch.delenv("WASTE_PLAY_SERVICE_ACCOUNT_FILE",raising=False)
    verifier=GooglePlayVerifier(); assert verifier.configured is False
    reports=MobilePlayReports(tmp_path/"reports.sqlite3",verifier); generated=[]
    status,body=reports.redeem(case_ref="case",token="token",expires_at_epoch=int(time.time())+86400,report_factory=lambda:generated.append(1) or {})
    assert status==503 and body["report_granted"] is False and generated==[]


class Response:
    def __init__(self,payload=None,status_code=200): self.payload,self.status_code=payload,status_code
    def json(self): return self.payload


def test_product_v2_verification_is_exact_and_fail_closed():
    verifier=GooglePlayVerifier.__new__(GooglePlayVerifier); verifier.configured=True; verifier.session=Mock()
    verifier.session.get.return_value=Response({"purchaseStateContext":{"purchaseState":"PURCHASED"},"productLineItem":[{"productId":"waste_report_one","productOfferDetails":{"consumptionState":"CONSUMPTION_STATE_YET_TO_BE_CONSUMED"}}]})
    assert verifier.verify("token") is True
    verifier.session.get.return_value=Response({"purchaseStateContext":{"purchaseState":"PENDING"},"productLineItem":[]})
    assert verifier.verify("token") is False


def test_readiness_api_returns_engine_missing_fact_as_server_question(tmp_path, monkeypatch):
    class Server:
        routes={}
        def custom_route(self,path,**_kwargs):
            def register(fn): self.routes[path]=fn; return fn
            return register
    class Request:
        def __init__(self,body): self.body=body
        async def json(self): return self.body
    server=Server(); register_mobile_routes(server,case_store=DurableCaseStore(tmp_path,ttl_seconds=86400),runtime_dir=tmp_path)
    response=asyncio.run(server.routes["/api/mobile/v1/readiness"](Request({"nation":"England","role":"receiver","activities":["receive_waste"]})))
    body=json.loads(response.body)
    assert body["status"]=="more_information_needed"
    assert body["next_question"]["id"]=="site_location"
    assert body["case_ref"] is None and body["report_available"] is False
    unknown=asyncio.run(server.routes["/api/mobile/v1/readiness"](Request({"nation":"England","role":"receiver","activities":["receive_waste"],"stop_on_missing":"site_location"})))
    unknown_body=json.loads(unknown.body)
    assert unknown_body["status"]=="more_information_needed"
    assert unknown_body["result"]["title"]=="More information needed"
    assert unknown_body["report_available"] is False


def test_case_extension_aligns_purchase_access_expiry(tmp_path):
    store=DurableCaseStore(tmp_path,ttl_seconds=86400)
    case=store.create(action="waste_case_preflight",workflow="waste_rule_preflight",payload={"nation":"England"},source_bucket="android",classification="confirmed_external",owner_test=False)
    expiry=int(time.time())+90000
    assert store.extend(case.state_ref,expires_at_epoch=expiry)
    assert store.get(case.state_ref).expires_at_epoch==expiry
