import React, { useState, useEffect, useRef } from 'react';
import { 
  PanelLeftClose, 
  PanelLeftOpen, 
  Plus, 
  ArrowUp, 
  Paperclip, 
  ChevronRight, 
  FileText, 
  FileCode, 
  Download, 
  ExternalLink, 
  X, 
  ShieldCheck, 
  Database,
  Eye,
  Check
} from 'lucide-react';

// Knowledge Base Documents in ChromaDB (On-Premise)
const INITIAL_DATABASE_DOCS = [
  { name: 'ASME_B31_3_Process_Piping_Standard.pdf', size: '4.2 MB', date: 'Indexed 2d ago', type: 'standard' },
  { name: 'Refinery_SOP_Turnaround_Maintenance.docx', size: '1.1 MB', date: 'Indexed 5d ago', type: 'sop' },
  { name: 'Crude_Distillation_Unit_Manual_CDU102.pdf', size: '8.4 MB', date: 'Indexed 1w ago', type: 'manual' },
  { name: 'P_and_ID_Flare_Header_Isolation.dwg', size: '18.6 MB', date: 'Indexed 2w ago', type: 'schematic' }
];

// Presets & Active Conversations
const CONVERSATIONS = {
  'cdu-102': {
    id: 'cdu-102',
    title: 'CDU-102 Ultrasonic Inspection',
    query: 'Audit the scanned ultrasonic thickness inspection report for Crude Distillation Unit (CDU-102). Calculate the remaining corrosion allowance against ASME B31.3 safety margins, and draft a formal sign-off memorandum for the Chief Maintenance Engineer.',
    file: { name: 'cdu_102_ultrasonic_scan.pdf', size: '1.8 MB' },
    activeStage: 4, // 1=Plan, 2=Act, 3=Observe, 4=Deliverable
    nodes: [
      {
        id: 'plan',
        label: 'Plan',
        model: 'Model Router (Heuristics + Qwen 2.5 3B)',
        reason: 'Classified confidential document request into multi-step OCR extraction, mathematical corrosion calculation, and formal memorandum drafting.'
      },
      {
        id: 'act',
        label: 'Act',
        model: 'Tesseract OCR + PyMuPDF Engine',
        reason: 'Parsed high-resolution scan of ultrasonic gauge logs without outbound network sockets. Extracted 4 component thickness measurements.'
      },
      {
        id: 'observe',
        label: 'Observe',
        model: 'Qwen 2.5 3B (Reasoning Model)',
        reason: 'Evaluated Shell Plate C-102 (6.55mm) against ASME B31.3 minimum safety thickness (6.40mm). Computed 0.15mm remaining corrosion allowance.'
      },
      {
        id: 'deliverable',
        label: 'Deliverable',
        model: 'python-docx Sovereign Builder',
        reason: 'Synthesized executive approval memorandum formatted to PSU refinery specifications with cryptographic on-premise hash.'
      }
    ],
    prose: (
      <>
        <p>
          I have completed the audit of the non-destructive ultrasonic testing (UTT) records for Crude Distillation Unit (CDU-102). All optical character recognition and thickness calculations were performed locally on-premises without external network transmission.
        </p>

        <h3 className="prose-heading">1. Thickness Measurements & Degradation Analysis</h3>
        <p>
          The ultrasonic sensor array recorded readings across four primary structural nodes. While the majority of the vessel remains within standard operational allowances, Shell Plate C-102 exhibits accelerated localized wall thinning:
        </p>

        <table className="prose-table">
          <thead>
            <tr>
              <th>Vessel Location</th>
              <th>Nominal Thickness</th>
              <th>Measured (UTT)</th>
              <th>ASME B31.3 Min</th>
              <th>Operating Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Elbow E-101</td>
              <td>8.00 mm</td>
              <td>7.82 mm</td>
              <td>6.40 mm</td>
              <td>Nominal (+1.42 mm)</td>
            </tr>
            <tr style={{ color: 'var(--accent-terracotta)' }}>
              <td>Shell Plate C-102</td>
              <td>8.00 mm</td>
              <td>6.55 mm</td>
              <td>6.40 mm</td>
              <td>Critical Margin (+0.15 mm)</td>
            </tr>
            <tr>
              <td>Nozzle N-04</td>
              <td>7.50 mm</td>
              <td>7.20 mm</td>
              <td>6.00 mm</td>
              <td>Nominal (+1.20 mm)</td>
            </tr>
            <tr>
              <td>Bottom Head B-1</td>
              <td>8.20 mm</td>
              <td>8.10 mm</td>
              <td>6.50 mm</td>
              <td>Nominal (+1.60 mm)</td>
            </tr>
          </tbody>
        </table>

        <h3 className="prose-heading">2. Risk Assessment & Engineering Recommendation</h3>
        <p>
          Shell Plate C-102 currently retains an operational corrosion margin of only <strong>0.15 mm</strong>. Based on an annualized wall loss rate of 0.36 mm/year, the vessel will breach the mandatory retirement threshold within approximately 5 months of continuous service.
        </p>
        <p>
          I recommend continuous operation for up to 90 days conditioned upon bi-weekly ultrasonic logging at Node C-102. Full weld overlay restoration should be prioritized during the upcoming scheduled refinery turnaround.
        </p>
        <p>
          The complete executive approval memorandum has been generated and validated below.
        </p>
      </>
    ),
    deliverable: {
      name: 'Approval_Note_CDU102_NDT.docx',
      size: '24 KB',
      type: 'docx'
    }
  },
  'valve-dp': {
    id: 'valve-dp',
    title: 'Valve Delta-P Verification',
    query: 'Verify the Darcy-Weisbach pressure drop across the 6-inch crude feed isolation valve (XV-104A) at 450 m³/h throughput. Confirm if Delta-P is within the 4.50 bar threshold.',
    file: null,
    activeStage: 4,
    nodes: [
      {
        id: 'plan',
        label: 'Plan',
        model: 'Model Router (Heuristics)',
        reason: 'Routed to local coding sandbox for isolated mathematical verification.'
      },
      {
        id: 'act',
        label: 'Act',
        model: 'Qwen 2.5 Coder 1.5B',
        reason: 'Synthesized Darcy-Weisbach fluid velocity and pressure loss script.'
      },
      {
        id: 'observe',
        label: 'Observe',
        model: 'Local Python Sandbox',
        reason: 'Executed script in restricted subprocess. Exit Code 0, Delta-P computed at 4.28 bar.'
      },
      {
        id: 'deliverable',
        label: 'Deliverable',
        model: 'Sovereign Runtime',
        reason: 'Compiled verified execution output and safety margin calculation.'
      }
    ],
    prose: (
      <>
        <p>
          I have written and executed the fluid dynamics calculation within the local Python sandbox to evaluate pressure drop across isolation valve XV-104A.
        </p>

        <div className="prose-code-block">
{`# Sandboxed Python Execution - Darcy-Weisbach Verification
Flow Rate: 450.00 m³/h | Nominal Bore: 6.00 in (0.1524 m)
Fluid Velocity: 6.87 m/s | Reynolds Number: 1.42e5 (Turbulent)
Calculated Delta-P: 4.28 bar (Threshold Limit: 4.50 bar)
Verification Result: PASS (Margin: +0.22 bar)`}
        </div>

        <p>
          The computed pressure loss of <strong>4.28 bar</strong> complies with the system operating specification, leaving a 4.9% safety margin under maximum throughput conditions.
        </p>
      </>
    ),
    deliverable: {
      name: 'valve_dp_verification.py',
      size: '2.8 KB',
      type: 'py'
    }
  },
  'pid-flare': {
    id: 'pid-flare',
    title: 'P&ID Flare Line Review',
    query: 'Inspect the P&ID drawing for the flare knock-out drum bypass. Confirm whether emergency isolation valves are configured with lock-closed indicators.',
    file: { name: 'pid_sample_diagram.png', size: '520 KB' },
    activeStage: 4,
    nodes: [
      {
        id: 'plan',
        label: 'Plan',
        model: 'Model Router',
        reason: 'Image input routed to local Moondream 1.6B vision model.'
      },
      {
        id: 'act',
        label: 'Act',
        model: 'Moondream 1.6B Vision',
        reason: 'Extracted valve symbols and tag annotations from schematic.'
      },
      {
        id: 'observe',
        label: 'Observe',
        model: 'Qwen 2.5 3B',
        reason: 'Cross-checked tag BV-108 against refinery lockout SOP-304.'
      },
      {
        id: 'deliverable',
        label: 'Deliverable',
        model: 'Sovereign Knowledge Engine',
        reason: 'Generated compliance assessment matrix.'
      }
    ],
    prose: (
      <>
        <p>
          I have analyzed the Piping & Instrumentation Diagram (P&ID) for the flare header relief loop using the on-premise Moondream vision model.
        </p>
        <p>
          The inspection confirms that manual bypass valve <strong>BV-108</strong> is correctly designated as <strong>LC (Locked Closed)</strong> with mechanical car-seal protection in accordance with refinery safety protocol SOP-VR-304.
        </p>
      </>
    ),
    deliverable: {
      name: 'pid_compliance_audit.xlsx',
      size: '14 KB',
      type: 'xlsx'
    }
  }
};

export default function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [currentView, setCurrentView] = useState('landing'); // 'landing' (Screen 1) or 'active' (Screen 2)
  const [activeChatId, setActiveChatId] = useState(null);
  const [promptText, setPromptText] = useState('');
  const [attachedFile, setAttachedFile] = useState(null);
  const [activePopoverNode, setActivePopoverNode] = useState(null);
  const [databaseDocs, setDatabaseDocs] = useState(INITIAL_DATABASE_DOCS);
  
  const fileInputRef = useRef(null);
  const dbInputRef = useRef(null);

  // Switch to Screen 2 (Active Conversation)
  const handleSelectConversation = (chatId) => {
    setActiveChatId(chatId);
    setCurrentView('active');
    setActivePopoverNode(null);
  };

  // Switch to Screen 1 (Landing / New Chat state)
  const handleNewChat = () => {
    setActiveChatId(null);
    setPromptText('');
    setAttachedFile(null);
    setCurrentView('landing');
    setActivePopoverNode(null);
  };

  // Submit Prompt
  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!promptText.trim() && !attachedFile) return;

    // Route to CDU-102 scenario or valve-dp
    const targetChatId = promptText.toLowerCase().includes('valve') ? 'valve-dp' : 
                         attachedFile?.name.includes('png') ? 'pid-flare' : 'cdu-102';
    
    handleSelectConversation(targetChatId);
  };

  // Upload to Knowledge Base Database
  const handleUploadToDatabase = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const newDoc = {
        name: file.name,
        size: `${(file.size / 1024).toFixed(0)} KB`,
        date: 'Indexed just now',
        type: file.name.split('.').pop()
      };
      setDatabaseDocs(prev => [newDoc, ...prev]);
    }
  };

  // Download deliverable
  const handleDownload = (filename) => {
    const blob = new Blob([
      `SOVEREIGN AIR-GAPPED WORKBENCH DELIVERABLE\n` +
      `File: ${filename}\n` +
      `Status: VERIFIED ON-PREMISE\n` +
      `Zero cloud telemetry. 100% sovereign inference.`
    ], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
  };

  const activeChat = CONVERSATIONS[activeChatId || 'cdu-102'];

  return (
    <div className="app-shell">
      {/* Background Interactive Charcoal Grid Blocks (80px x 80px) */}
      <div className="background-grid-container" aria-hidden="true">
        {Array.from({ length: 140 }).map((_, i) => (
          <div key={i} className="grid-block" />
        ))}
      </div>
      <div className="vignette-overlay" aria-hidden="true" />

      {/* SCREEN 1 & 2: Left Sidebar (Thin, Minimal, Collapsible) */}
      <aside className={`sidebar ${isSidebarOpen ? '' : 'collapsed'}`}>
        <div className="sidebar-header">
          {isSidebarOpen ? (
            <div className="sidebar-brand" onClick={handleNewChat}>
              <div className="brand-monogram">S</div>
              <span className="brand-text">Sovereign</span>
            </div>
          ) : (
            <div className="sidebar-brand" onClick={handleNewChat} title="Sovereign AI">
              <div className="brand-monogram">S</div>
            </div>
          )}

          <button 
            className="toggle-sidebar-btn" 
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            title={isSidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            {isSidebarOpen ? <PanelLeftClose size={15} /> : <PanelLeftOpen size={15} />}
          </button>
        </div>

        {/* + New Chat / Session Button */}
        <button className="new-chat-btn" onClick={handleNewChat} title="New conversation">
          <Plus size={14} />
          {isSidebarOpen && <span>New Session</span>}
        </button>

        {/* Previous Chats History List */}
        {isSidebarOpen && (
          <div className="sidebar-section-label">Previous Chats</div>
        )}

        <div className="chat-history-list">
          {Object.values(CONVERSATIONS).map(chat => (
            <div 
              key={chat.id} 
              className={`chat-item ${currentView === 'active' && activeChatId === chat.id ? 'active' : ''}`}
              onClick={() => handleSelectConversation(chat.id)}
              title={chat.title}
            >
              <FileText size={14} style={{ opacity: 0.7, flexShrink: 0 }} />
              {isSidebarOpen && <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{chat.title}</span>}
            </div>
          ))}
        </div>

        {/* Sidebar Footer: Quiet Air-gap status */}
        <div className="sidebar-footer">
          <div className="airgap-indicator-dot" />
          {isSidebarOpen && <span>All inference local · 0 calls</span>}
        </div>
      </aside>

      {/* Main Content Viewport */}
      <main className="main-viewport">
        {/* Sticky Minimalist Top Bar */}
        <header className="viewport-topbar">
          <div className="topbar-title">
            {currentView === 'landing' ? (
              <span>Confidential Industrial Workspace</span>
            ) : (
              <span>{activeChat.title}</span>
            )}
          </div>
          <div className="topbar-meta">
            <span className="topbar-badge">OLLAMA RUNTIME</span>
            <span className="topbar-badge">4GB VRAM</span>
            <span style={{ color: 'var(--accent-terracotta)' }}>127.0.0.1 LOCK</span>
          </div>
        </header>

        {/* ================================================================
            SCREEN 1: FRONT PAGE (Landing / New Chat State)
            ================================================================ */}
        {currentView === 'landing' && (
          <div className="frontpage-container">
            {/* Editorial Serif Greeting */}
            <h1 className="greeting-editorial">What confidential task shall we examine?</h1>
            <p className="greeting-sub">
              Sovereign runs small open-weight reasoning and vision models entirely on your premises. No telemetry, zero cloud egress.
            </p>

            {/* Centered Pill Input Box (Rounded pill, subtle border, glassmorphism blur, no fill) */}
            <form className="pill-input-box" onSubmit={handleSubmit}>
              {attachedFile && (
                <span className="attached-tag">
                  <FileText size={11} />
                  <span>{attachedFile.name}</span>
                  <button 
                    type="button" 
                    className="remove-tag-btn" 
                    onClick={() => setAttachedFile(null)}
                  >
                    <X size={11} />
                  </button>
                </span>
              )}

              <input 
                type="text" 
                className="pill-input-field"
                placeholder="How can Sovereign assist with your industrial workflows today?"
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
              />

              <div className="pill-action-group">
                {/* File picker */}
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setAttachedFile({ name: file.name, size: `${(file.size / 1024).toFixed(0)} KB` });
                    }
                  }}
                />

                <button 
                  type="button" 
                  className="pill-icon-btn" 
                  onClick={() => fileInputRef.current?.click()}
                  title="Attach inspection scan, drawing, or code"
                >
                  <Paperclip size={15} />
                </button>

                <button 
                  type="submit" 
                  className="pill-send-btn" 
                  disabled={!promptText.trim() && !attachedFile}
                  title="Submit task"
                >
                  <ArrowUp size={15} />
                </button>
              </div>
            </form>

            {/* Below input: subtle, outlined, not filled + Create button */}
            <button 
              className="create-btn-outlined"
              onClick={() => {
                setPromptText('Audit the scanned ultrasonic thickness inspection report for Crude Distillation Unit (CDU-102).');
                setAttachedFile({ name: 'cdu_102_ultrasonic_scan.pdf', size: '1.8 MB' });
              }}
            >
              <Plus size={13} />
              <span>+ Create with sample inspection scan</span>
            </button>

            {/* Below the Fold: Persistent "Add to Database" Panel */}
            <section className="database-section">
              <div className="database-header">
                <div>
                  <h2 className="database-title">Add to Database</h2>
                  <p className="database-desc">Ingest standards, manuals, and SOPs into the local ChromaDB vector store for sovereign grounding.</p>
                </div>

                <input 
                  type="file" 
                  ref={dbInputRef} 
                  style={{ display: 'none' }}
                  onChange={handleUploadToDatabase}
                />

                {/* Simple Circular + Icon Button */}
                <button 
                  className="circular-add-btn" 
                  onClick={() => dbInputRef.current?.click()}
                  title="Upload document to local vector store"
                >
                  <Plus size={16} />
                </button>
              </div>

              {/* Uploaded Documents List */}
              <div className="documents-list">
                {databaseDocs.map((doc, idx) => (
                  <div key={idx} className="doc-card" title={doc.name}>
                    <Database size={15} style={{ color: 'var(--text-muted)', marginTop: 2, flexShrink: 0 }} />
                    <div className="doc-card-info">
                      <span className="doc-card-name">{doc.name}</span>
                      <span className="doc-card-meta">{doc.size} · {doc.date}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}

        {/* ================================================================
            SCREEN 2: ACTIVE TASK / CONVERSATION VIEW
            ================================================================ */}
        {currentView === 'active' && (
          <div className="conversation-container">
            
            {/* User's Submitted Question Shown Above */}
            <div className="user-query-block">
              <div className="user-query-label">CONFIDENTIAL WORKFLOW PROMPT</div>
              <h2 className="user-query-text">{activeChat.query}</h2>
            </div>

            {/* Top Question / Follow-up Input Bar (Same Pill Style) */}
            <div className="conversation-input-wrapper">
              <form className="pill-input-box" onSubmit={handleSubmit}>
                <input 
                  type="text" 
                  className="pill-input-field"
                  placeholder="Ask a follow-up or refine the calculation..."
                  value={promptText}
                  onChange={(e) => setPromptText(e.target.value)}
                />
                <button 
                  type="submit" 
                  className="pill-send-btn"
                  disabled={!promptText.trim()}
                >
                  <ArrowUp size={15} />
                </button>
              </form>
            </div>

            {/* Agent Process Indicator: Small horizontal row of connected dots */}
            <div className="process-indicator-row">
              {activeChat.nodes.map((node, index) => {
                const isCompleted = activeChat.activeStage > index + 1;
                const isActive = activeChat.activeStage === index + 1;
                const isPopoverOpen = activePopoverNode === node.id;

                return (
                  <React.Fragment key={node.id}>
                    <div 
                      className={`process-node ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''}`}
                      onClick={() => setActivePopoverNode(isPopoverOpen ? null : node.id)}
                      title="Click to view model rationale"
                    >
                      <div className="node-dot" />
                      <span className="node-label">{node.label}</span>

                      {/* Clickable Tooltip / Popover showing model details & rationale */}
                      {isPopoverOpen && (
                        <div className="node-popover" onClick={(e) => e.stopPropagation()}>
                          <div className="popover-stage-title">STAGE: {node.label}</div>
                          <div className="popover-model-name">{node.model}</div>
                          <p className="popover-explanation">{node.reason}</p>
                        </div>
                      )}
                    </div>

                    {index < activeChat.nodes.length - 1 && (
                      <div className="process-connector-arrow">
                        <ChevronRight size={13} />
                      </div>
                    )}
                  </React.Fragment>
                );
              })}
            </div>

            {/* Output Panel: Claude's Reading-Friendly Prose Style */}
            <article className="prose-output-panel">
              {activeChat.prose}
            </article>

            {/* Real-time Deliverable Panel: Simple Horizontal File-Preview Strip at Bottom */}
            {activeChat.deliverable && (
              <div className="deliverable-strip">
                <div className="deliverable-strip-left">
                  <div className="deliverable-icon-box">
                    {activeChat.deliverable.type === 'docx' && <FileText size={17} />}
                    {activeChat.deliverable.type === 'py' && <FileCode size={17} />}
                    {activeChat.deliverable.type === 'xlsx' && <FileText size={17} />}
                  </div>
                  <div>
                    <div className="deliverable-name">{activeChat.deliverable.name}</div>
                    <div className="deliverable-meta">{activeChat.deliverable.size} · Verified Sovereign Deliverable</div>
                  </div>
                </div>

                <div className="deliverable-actions">
                  <button 
                    className="deliverable-action-btn"
                    onClick={() => handleDownload(activeChat.deliverable.name)}
                  >
                    <Download size={13} />
                    <span>Download</span>
                  </button>
                  <button 
                    className="deliverable-action-btn"
                    onClick={() => handleDownload(activeChat.deliverable.name)}
                  >
                    <ExternalLink size={13} />
                    <span>Open</span>
                  </button>
                </div>
              </div>
            )}

          </div>
        )}

      </main>
    </div>
  );
}
