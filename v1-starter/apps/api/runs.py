import hashlib
import json
from .models import RunCreate


def canonical_hash(value: dict) -> str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def build_manifest(run: RunCreate, version_record: dict, dataset_record: dict) -> dict:
    return {
        "strategy_id": run.strategy_id,
        "strategy_version": run.strategy_version,
        "code_hash": version_record["code_hash"],
        "config_hash": version_record["config_hash"],
        "dataset_version_id": run.dataset_version_id,
        "dataset_hash": dataset_record["content_hash"],
        "runner_version": run.runner_version,
        "parameters": run.parameters,
        "seed": run.seed,
        "starting_equity": run.starting_equity,
        "trades": [t.model_dump() for t in run.trades],
    }


def execute_manifest(manifest: dict) -> dict:
    trades=manifest["trades"]
    net=[t["pnl_gross"]-t["fees"]-t["slippage"] for t in trades]
    wins=sum(x for x in net if x>0); losses=abs(sum(x for x in net if x<0))
    equity=0.0; peak=0.0; max_dd=0.0
    for x in net:
        equity+=x; peak=max(peak,equity); max_dd=max(max_dd,peak-equity)
    metrics={
        "rr_planned": round(sum(t["planned_reward"]/t["planned_risk"] for t in trades)/len(trades),8),
        "profit_factor_net": round(wins/losses,8) if losses else 999.0,
        "expectancy_net": round(sum(net)/len(net),8),
        "sample_size": len(net),
        "max_drawdown_absolute": round(max_dd,8),
        "max_drawdown_pct": round(100*max_dd/manifest["starting_equity"],8),
        "net_total": round(sum(net),8),
    }
    return metrics


def execute_reproducibly(manifest: dict) -> tuple[dict,str,bool]:
    first=execute_manifest(manifest); second=execute_manifest(manifest)
    a=canonical_hash(first); b=canonical_hash(second)
    return first,a,a==b
