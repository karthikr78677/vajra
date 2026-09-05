from fastapi import FastAPI, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
import logging
import time
from backend.schemas import UserRequest, TaskAnalysisResult, TaskResponse, TaskType
from backend.task_analysis import analyze_task_async
from backend.router import ModelRouter
from agents.orchestrator import AgentOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vajra - Air-gapped AI Workbench (Advanced M1)")
router = ModelRouter()

@app.on_event("shutdown")
async def shutdown_event():
    await router.close()

@app.post("/analyze", response_model=TaskAnalysisResult)
async def api_analyze_task(request: UserRequest):
    """
    Endpoint to classify a user request using hybrid heuristics + LLM fallback.
    """
    try:
        return await analyze_task_async(request, router)
    except Exception as e:
        logger.error(f"Error in task analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process", response_model=TaskResponse)
async def api_process_task(request: UserRequest):
    """
    Fully integrated endpoint that analyzes the task and runs the Agent Orchestrator.
    """
    start_time = time.time()
    try:
        # 1. Analyze the task
        analysis = await analyze_task_async(request, router)
        logger.info(f"Task classified as {analysis.task_type} (Fallback: {analysis.is_fallback})")
        
        # 2. Run the Orchestrator
        orchestrator = AgentOrchestrator(router)
        final_output, trace = await orchestrator.run_async(request.query, analysis.task_type)
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return TaskResponse(
            status="success",
            final_output=final_output,
            generated_files=[],
            agent_trace=trace,
            execution_time_ms=execution_time,
            metadata={"classification": analysis.model_dump()}
        )
    except Exception as e:
        logger.error(f"Error in processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stream")
async def api_stream_task(request: Request):
    """
    SSE endpoint for streaming responses in real-time.
    """
    body = await request.json()
    query = body.get("query", "")
    
    async def event_generator():
        messages = [{"role": "user", "content": query}]
        try:
            model_name = router.get_model_for_task(TaskType.REASONING)
            async for chunk in router.chat_stream_async(model_name, messages):
                yield {"data": chunk}
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {"event": "error", "data": str(e)}
            
    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
