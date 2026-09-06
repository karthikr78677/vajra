# Vajra Architecture (Current State)

Here is a visual flowchart representation of everything we have successfully integrated and built into the Vajra ecosystem up to this point.

```mermaid
flowchart TD
    %% Styling
    classDef user fill:#6366f1,stroke:#fff,stroke-width:2px,color:#fff
    classDef router fill:#8b5cf6,stroke:#fff,stroke-width:2px,color:#fff
    classDef agent fill:#ec4899,stroke:#fff,stroke-width:2px,color:#fff
    classDef tools fill:#14b8a6,stroke:#fff,stroke-width:2px,color:#fff
    classDef external fill:#f59e0b,stroke:#fff,stroke-width:2px,color:#fff
    classDef logic fill:#3b82f6,stroke:#fff,stroke-width:2px,color:#fff

    User(("User Request")):::user --> API["FastAPI Backend\nrouter.py"]:::router
    
    API --> TaskAnalyzer{"Task Analysis\ntask_analysis.py"}:::logic
    
    %% Routes
    TaskAnalyzer -- "TaskType.REASONING" --> ReasoningAgent["Reasoning Agent\n(Qwen2.5 7B / LLaMA)"]:::agent
    TaskAnalyzer -- "TaskType.CODING" --> CodingAgent["Coding Agent\n(Qwen2.5-Coder 1.5B)"]:::agent
    
    %% Reasoning Agent Subsystems
    ReasoningAgent --> Tools{"Tool Execution Loop"}:::logic
    Tools -- "extract_text" --> OCR["Parser & OCR Engine"]:::tools
    Tools -- "analyze_image" --> Vision["Vision Engine\nMoondream"]:::tools
    Tools -- "calculate" --> Calc["Calculator"]:::tools
    Tools -- "read/write/delete" --> FileSystem["File Tool\nDynamic Workspace"]:::tools
    
    OCR --> PDF["PyMuPDF / Tesseract"]:::external
    
    %% Coding Agent Subsystems
    CodingAgent --> Regex["Extract Markdown Code"]:::logic
    Regex --> Sandbox["Sandbox Environment\nsandbox_exec.py"]:::tools
    
    %% Sandbox Logic
    Sandbox --> CheckPerm{"Security Check"}:::logic
    CheckPerm -- "Safe Command" --> Exec["Execute Code\n(Python, Node, PS)"]:::external
    CheckPerm -- "Dangerous Command" --> Pause["Permission Manager\nEvent Paused"]:::logic
    
    %% Permission Flow
    Pause -. "Request Approval" .-> UserUI(("User UI\nTerminal / API")):::user
    UserUI -. "Approve/Deny" .-> Pause
    Pause -- "Approved" --> Exec
    
    %% Auto-fix Loop
    Exec -- "Syntax/Runtime Error" --> AutoFix{"Auto-Fix Loop\n(Max 3 retries)"}:::logic
    AutoFix -- "Send Error to Model" --> CodingAgent
    
    %% Success Return
    Exec -- "Success Output" --> Return["Return Final Output to User"]:::router
    ReasoningAgent -- "final_answer" --> Return
```

### Key Highlights from the Flowchart:
- **Intelligent Routing:** The backend analyzes the task and routes complex reasoning to the large model, and code generation to the smaller, specialized coder model.
- **Vision & OCR (M1/M3):** The Reasoning Agent has full access to the production-grade PyMuPDF/Tesseract text extractor and your teammate's Moondream vision engine.
- **The Coding Loop (M4/Scenario B):** The Coding agent operates in a closed loop. It generates code, the Sandbox executes it in the dynamic workspace, and if it fails, it auto-heals itself up to 3 times.
- **Security Check:** The `PermissionManager` acts as the critical barrier between the Sandbox and Execution, capable of freezing the agent until you provide explicit approval.
