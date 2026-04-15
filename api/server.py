from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent.conversation import ConversationEngine
from agent.improver import ScriptImprover
from memory.analyzer import CallAnalyzer
from memory.database import initialize_db, save_call, get_conversion_rate, fetch_recent_calls


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CallRequest(BaseModel):
    name: str
    persona: str = "skeptical"


class BatchRequest(BaseModel):
    calls: Optional[list[CallRequest]] = None


class BatchResult(BaseModel):
    calls_run: int
    results: list[dict]
    stats: dict


class ImproveResult(BaseModel):
    previous_version: int
    new_version: int
    improvement_summary: dict


class StatsResult(BaseModel):
    version: Optional[int]
    total: int
    converted: int
    rejected: int
    incomplete: int
    rate: float


# ---------------------------------------------------------------------------
# Default demo batch
# ---------------------------------------------------------------------------

DEFAULT_BATCH = [
    CallRequest(name="Marcus", persona="skeptical"),
    CallRequest(name="Priya",  persona="price_sensitive"),
    CallRequest(name="Tom",    persona="hostile"),
    CallRequest(name="Lisa",   persona="friendly"),
]


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_db()
    yield

app = FastAPI(
    title="PulseIQ Self-Improving Sales Agent",
    description="API for running simulated sales calls, analyzing outcomes, and iteratively improving the sales script.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "service": "PulseIQ Sales Agent API"}


@app.post("/run-batch", response_model=BatchResult)
def run_batch(voice: bool = False):
    calls_to_run = DEFAULT_BATCH

    engine = ConversationEngine(voice_mode=voice)
    analyzer = CallAnalyzer()

    results = []
    for call in calls_to_run:
        try:
            result = engine.run(prospect_name=call.name, persona=call.persona)
            analysis = analyzer.analyze(result)
            call_id = save_call(result, analysis)

            results.append({
                "call_id": call_id,
                "prospect": call.name,
                "persona": call.persona,
                "outcome": result["outcome"],
                "script_version": result["script_version"],
                "turn_count": result["turn_count"],
                "objections_raised": analysis.get("objections_raised", []),
                "call_quality": analysis.get("call_quality"),
                "improvement_note": analysis.get("improvement_note"),
            })
        except Exception as e:
            results.append({
                "prospect": call.name,
                "persona": call.persona,
                "error": str(e),
            })

    current_version = engine.script["version"]
    stats = get_conversion_rate(script_version=current_version)

    return BatchResult(calls_run=len(results), results=results, stats=stats)


@app.post("/improve", response_model=ImproveResult)
def improve_script():
    try:
        improver = ScriptImprover()
        previous_version = improver.script["version"]
        new_script = improver.improve()

        stats = get_conversion_rate(script_version=previous_version)

        return ImproveResult(
            previous_version=previous_version,
            new_version=new_script["version"],
            improvement_summary={
                "v1_conversion_rate": stats["rate"],
                "calls_analyzed": stats["total"],
                "converted": stats["converted"],
                "rejected": stats["rejected"],
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=StatsResult)
def get_stats(version: Optional[int] = None):
    stats = get_conversion_rate(script_version=version)
    return StatsResult(
        version=version,
        total=stats["total"],
        converted=stats["converted"],
        rejected=stats["rejected"],
        incomplete=stats["incomplete"],
        rate=stats["rate"],
    )


@app.get("/calls/recent")
def recent_calls(limit: int = 10):
    calls = fetch_recent_calls(limit=limit)
    return {"calls": calls}
