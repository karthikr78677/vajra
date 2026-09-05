from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class TaskType(str, Enum):
    REASONING = "REASONING"
    CODING = "CODING"
    VISION = "VISION"

class UserRequest(BaseModel):
    query: str = Field(description="The natural language query from the user.")
    file_paths: List[str] = Field(default_factory=list, description="Paths to uploaded files (PDFs, images, etc.)")

class TaskAnalysisResult(BaseModel):
    task_type: TaskType = Field(description="The classified task type.")
    reasoning: str = Field(description="Why this task type was selected.")
    extracted_text: Optional[str] = Field(None, description="Any text extracted during preprocessing.")
    confidence_score: float = Field(1.0, description="Confidence score from 0.0 to 1.0")
    is_fallback: bool = Field(False, description="True if a fallback classification method was used.")

class AgentStep(BaseModel):
    thought: str
    action: str
    action_input: Any
    observation: str

class TaskResponse(BaseModel):
    status: str = Field(description="Success or error status.")
    final_output: str = Field(description="The final text response from the agent.")
    generated_files: List[str] = Field(default_factory=list, description="Paths to any generated files (Word, Excel, Code).")
    agent_trace: List[AgentStep] = Field(default_factory=list, description="The steps taken by the agent orchestrator.")
    execution_time_ms: int = Field(0, description="Time taken to execute the task in ms")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the frontend")

# Configuration Schema for model routing
class ModelConfig(BaseModel):
    name: str
    type: str
    description: str

class RouterConfig(BaseModel):
    models: Dict[str, ModelConfig]
    ollama_base_url: str
