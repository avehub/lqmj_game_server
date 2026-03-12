import asyncio
import os
import random
import time
import urllib.request
import urllib.error
import json
import asyncio
from datetime import datetime

BASE_URL = "http://192.168.113.165:8989/"
PREFIX = "luckyGame"
DEFAULT_PLATFORM = int(os.environ.get("LG_PLATFORM", "1"))
DEFAULT_C_OS = os.environ.get("LG_C_OS", "ios")
DEFAULT_C_VER = os.environ.get("LG_C_VER", "1.0.0")

def _post_json(url, payload, headers=None, timeout: int = 10):
    body = json.dumps(payload).encode("utf-8")
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = resp.getcode()
        text = resp.read().decode("utf-8")
        return status, json.loads(text)

def _get_json(url, headers=None, timeout: int = 10):
    hdrs = {}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = resp.getcode()
        text = resp.read().decode("utf-8")
        return status, json.loads(text)

def _post_with_fallback(paths, payload, headers=None, timeout: int = 10):
    last_err = None
    for url in paths:
        try:
            return _post_json(url, payload, headers=headers, timeout=timeout)
        except Exception as e:
            last_err = e
    raise last_err

def _get_with_fallback(paths, headers=None, timeout: int = 10):
    last_err = None
    for url in paths:
        try:
            return _get_json(url, headers=headers, timeout=timeout)
        except Exception as e:
            last_err = e
    raise last_err

def login_guest(platform: int, device_id: str):
    p1 = f"{BASE_URL}/{PREFIX}/LoginByGuest/?platform={platform}&c_os={DEFAULT_C_OS}&c_uid=0&c_ver={DEFAULT_C_VER}"
    p2 = f"{BASE_URL}/LoginByGuest/?platform={platform}&c_os={DEFAULT_C_OS}&c_uid=0&c_ver={DEFAULT_C_VER}"
    p3 = f"{BASE_URL}/{PREFIX}/LoginByGuest?platform={platform}&c_os={DEFAULT_C_OS}&c_uid=0&c_ver={DEFAULT_C_VER}"
    p4 = f"{BASE_URL}/LoginByGuest?platform={platform}&c_os={DEFAULT_C_OS}&c_uid=0&c_ver={DEFAULT_C_VER}"
    code, j = _post_with_fallback([p1, p2, p3, p4], {"device_id": device_id})
    d = j.get("data") or {}
    u = d.get("user_info") or {}
    return u.get("token"), u.get("uid"), j

def get_current_cycle_id(token, uid, platform=DEFAULT_PLATFORM, c_os=DEFAULT_C_OS, c_ver=DEFAULT_C_VER):
    qs = f"?c_os={c_os}&platform={platform}&c_uid={uid}&c_ver={c_ver}"
    p1 = f"{BASE_URL}/{PREFIX}/TournamentUserPoint/{qs}"
    p2 = f"{BASE_URL}/TournamentUserPoint/{qs}"
    try:
        code, j = _get_with_fallback([p1, p2], headers={"Authorization": token})
        d = j.get("data") or {}
        cid = d.get("cycle_id") or 0
        if cid:
            return cid
    except Exception:
        pass
    c1 = f"{BASE_URL}/{PREFIX}/TournamentConfig/{qs}"
    c2 = f"{BASE_URL}/TournamentConfig/{qs}"
    code, j = _get_with_fallback([c1, c2], headers={"Authorization": token})
    d = j.get("data") or {}
    cycles = d.get("cycle") or []
    if isinstance(cycles, list) and cycles:
        live = [c for c in cycles if c.get("status") == 1]
        target = live[0] if live else cycles[0]
        return target.get("id") or 0
    return 0

def join_tournament(token, uid, cycle_id=None, pid=0, platform=DEFAULT_PLATFORM, c_os=DEFAULT_C_OS, c_ver=DEFAULT_C_VER):
    qs = f"?c_os={c_os}&platform={platform}&c_uid={uid}&c_ver={c_ver}"
    p1 = f"{BASE_URL}/{PREFIX}/JoinTournament/{qs}"
    p2 = f"{BASE_URL}/JoinTournament/{qs}"
    headers = {"Authorization": token}
    payload = {"cycle_id": cycle_id, "pid": pid}
    return _post_with_fallback([p1, p2], payload, headers=headers)

def simulate_once():
    device_id = f"dev_{random.randint(100000,999999)}"
    try:
        token, uid, login_resp = login_guest(DEFAULT_PLATFORM, device_id)
        print(json.dumps({"login": login_resp}, ensure_ascii=False))
    except Exception:
        token = os.environ.get("LG_TOKEN", "")
        uid = int(os.environ.get("LG_UID", "0"))
        if not token or uid <= 0:
            print(json.dumps({"error": "login_failed", "hint": "需要提供 LG_TOKEN 与 LG_UID 环境变量或开启游客登录路由"}, ensure_ascii=False))
            return
    cycle_id = get_current_cycle_id(token, uid, DEFAULT_PLATFORM, DEFAULT_C_OS, DEFAULT_C_VER)
    code, resp = join_tournament(token, uid, cycle_id=cycle_id)
    print(json.dumps({"uid": uid, "code": code, "resp": resp}, ensure_ascii=False))

async def pressure_test(total: int = 100, concurrency: int = 20, platform: int = DEFAULT_PLATFORM):
    sem = asyncio.Semaphore(concurrency)
    results = []
    async def run_one(i: int):
        async with sem:
            device_id = f"dev_{i}_{random.randint(100000,999999)}"
            token, uid, _ = login_guest(platform, device_id)
            ts = time.perf_counter()
            code, resp = join_tournament(token, uid, platform=platform)
            dur = time.perf_counter() - ts
            return {"i": i, "uid": uid, "code": code, "dur_ms": int(dur * 1000), "msg": resp.get("msg")}
    tasks = [asyncio.create_task(run_one(i)) for i in range(total)]
    for t in asyncio.as_completed(tasks):
        r = await t
        results.append(r)
    ok = sum(1 for r in results if r["code"] == 200 and (r.get("msg") in (None, "", "PASS")))
    fail = len(results) - ok
    p50 = sorted(r["dur_ms"] for r in results)[int(0.5 * len(results))] if results else 0
    p90 = sorted(r["dur_ms"] for r in results)[int(0.9 * len(results))] if results else 0
    summary = {"total": len(results), "success": ok, "fail": fail, "p50_ms": p50, "p90_ms": p90}
    print(json.dumps({"summary": summary, "samples": results[:10]}, ensure_ascii=False))

async def init_db_conn():
    from tortoise import Tortoise
    from common.public.conf import CONF_DB
    await Tortoise.init(config={'apps': {"lucky_game": {'models': ["lucky_game.model_db.main", "lucky_game.model_db.extra"]}},
                                'connections': CONF_DB, 'use_tz': False, 'timezone': "UTC"})

def get_rds_client():
    import redis.asyncio as redis
    from common.public.conf import CONF_RDS
    cfg = CONF_RDS['default'].copy()
    cfg.pop("use_block", None)
    return redis.Redis(**cfg)

async def pick_cycle_id():
    from lucky_game.model_db.main import TournamentCycle
    data = await TournamentCycle.filter(status=1).order_by("id").values()
    if data:
        return data[0]["id"]
    data = await TournamentCycle.all().order_by("id").values()
    return data[0]["id"] if data else 0

async def direct_register(uid, cycle_id=None, pid=0):
    from lucky_game.model_db.main import TournamentRegistration
    if not cycle_id:
        cycle_id = await pick_cycle_id()
    exist = await TournamentRegistration.filter(cycle_id=cycle_id, uid=uid).count()
    if exist:
        return {"cycle_id": cycle_id, "uid": uid, "registered": True}
    data = {"cycle_id": cycle_id, "uid": uid, "pid": pid, "register_type": 1,
            "register_status": 1, "register_time": datetime.now()}
    new = await TournamentRegistration.add_one(data)
    async with get_rds_client() as client:
        await client.sadd(f"tournament_registration:{cycle_id}", uid)
    return {"cycle_id": cycle_id, "uid": uid, "registered": True, "row": bool(new)}

async def simulate_match(uid, competition_id=None, with_room: bool = True):
    from lucky_game.model_db.main import ConfCompetition
    async with get_rds_client() as client:
        if not competition_id:
            data = await ConfCompetition.filter().order_by("id").values()
            competition_id = data[0]["id"] if data else 1
        info = {"competition_id": competition_id, "timestamp": int(datetime.now().timestamp()), "rank": 0}
        if with_room:
            match_room_id = f"{random.randint(1000000, 9999999)}"
            info["match_room_id"] = match_room_id
            await client.sadd("match_room_number", match_room_id)
        await client.hset("IN_MATCH", str(uid), json.dumps(info, ensure_ascii=False))
    return {"uid": uid, "competition_id": competition_id, "in_match": True}

if __name__ == "__main__":
    mode = os.environ.get("LG_MODE", "direct")
    if mode == "simulate":
        simulate_once()
    else:
        if mode == "pressure":
            total = int(os.environ.get("LG_TOTAL", "100"))
            conc = int(os.environ.get("LG_CONC", "20"))
            asyncio.run(pressure_test(total=total, concurrency=conc))
        elif mode == "direct":
            async def main_direct():
                uid = int(os.environ.get("LG_UID", "0"))
                cycle_id = int(os.environ.get("LG_CYCLE_ID", "0")) or None
                comp_id = int(os.environ.get("LG_COMP_ID", "0")) or None
                pid = int(os.environ.get("LG_PID", "0"))
                await init_db_conn()
                out1 = await direct_register(uid, cycle_id=cycle_id, pid=pid)
                out2 = await simulate_match(uid, competition_id=comp_id, with_room=True)
                print(json.dumps({"register": out1, "match": out2}, ensure_ascii=False))
                from tortoise import Tortoise
                await Tortoise.close_connections()
            asyncio.run(main_direct())
