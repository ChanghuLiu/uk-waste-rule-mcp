"""Android Play report API for the existing Waste preflight engine."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from .engine import ROLES, ACTIVITIES, waste_preflight
from .human_report import validate_form

PRODUCT_ID = "waste_report_one"
PACKAGE_NAME = "com.regevidencehub.waste"


class GooglePlayVerifier:
    def __init__(self) -> None:
        self.session = None
        self.configured = False
        try:
            from google.auth.transport.requests import AuthorizedSession
            from google.oauth2 import service_account
            raw = os.getenv("WASTE_PLAY_SERVICE_ACCOUNT_JSON", "").strip()
            path = os.getenv("WASTE_PLAY_SERVICE_ACCOUNT_FILE", "").strip()
            if path:
                credentials = service_account.Credentials.from_service_account_file(path, scopes=["https://www.googleapis.com/auth/androidpublisher"])
            elif raw:
                credentials = service_account.Credentials.from_service_account_info(json.loads(raw), scopes=["https://www.googleapis.com/auth/androidpublisher"])
            else:
                return
            self.session = AuthorizedSession(credentials)
            self.configured = True
        except Exception:
            return

    def _url(self, token: str, consume: bool = False) -> str:
        root = f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE_NAME}"
        if consume:
            return f"{root}/purchases/products/{PRODUCT_ID}/tokens/{token}:consume"
        return f"{root}/purchases/productsv2/tokens/{token}"

    def verify(self, token: str) -> bool:
        if not self.configured or self.session is None: return False
        try:
            response = self.session.get(self._url(token), timeout=10)
            if response.status_code != 200: return False
            data = response.json()
            return bool(isinstance(data, Mapping)
                and isinstance(data.get("purchaseStateContext"), Mapping)
                and data["purchaseStateContext"].get("purchaseState") == "PURCHASED"
                and isinstance(data.get("productLineItem"), list)
                and any(isinstance(item, Mapping) and item.get("productId") == PRODUCT_ID
                    and isinstance(item.get("productOfferDetails"), Mapping)
                    and item["productOfferDetails"].get("consumptionState") == "CONSUMPTION_STATE_YET_TO_BE_CONSUMED"
                    for item in data["productLineItem"]))
        except Exception: return False

    def consume(self, token: str) -> bool:
        if not self.configured or self.session is None: return False
        try: return self.session.post(self._url(token, True), timeout=10).status_code in {200, 204}
        except Exception: return False


class MobilePlayReports:
    def __init__(self, db_path: Path, verifier: Any) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path, self.verifier, self.lock = db_path, verifier, threading.RLock()
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS mobile_play_reports (case_ref TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE, report_json TEXT NOT NULL, consume_pending INTEGER NOT NULL DEFAULT 1, expires_at_epoch INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            columns={row["name"] for row in db.execute("PRAGMA table_info(mobile_play_reports)").fetchall()}
            if "expires_at_epoch" not in columns:
                db.execute("ALTER TABLE mobile_play_reports ADD COLUMN expires_at_epoch INTEGER NOT NULL DEFAULT 0")
        os.chmod(db_path, 0o600)
        self.purge_expired()

    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=15); db.row_factory = sqlite3.Row; return db

    def purge_expired(self) -> None:
        with self._db() as db:
            db.execute("UPDATE mobile_play_reports SET report_json='{}' WHERE expires_at_epoch<=? AND report_json!='{}'", (int(time.time()),))

    @staticmethod
    def token_hash(token: str) -> str: return hashlib.sha256(token.encode()).hexdigest()

    def _result(self, row, token: str) -> dict[str, Any]:
        if int(row["expires_at_epoch"]) <= int(time.time()):
            with self._db() as db: db.execute("UPDATE mobile_play_reports SET report_json='{}' WHERE case_ref=?", (row["case_ref"],))
            return {"status":"report_expired","case_ref":row["case_ref"],"report_granted":False}
        pending = bool(row["consume_pending"])
        if pending and self.verifier.consume(token):
            with self._db() as db: db.execute("UPDATE mobile_play_reports SET consume_pending=0 WHERE case_ref=?", (row["case_ref"],))
            pending = False
        return {"status":"report_granted","case_ref":row["case_ref"],"report":json.loads(row["report_json"]),"consume_pending":pending,"report_granted":True}

    def redeem(self, *, case_ref: str, token: str, expires_at_epoch: int, report_factory: Callable[[], Mapping[str, Any]], on_grant: Callable[[], None] | None = None) -> tuple[int,dict[str,Any]]:
        if not case_ref or not token or len(token)>4096: return 422,{"status":"invalid_request","report_granted":False}
        digest=self.token_hash(token)
        with self.lock, self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT * FROM mobile_play_reports WHERE token_hash=?",(digest,)).fetchone()
            if row:
                db.commit()
                return (409,{"status":"purchase_already_bound","report_granted":False}) if row["case_ref"]!=case_ref else (200,self._result(row,token))
            if db.execute("SELECT 1 FROM mobile_play_reports WHERE case_ref=?",(case_ref,)).fetchone(): db.rollback(); return 409,{"status":"case_already_granted","report_granted":False}
            if not self.verifier.configured: db.rollback(); return 503,{"status":"play_verification_unavailable","report_granted":False}
            try:
                if not self.verifier.verify(token): db.rollback(); return 403,{"status":"purchase_not_verified","report_granted":False}
                report=json.dumps(dict(report_factory()),sort_keys=True,separators=(",",":"))
                if on_grant is not None: on_grant()
                db.execute("INSERT INTO mobile_play_reports(case_ref,token_hash,report_json,expires_at_epoch) VALUES(?,?,?,?)",(case_ref,digest,report,int(expires_at_epoch))); db.commit()
            except Exception: db.rollback(); return 503,{"status":"report_unavailable","report_granted":False}
            row=db.execute("SELECT * FROM mobile_play_reports WHERE case_ref=?",(case_ref,)).fetchone()
            return 200,self._result(row,token)

    def recover(self, *,case_ref:str,token:str):
        with self._db() as db: row=db.execute("SELECT * FROM mobile_play_reports WHERE case_ref=?",(case_ref,)).fetchone()
        if row is None or row["token_hash"]!=self.token_hash(token): return 404,{"status":"report_not_found","report_granted":False}
        return 200,self._result(row,token)


def _question(field: str) -> dict[str, Any]:
    descriptors = {
        "nation": ("Where is the operation based?", "single_choice", [{"id":"England","label":"England"},{"id":"Scotland","label":"Scotland"},{"id":"Wales","label":"Wales"},{"id":"Northern Ireland","label":"Northern Ireland"}]),
        "role": ("Which role best describes your business?", "single_choice", [{"id":k,"label":v} for k,v in ROLES.items()]),
        "activities": ("What does the operation do with waste?", "multi_choice", [{"id":k,"label":v["label"]} for k,v in ACTIVITIES.items()]),
        "site_location": ("Where is the site or operation?", "text", []),
        "waste_types": ("What waste types or codes are involved?", "text", []),
        "hazardous_status": ("Could hazardous waste be involved?", "single_choice", [{"id":"true","label":"Yes"},{"id":"false","label":"No"}]),
        "authorisation_status": ("What authorisation does the site currently rely on?", "single_choice", [{"id":x,"label":x.title()} for x in ("permit","exemption","licence","none","other")]),
    }
    title, kind, options = descriptors[field]
    return {"id":field,"title":title,"type":kind,"options":options,"required":True}


def _extend_case(case_store: Any, case_ref: str, expires_at_epoch: int) -> None:
    if not case_store.extend(case_ref, expires_at_epoch=expires_at_epoch):
        raise RuntimeError("case_expired")


def register_mobile_routes(server: Any, *, case_store: Any, runtime_dir: Path) -> None:
    from starlette.responses import JSONResponse
    verifier=GooglePlayVerifier()
    reports=MobilePlayReports(runtime_dir/"mobile_play_reports.sqlite3",verifier)

    @server.custom_route("/api/mobile/v1/capabilities",methods=["GET"],name="mobile-capabilities")
    async def capabilities(_request):
        return JSONResponse({"product":"RegEvidenceHub Waste","flow":"server_driven_route_readiness","questions":[_question(x) for x in ("nation","role","activities")],"play_billing":{"available":verifier.configured,"product_id":PRODUCT_ID,"package_name":PACKAGE_NAME,"product_type":"one_time_consumable"},"report_access_hours":24,"stripe_available_in_android":False,"boundary":"Preflight information only; not legal advice or a permit, registration or regulator decision."},headers={"Cache-Control":"no-store"})

    @server.custom_route("/api/mobile/v1/readiness",methods=["POST"],name="mobile-readiness")
    async def readiness(request):
        try:
            body=await request.json()
            if not isinstance(body,dict): raise ValueError
        except Exception: return JSONResponse({"status":"invalid_request"},status_code=422)
        payload={k:v for k,v in body.items() if k in {"nation","role","activities","site_location","waste_types","hazardous_status","authorisation_status"}}
        result=waste_preflight(payload)
        missing=[f for f in result.get("findings",[]) if f.get("severity")=="blocking" and f.get("status")=="missing"]
        field_map={"SCOPE-001":"nation","ROLE-002":"role","ACTIVITY-002":"activities","FACT-SITE_LOCATION":"site_location","FACT-WASTE_TYPES":"waste_types","FACT-HAZARDOUS_STATUS":"hazardous_status","AUTH-001":"authorisation_status"}
        next_field=next((field_map.get(item.get("code")) for item in missing if field_map.get(item.get("code"))),None)
        result_decision=result.get("decision",{})
        if result_decision.get("route") == "OUT_OF_SCOPE":
            summary={"state":"review_needed","title":"Outside current scope","route":result_decision.get("route"),"message":result_decision.get("conclusion"),"source_health":result.get("source_health")}
            return JSONResponse({"status":"out_of_scope","result":summary,"case_ref":None,"report_available":False},headers={"Cache-Control":"no-store"})
        if next_field:
            summary={"state":"more_information_needed","title":"More information needed","route":result_decision.get("route"),"message":missing[0].get("message","Add the missing fact to continue."),"source_health":result.get("source_health")}
            if body.get("stop_on_missing") == next_field:
                summary.update({"status":result_decision.get("status"),"findings":result.get("findings",[]),"evidence":result.get("evidence",[]),"next_actions":result.get("next_actions",[])})
                return JSONResponse({"status":"more_information_needed","result":summary,"case_ref":None,"report_available":False},headers={"Cache-Control":"no-store"})
            return JSONResponse({"status":"more_information_needed","next_question":_question(next_field),"result":summary,"case_ref":None,"report_available":False},headers={"Cache-Control":"no-store"})
        state="current_source_not_verified" if not result.get("source_health",{}).get("decision_usable") else "review_needed" if result_decision.get("status")!="SCREENING_COMPLETE_REVIEW_REQUIRED" else "route_identified"
        summary={"state":state,"title":{"route_identified":"Route identified","review_needed":"Review needed","current_source_not_verified":"Current source not verified"}[state],"route":result_decision.get("route"),"status":result_decision.get("status"),"message":result_decision.get("conclusion"),"findings":result.get("findings",[]),"evidence":result.get("evidence",[]),"source_health":result.get("source_health"),"next_actions":result.get("next_actions",[])}
        form={k: ("true" if v is True else "false" if v is False else ", ".join(v) if isinstance(v,list) else str(v)) for k,v in payload.items()}
        for activity in payload.get("activities", []): form[f"activity_{activity}"] = "true"
        form["facts_complete"]="true"
        human_payload,errors=validate_form(form)
        if errors or human_payload is None: return JSONResponse({"status":"invalid_request","errors":errors},status_code=422)
        case=case_store.create(action="waste_case_preflight",workflow="waste_rule_preflight",payload=human_payload,source_bucket="android",classification="confirmed_external",owner_test=False)
        return JSONResponse({"status":"ready","result":summary,"case_ref":case.state_ref,"report_available":True},headers={"Cache-Control":"no-store"})

    async def parse(request):
        reports.purge_expired()
        try:
            body=await request.json(); case_ref,token=body.get("case_ref"),body.get("purchase_token")
            case=case_store.get(case_ref) if isinstance(case_ref,str) else None
            if not isinstance(token,str) or case is None or case.workflow!="waste_rule_preflight": return None
            return case_ref,token,case
        except Exception:return None

    @server.custom_route("/api/mobile/v1/play/redeem",methods=["POST"],name="mobile-play-redeem")
    async def redeem(request):
        parsed=await parse(request)
        if parsed is None:return JSONResponse({"status":"case_not_found","report_granted":False},status_code=404)
        case_ref,token,case=parsed
        grant_expiry=int(time.time())+86400
        status,result=reports.redeem(case_ref=case_ref,token=token,expires_at_epoch=grant_expiry,on_grant=lambda: _extend_case(case_store,case_ref,grant_expiry),report_factory=lambda:waste_preflight(dict(case.payload))|{"boundary":"Preflight information only; not a permit, registration or regulator decision, or legal advice."})
        return JSONResponse(result,status_code=status,headers={"Cache-Control":"no-store"})

    @server.custom_route("/api/mobile/v1/report/recover",methods=["POST"],name="mobile-report-recovery")
    async def recover(request):
        parsed=await parse(request)
        if parsed is None:return JSONResponse({"status":"case_not_found","report_granted":False},status_code=404)
        status,result=reports.recover(case_ref=parsed[0],token=parsed[1])
        return JSONResponse(result,status_code=status,headers={"Cache-Control":"no-store"})
