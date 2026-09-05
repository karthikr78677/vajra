import logging
import asyncio
from backend.schemas import UserRequest, TaskType
from backend.task_analysis import analyze_task_async
from backend.router import ModelRouter
from tools.sandbox_exec import execute_python
from tools.calculator_tool import calculate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_tests():
    router = ModelRouter()
    
    print("=== Testing Advanced Task Analysis (Hybrid) ===")
    req1 = UserRequest(query="Extract data from this diagram", file_paths=["ocr-text-test.png"])
    res1 = await analyze_task_async(req1, router)
    print(f"Request 1 (Image): {res1.task_type} (Fallback: {res1.is_fallback}) - {res1.reasoning}")
    
    req2 = UserRequest(query="Write a python script to sort an array", file_paths=[])
    res2 = await analyze_task_async(req2, router)
    print(f"Request 2 (Code): {res2.task_type} (Fallback: {res2.is_fallback}) - {res2.reasoning}")

    req3 = UserRequest(query="Is there a bug in the following matrix math algorithm?", file_paths=[])
    res3 = await analyze_task_async(req3, router)
    print(f"Request 3 (Ambiguous/Complex): {res3.task_type} (Fallback: {res3.is_fallback}) - {res3.reasoning}")

    print("\n=== Testing Tools ===")
    calc_res = calculate("25 * 4 + 10")
    print(f"Calculator Tool (25 * 4 + 10): {calc_res}")

    code = "print('Hello from the sandbox!')\nfor i in range(3): print(i)"
    sandbox_res = execute_python(code)
    print(f"Sandbox Exec Tool Output:\n{sandbox_res}")

    print("\n=== Testing Model Router (Async Ollama Connection) ===")
    try:
        print("Sending an async ping to the reasoning model...")
        model_name = router.get_model_for_task(TaskType.REASONING)
        
        response = await router.generate_async(model_name, prompt="Hello! Please reply with exactly one word: 'Ready'.")
        print(f"Model Router Response ({model_name}): {response}")
    except Exception as e:
        print(f"Router Test Failed (Is Ollama running?): {e}")
        
    print("\n=== Interactive Intent Classifier Test ===")
    print("Type 'exit' to quit.")
    while True:
        user_input = input("\nEnter a query to classify: ")
        if user_input.lower().strip() == 'exit':
            break
        if not user_input.strip():
            continue
            
        custom_req = UserRequest(query=user_input, file_paths=[])
        try:
            res = await analyze_task_async(custom_req, router)
            print(f"-> Classified as: {res.task_type}")
            print(f"-> Reason: {res.reasoning} (Fallback Used: {res.is_fallback})")
        except Exception as e:
            print(f"Error classifying: {e}")
            
    await router.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
