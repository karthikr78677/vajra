import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  PanelLeftClose, PanelLeftOpen, Plus, ArrowUp, ArrowRight,
  Paperclip, ChevronRight, Play, FileText, FileCode, Download,
  ExternalLink, X, ShieldCheck, Database, Check, Loader2,
  Upload, FolderOpen, Link, Image, Cloud, Folder, Settings,
  Zap, Activity, LayoutGrid, MessageSquare, Clock, Send,
  CornerDownLeft
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api } from './api';
import './App.css';

// ─── File Type Configs ────────────────────────────────────────────────────────
const SOURCE_FILE_CONFIGS = {
  upload: {
    accept: '.csv,.pdf,.json,.docx,.xlsx,.txt,.parquet,.mp3,.wav,.ogg,.md',
    multiple: true,
    dropTitle: 'Drop CSV, PDF, DOCX, JSON, Parquet, or Audio transcripts here',
    dropSub: 'Supports multi-file upload up to 250 MB per batch · SOC-2 Type II encrypted',
  },
  media: {
    accept: '.png,.jpg,.jpeg,.webp,.gif,.bmp,.tiff,.svg,.pdf,.csv,.parquet,.json',
    multiple: true,
    dropTitle: 'Drop images (PNG, JPG, WEBP, TIFF, SVG) or dataset files (CSV, Parquet, JSON)',
    dropSub: 'Multi-modal visual embeddings — multiple files supported up to 250 MB per batch',
  },
};

const IMAGE_EXTS = new Set(['png','jpg','jpeg','webp','gif','bmp','tiff','svg']);

// ─── Helpers ──────────────────────────────────────────────────────────────────
function fileIcon(name) {
  const ext = name.split('.').pop().toLowerCase();
  if (IMAGE_EXTS.has(ext)) return <Image size={12} />;
  if (['py','js','jsx','ts','tsx'].includes(ext)) return <FileCode size={12} />;
  return <FileText size={12} />;
}

function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function relTime(ts) {
  const diff = Date.now() - ts;
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ─── Knowledge Base Documents (ChromaDB) ─────────────────────────────────────
const INITIAL_DATABASE_DOCS = [];

// ─── Preset Conversations (messages[] model) ──────────────────────────────────
function makeAssistantMsg(nodes, proseJsx, deliverable) {
  return {
    id: `msg-${Date.now()}-${Math.random()}`,
    role: 'assistant',
    nodes,
    proseJsx,
    deliverable,
    timestamp: Date.now() - 120000,
  };
}

function makeUserMsg(content, files = []) {
  return {
    id: `msg-${Date.now()}-${Math.random()}`,
    role: 'user',
    content,
    files,
    timestamp: Date.now() - 130000,
  };
}

const PRESET_CONVERSATIONS = {
  'cdu-102': {
    id: 'cdu-102',
    title: 'CDU-102 Ultrasonic Inspection',
    timestamp: Date.now() - 7200000,
    messages: [
      makeUserMsg(
        'Audit the scanned ultrasonic thickness inspection report for Crude Distillation Unit (CDU-102). Calculate the remaining corrosion allowance against ASME B31.3 safety margins, and draft a formal sign-off memorandum for the Chief Maintenance Engineer.',
        [{ name: 'cdu_102_ultrasonic_scan.pdf', size: 1887436 }]
      ),
      makeAssistantMsg(
        [
          { id: 'plan', label: 'Plan', model: 'Model Router (Heuristics + Qwen 2.5 3B)', reason: 'Classified confidential document request into multi-step OCR extraction, mathematical corrosion calculation, and formal memorandum drafting.' },
          { id: 'act', label: 'Act', model: 'Tesseract OCR + PyMuPDF Engine', reason: 'Parsed high-resolution scan of ultrasonic gauge logs without outbound network sockets. Extracted 4 component thickness measurements.' },
          { id: 'observe', label: 'Observe', model: 'Qwen 2.5 3B (Reasoning Model)', reason: 'Evaluated Shell Plate C-102 (6.55mm) against ASME B31.3 minimum safety thickness (6.40mm). Computed 0.15mm remaining corrosion allowance.' },
          { id: 'deliverable', label: 'Deliverable', model: 'python-docx Sovereign Builder', reason: 'Synthesized executive approval memorandum formatted to PSU refinery specifications with cryptographic on-premise hash.' },
        ],
        <>
          <p>I have completed the audit of the non-destructive ultrasonic testing (UTT) records for Crude Distillation Unit (CDU-102). All optical character recognition and thickness calculations were performed locally on-premises without external network transmission.</p>
          <h3 className="prose-heading">1. Thickness Measurements &amp; Degradation Analysis</h3>
          <p>The ultrasonic sensor array recorded readings across four primary structural nodes. Shell Plate C-102 exhibits accelerated localized wall thinning:</p>
          <table className="prose-table">
            <thead><tr><th>Vessel Location</th><th>Nominal</th><th>Measured (UTT)</th><th>ASME B31.3 Min</th><th>Status</th></tr></thead>
            <tbody>
              <tr><td>Elbow E-101</td><td>8.00 mm</td><td>7.82 mm</td><td>6.40 mm</td><td>Nominal (+1.42 mm)</td></tr>
              <tr style={{ color: 'var(--danger-red)' }}><td>Shell Plate C-102</td><td>8.00 mm</td><td>6.55 mm</td><td>6.40 mm</td><td>Critical (+0.15 mm)</td></tr>
              <tr><td>Nozzle N-04</td><td>7.50 mm</td><td>7.20 mm</td><td>6.00 mm</td><td>Nominal (+1.20 mm)</td></tr>
              <tr><td>Bottom Head B-1</td><td>8.20 mm</td><td>8.10 mm</td><td>6.50 mm</td><td>Nominal (+1.60 mm)</td></tr>
            </tbody>
          </table>
          <h3 className="prose-heading">2. Risk Assessment &amp; Engineering Recommendation</h3>
          <p>Shell Plate C-102 retains a corrosion margin of only <strong>0.15 mm</strong>. Based on an annualized wall loss rate of 0.36 mm/year, the vessel will breach the mandatory retirement threshold within approximately 5 months of continuous service.</p>
          <p>I recommend continuous operation for up to 90 days conditioned upon bi-weekly ultrasonic logging at Node C-102. Full weld overlay restoration should be prioritized during the upcoming scheduled refinery turnaround.</p>
        </>,
        { name: 'Approval_Note_CDU102_NDT.docx', size: '24 KB', type: 'docx' }
      ),
    ],
  },
  'valve-dp': {
    id: 'valve-dp',
    title: 'Valve Delta-P Verification',
    timestamp: Date.now() - 3600000,
    messages: [
      makeUserMsg('Verify the Darcy-Weisbach pressure drop across the 6-inch crude feed isolation valve (XV-104A) at 450 m³/h throughput. Confirm if Delta-P is within the 4.50 bar threshold.'),
      makeAssistantMsg(
        [
          { id: 'plan', label: 'Plan', model: 'Model Router (Heuristics)', reason: 'Routed to local coding sandbox for isolated mathematical verification.' },
          { id: 'act', label: 'Act', model: 'Qwen 2.5 Coder 1.5B', reason: 'Synthesized Darcy-Weisbach fluid velocity and pressure loss script.' },
          { id: 'observe', label: 'Observe', model: 'Local Python Sandbox', reason: 'Executed script in restricted subprocess. Exit Code 0, Delta-P computed at 4.28 bar.' },
          { id: 'deliverable', label: 'Deliverable', model: 'Sovereign Runtime', reason: 'Compiled verified execution output and safety margin calculation.' },
        ],
        <>
          <p>I have written and executed the fluid dynamics calculation within the local Python sandbox to evaluate pressure drop across isolation valve XV-104A.</p>
          <div className="prose-code-block">{`# Sandboxed Python Execution — Darcy-Weisbach Verification\nFlow Rate: 450.00 m³/h | Nominal Bore: 6.00 in (0.1524 m)\nFluid Velocity: 6.87 m/s | Reynolds Number: 1.42e5 (Turbulent)\nCalculated Delta-P: 4.28 bar (Threshold Limit: 4.50 bar)\nVerification Result: PASS (Margin: +0.22 bar)`}</div>
          <p>The computed pressure loss of <strong>4.28 bar</strong> complies with the system operating specification, leaving a 4.9% safety margin under maximum throughput conditions.</p>
        </>,
        { name: 'valve_dp_verification.py', size: '2.8 KB', type: 'py' }
      ),
    ],
  },
  'pid-flare': {
    id: 'pid-flare',
    title: 'P&ID Flare Line Review',
    timestamp: Date.now() - 86400000,
    messages: [
      makeUserMsg(
        'Inspect the P&ID drawing for the flare knock-out drum bypass. Confirm whether emergency isolation valves are configured with lock-closed indicators.',
        [{ name: 'pid_sample_diagram.png', size: 532480 }]
      ),
      makeAssistantMsg(
        [
          { id: 'plan', label: 'Plan', model: 'Model Router', reason: 'Image input routed to local Moondream 1.6B vision model.' },
          { id: 'act', label: 'Act', model: 'Moondream 1.6B Vision', reason: 'Extracted valve symbols and tag annotations from schematic.' },
          { id: 'observe', label: 'Observe', model: 'Qwen 2.5 3B', reason: 'Cross-checked tag BV-108 against refinery lockout SOP-304.' },
          { id: 'deliverable', label: 'Deliverable', model: 'Sovereign Knowledge Engine', reason: 'Generated compliance assessment matrix.' },
        ],
        <>
          <p>I have analyzed the Piping &amp; Instrumentation Diagram (P&amp;ID) for the flare header relief loop using the on-premise Moondream vision model.</p>
          <p>The inspection confirms that manual bypass valve <strong>BV-108</strong> is correctly designated as <strong>LC (Locked Closed)</strong> with mechanical car-seal protection in accordance with refinery safety protocol SOP-VR-304.</p>
        </>,
        { name: 'pid_compliance_audit.xlsx', size: '14 KB', type: 'xlsx' }
      ),
    ],
  },
};

// ─── File Chip Component ──────────────────────────────────────────────────────
function FileChip({ file, onRemove, showThumb = false }) {
  const [thumbUrl, setThumbUrl] = useState(null);
  const ext = (file.name || '').split('.').pop().toLowerCase();
  const isImage = IMAGE_EXTS.has(ext);

  useEffect(() => {
    if (showThumb && isImage && file instanceof File) {
      const url = URL.createObjectURL(file);
      setThumbUrl(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [file, showThumb, isImage]);

  // Workspace path chip — distinct styling
  if (file.isWorkspace) {
    return (
      <div className="file-chip workspace-chip">
        <span className="file-chip-icon ws">
          <FolderOpen size={12} />
        </span>
        <div className="file-chip-info">
          <span className="file-chip-name" title={file.name}>
            {file.name.length > 28 ? '…' + file.name.slice(-26) : file.name}
          </span>
          <span className="file-chip-size">Local Workspace</span>
        </div>
        {onRemove && (
          <button className="file-chip-remove" onClick={e => { e.stopPropagation(); onRemove(); }} title="Remove">
            <X size={10} />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="file-chip">
      {showThumb && thumbUrl
        ? <img src={thumbUrl} alt={file.name} className="file-chip-img" />
        : <span className="file-chip-icon">{fileIcon(file.name)}</span>
      }
      <div className="file-chip-info">
        <span className="file-chip-name" title={file.name}>
          {file.name.length > 22 ? file.name.slice(0, 19) + '…' + file.name.slice(-4) : file.name}
        </span>
        <span className="file-chip-size">{typeof file.size === 'number' ? fmtSize(file.size) : file.size}</span>
      </div>
      {onRemove && (
        <button className="file-chip-remove" onClick={e => { e.stopPropagation(); onRemove(); }} title="Remove file">
          <X size={10} />
        </button>
      )}
    </div>
  );
}

// ─── Attach Popover (Claude-style) ──────────────────────────────────────────
function AttachPopover({ onFiles, onWorkspacePath, onClose }) {
  const [showWorkspace, setShowWorkspace] = useState(false);
  const [wsPath, setWsPath] = useState('');
  const fileRef = useRef(null);
  const imgRef = useRef(null);
  const folderRef = useRef(null);
  const wsInputRef = useRef(null);

  const handleFileChange = (e, ref) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) { onFiles(files); onClose(); }
    e.target.value = '';
  };

  const handleFolderPick = (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      const rel = files[0].webkitRelativePath || files[0].name;
      const folder = rel.split('/')[0] || rel;
      setWsPath(folder);
      if (wsInputRef.current) wsInputRef.current.value = folder;
    }
    e.target.value = '';
  };

  const confirmWorkspace = () => {
    const path = wsPath.trim();
    if (path) { onWorkspacePath(path); onClose(); }
  };

  return (
    <div className="attach-popover">
      {/* Hidden inputs */}
      <input ref={fileRef} type="file" multiple
        accept=".csv,.pdf,.json,.docx,.xlsx,.txt,.parquet,.mp3,.wav,.ogg,.md"
        style={{ display: 'none' }}
        onChange={e => handleFileChange(e, fileRef)} />
      <input ref={imgRef} type="file" multiple
        accept="image/*"
        style={{ display: 'none' }}
        onChange={e => handleFileChange(e, imgRef)} />
      <input ref={folderRef} type="file"
        // @ts-ignore
        webkitdirectory="" directory=""
        style={{ display: 'none' }}
        onChange={handleFolderPick} />

      {/* Option 1 — Upload Files */}
      <button
        className="attach-popover-item"
        onClick={() => { fileRef.current?.click(); }}
        type="button"
      >
        <span className="attach-popover-item-icon doc">
          <FileText size={15} />
        </span>
        <span className="attach-popover-item-body">
          <span className="attach-popover-item-label">Upload Files</span>
          <span className="attach-popover-item-desc">CSV, PDF, DOCX, TXT, JSON, Parquet…</span>
        </span>
      </button>

      <div className="attach-popover-divider" />

      {/* Option 2 — Upload Images */}
      <button
        className="attach-popover-item"
        onClick={() => { imgRef.current?.click(); }}
        type="button"
      >
        <span className="attach-popover-item-icon img">
          <Image size={15} />
        </span>
        <span className="attach-popover-item-body">
          <span className="attach-popover-item-label">Upload Images</span>
          <span className="attach-popover-item-desc">PNG, JPG, WEBP, GIF, SVG, TIFF…</span>
        </span>
      </button>

      <div className="attach-popover-divider" />

      {/* Option 3 — Local Workspace */}
      <button
        className={`attach-popover-item ${showWorkspace ? 'active' : ''}`}
        onClick={() => { setShowWorkspace(v => !v); }}
        type="button"
      >
        <span className="attach-popover-item-icon ws">
          <FolderOpen size={15} />
        </span>
        <span className="attach-popover-item-body">
          <span className="attach-popover-item-label">Local Workspace</span>
          <span className="attach-popover-item-desc">Enter or browse a folder path</span>
        </span>
        <ChevronRight
          size={12}
          className="attach-popover-item-chevron"
          style={{ transform: showWorkspace ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s' }}
        />
      </button>

      {showWorkspace && (
        <div className="attach-popover-workspace">
          <div className="attach-ws-input-row">
            <FolderOpen size={12} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            <input
              ref={wsInputRef}
              className="attach-ws-input"
              type="text"
              placeholder="C:\Users\... or /mnt/datasets/"
              value={wsPath}
              onChange={e => setWsPath(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); confirmWorkspace(); } }}
              autoFocus
            />
            <button
              className="attach-ws-browse-btn"
              type="button"
              onClick={() => folderRef.current?.click()}
              title="Browse folder"
            >
              <FolderOpen size={12} />
            </button>
            <button
              className="attach-ws-confirm-btn"
              type="button"
              onClick={confirmWorkspace}
              title="Confirm path"
              disabled={!wsPath.trim()}
            >
              <CornerDownLeft size={12} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── CRM Panel (placeholder) ──────────────────────────────────────────────────
function CrmPanel() {
  return (
    <div className="crm-panel">
      <div className="crm-panel-icon"><Link size={22} /></div>
      <div className="crm-panel-title">Connect HubSpot / CRM</div>
      <p className="crm-panel-desc">
        Authenticate your CRM account to enable automatic real-time deal property sync into the knowledge vector store.
      </p>
      <button className="crm-connect-btn">
        <Link size={13} /> Connect CRM Account
      </button>
      <div className="crm-panel-note">Supports HubSpot, Salesforce, Pipedrive &amp; custom REST endpoints.</div>
    </div>
  );
}

// ─── Home Page ────────────────────────────────────────────────────────────────
function HomePage({ onEnterApp }) {
  return (
    <div className="homepage">
      <div className="hp-grid-bg" aria-hidden="true" />

      <nav className="hp-nav">
        <div className="hp-nav-logo">
          <span className="hp-nav-logo-dot" />
          vajra
        </div>
        <div className="hp-nav-links">
          {['Why Sovereign', 'What We Do', 'Latest News', 'Free CRM Audit', 'Get In Touch'].map(link => (
            <button key={link} className="hp-nav-link">{link}</button>
          ))}
        </div>
        <button className="hp-nav-cta">Schedule a Call Now</button>
      </nav>

      <section className="hp-hero">
        <button className="hp-play-btn" onClick={onEnterApp} title="Enter Vajra Workbench" aria-label="Enter the Vajra AI Workbench">
          <Play size={20} fill="currentColor" />
        </button>
        <h1 className="hp-headline">
          <span className="hp-headline-row">Nothing gets <span className="hp-headline-italic">through</span></span>
          <span className="hp-headline-row">Nothing gets<span className="hp-headline-badge">Lost</span></span>
        </h1>
        <p className="hp-subtext">Strength you can <strong>trust</strong> — Security you can see</p>
      </section>

      <div className="hp-mockup-wrap">
        <div className="hp-browser-frame">
          <div className="hp-browser-chrome">
            <div className="hp-browser-dots">
              <div className="hp-browser-dot red" /><div className="hp-browser-dot yellow" /><div className="hp-browser-dot green" />
            </div>
            <div className="hp-browser-addr">https://app.sovereign.io/deals</div>
            <div style={{ display: 'flex', gap: 8, marginLeft: 'auto' }}>
              <LayoutGrid size={13} style={{ color: 'var(--text-muted)' }} />
              <ArrowRight size={13} style={{ color: 'var(--text-muted)' }} />
              <Plus size={13} style={{ color: 'var(--text-muted)' }} />
            </div>
          </div>
          <div className="hp-browser-body">
            <div className="ask-vajra-header">
              <div className="ask-vajra-brand">
                <div className="ask-vajra-avatar">V</div>
                <div>
                  <span className="ask-vajra-title">Ask Vajra</span>
                  <span className="ask-vajra-version">v2.4-stream</span>
                </div>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8 }}>
                  Inquire directly across synced CRM deals, ingest batches &amp; vector logs
                </span>
              </div>
              <div className="ask-vajra-status">
                <span className="ask-vajra-status-dot" />Knowledge Store Live
              </div>
            </div>
            <div className="ask-vajra-input-row">
              <span className="ask-vajra-input-placeholder">Ask Vajra anything about deals, pipelines, or security audit logs…</span>
              <button className="ask-vajra-query-btn">Query <Play size={10} fill="currentColor" /></button>
            </div>
            <div className="ask-vajra-suggestions">
              <span className="ask-vajra-suggestion-label">Suggested:</span>
              {['Summarise Q3 Deal Pipeline', 'Analyse ingest latency', 'Check compliance audit logs'].map(s => (
                <span key={s} className="ask-vajra-chip">{s}</span>
              ))}
            </div>
            <div className="mock-stream-bar">
              <div className="mock-stream-icon"><Zap size={12} color="var(--accent-blue)" /></div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="mock-stream-title">Vajra Synthesis Stream</div>
                <div className="mock-stream-text">
                  Q3 migration deals represent <strong>$246,500</strong> in weighted pipeline. Acme Global Enterprise has completed SOC-2 review with health score updated to 94%. Starlight Vector search evaluation is scheduled for close on Dec 05.
                </div>
                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                  {['deal_acme_q3.json', 'vector_pipeline_eval.parquet'].map(f => (
                    <span key={f} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, background: 'var(--bg-canvas)', border: '1px solid var(--border-hairline)', borderRadius: 4, padding: '2px 8px', fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      <FileText size={9} />{f}
                    </span>
                  ))}
                </div>
              </div>
              <div className="mock-stream-latency">Latency: 388ms<br /><span style={{ color: 'var(--accent-blue)' }}>3 sources cited</span></div>
            </div>
          </div>
        </div>
      </div>
      <div style={{ height: 80, background: 'linear-gradient(to bottom, transparent, var(--bg-canvas))', position: 'relative', zIndex: 10 }} />
    </div>
  );
}

// ─── Pipeline Page ────────────────────────────────────────────────────────────
function PipelinePage({
  onNavigateToChat,
  databaseDocs,
  onAddDoc,
  onDatabaseChanged,
  dbInputRef,
  conversations,
  onSelectConversation,
  onNewSession,
}) {
  const [activeSource, setActiveSource] = useState('upload');
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [workspacePath, setWorkspacePath] = useState('');
  const [domain, setDomain] = useState('Research & Financial Briefs');
  const [isDragging, setIsDragging] = useState(false);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [activePopoverNode, setActivePopoverNode] = useState(null);

  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const dbFileInputRef = dbInputRef;

  const sourceDefs = [
    { id: 'upload', icon: <Upload size={16} />, title: 'Upload Local File', desc: 'Direct upload CSV, PDF, JSON, or research transcripts', tag: 'Direct chunking', badge: 'ACTIVE' },
    { id: 'workspace', icon: <Folder size={16} />, title: 'Local Workspace', desc: 'Enter or browse a local folder path', tag: 'Fastest transfer' },
    { id: 'crm', icon: <Link size={16} />, title: 'Connect HubSpot / CRM', desc: 'Automatic real-time sync with deal properties', tag: 'Continuous sync' },
    { id: 'media', icon: <Image size={16} />, title: 'Media & Diagrams', desc: 'Images + dataset files for multi-modal embeddings', tag: 'Vision-v3' },
  ];

  const currentConfig = SOURCE_FILE_CONFIGS[activeSource] || null;

  // ── Supported text for section label
  const supportedText = {
    upload: 'Supported: CSV, PDF, DOCX, JSON, TXT, Parquet, MP3, WAV',
    workspace: 'Enter the full local folder path below',
    crm: 'HubSpot, Salesforce, Pipedrive & custom REST',
    media: 'Supported: PNG, JPG, WEBP, GIF, TIFF, SVG, PDF, CSV, Parquet, JSON',
  }[activeSource];

  const addFiles = useCallback((fileList) => {
    const arr = Array.from(fileList);
    setUploadedFiles(prev => {
      const names = new Set(prev.map(f => f.name));
      return [...prev, ...arr.filter(f => !names.has(f.name))];
    });
  }, []);

  const removeFile = (idx) => setUploadedFiles(prev => prev.filter((_, i) => i !== idx));

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    addFiles(e.dataTransfer.files);
  };

  const handleFolderBrowse = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      // Extract folder path from first file's webkitRelativePath
      const rel = files[0].webkitRelativePath || files[0].name;
      const parts = rel.split('/');
      const folderName = parts.length > 1 ? parts[0] : rel;
      setWorkspacePath(folderName);
    }
  };

  const handleStartIngest = async () => {
    if (uploadedFiles.length === 0 && !workspacePath) return;
    setIngestLoading(true);
    try {
      // 1. Upload files → get server paths
      let serverPaths = [];
      let documentIds = [];
      if (uploadedFiles.length > 0) {
        const uploadResult = await api.uploadFiles(uploadedFiles);
        serverPaths = uploadResult.paths || [];
        documentIds = (uploadResult.documents || []).map(doc => doc.document_id);
      }

      // 2. Index into ChromaDB
      await api.ingestDocuments({
        filePaths: serverPaths,
        documentIds,
        workspacePath: workspacePath || null,
        domain,
      });
      await onDatabaseChanged?.();
    } catch (err) {
      console.error('Pipeline ingest error:', err.message);
      // Still register files in UI even if backend failed
      uploadedFiles.forEach(f => onAddDoc(f));
    } finally {
      setIngestLoading(false);
    }
  };


  const handleGoToChat = () => {
    onNavigateToChat(uploadedFiles);
  };

  const showDropZone = activeSource === 'upload' || activeSource === 'media';

  return (
    <div className="pipeline-shell">
      {/* Top Bar */}
      <header className="pipeline-topbar">
        <div className="pipeline-topbar-left">
          <span className="pipeline-topbar-brand">sovereign</span>
          <span className="pipeline-topbar-sep">/</span>
          <span className="pipeline-topbar-crumb">Knowledge &amp; Vector Pipeline</span>
        </div>
        <div className="pipeline-topbar-right">
          <div className="pipeline-status-chip"><span className="pipeline-status-dot" />index.vpath://live-q3</div>
          <div className="pipeline-status-chip"><Activity size={11} />Latency: 288ms</div>
          <div className="pipeline-status-chip"><ShieldCheck size={11} />soc2-vault-us-east-1</div>
          <div className="pipeline-avatar" title="Go to Chat" onClick={handleGoToChat} style={{ cursor: 'pointer' }}>Vi</div>
        </div>
      </header>

      {/* Two-column layout */}
      <div className="pipeline-layout">
        {/* ── LEFT: Main content ── */}
        <main className="pipeline-content">
          <div className="pipeline-title-row">
            <h1 className="pipeline-title">Knowledge Ingestion &amp; Vector Pipeline</h1>
            <button className="model-params-btn"><Settings size={13} />Model Parameters</button>
          </div>

          {/* Section 1 */}
          <div className="section-label-row">
            <span className="section-label">1. Select Ingestion Source</span>
            <span className="section-supported">{supportedText}</span>
          </div>

          <div className="source-cards-grid">
            {sourceDefs.map(src => (
              <div
                key={src.id}
                className={`source-card ${activeSource === src.id ? 'active' : ''}`}
                onClick={() => { setActiveSource(src.id); setUploadedFiles([]); }}
              >
                {src.badge && <span className="source-card-badge">{src.badge}</span>}
                <div className="source-card-icon">{src.icon}</div>
                <div className="source-card-title">{src.title}</div>
                <div className="source-card-desc">{src.desc}</div>
                <span className="source-card-tag">{src.tag}</span>
              </div>
            ))}
          </div>

          {/* Section 2 */}
          <div className="section-2">
            <div className="section-label" style={{ marginBottom: 4 }}>2. Target Data &amp; Pipeline Configuration</div>
            <p className="section-2-desc">
              {activeSource === 'workspace'
                ? 'Enter or browse a local folder path. Only one workspace path is supported at a time.'
                : activeSource === 'crm'
                ? 'Connect your CRM to enable continuous automatic sync.'
                : 'Select or drop files to begin embedding processing.'}
            </p>

            {/* ── Upload / Media: drop zone ── */}
            {showDropZone && currentConfig && (
              <>
                <input
                  key={activeSource}
                  type="file"
                  multiple={currentConfig.multiple}
                  accept={currentConfig.accept}
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  onChange={e => { addFiles(e.target.files); e.target.value = ''; }}
                />

                {uploadedFiles.length === 0 ? (
                  <div
                    className={`drop-zone ${isDragging ? 'dragging' : ''}`}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <div className="drop-zone-icon"><Cloud size={32} strokeWidth={1.2} /></div>
                    <div className="drop-zone-title">{currentConfig.dropTitle}</div>
                    <div className="drop-zone-sub">{currentConfig.dropSub}</div>
                    <button type="button" className="browse-btn" onClick={e => { e.stopPropagation(); fileInputRef.current?.click(); }}>
                      Browse Local Explorer
                    </button>
                  </div>
                ) : (
                  <div className="drop-zone-filled">
                    <div className="drop-zone-filled-header">
                      <span className="drop-zone-filled-count">{uploadedFiles.length} file{uploadedFiles.length > 1 ? 's' : ''} selected</span>
                      <button
                        className="dz-add-more-btn"
                        onClick={() => fileInputRef.current?.click()}
                      >
                        <Plus size={12} /> Add more
                      </button>
                    </div>
                    <div className="file-chips-grid">
                      {uploadedFiles.map((f, idx) => (
                        <FileChip
                          key={f.name + idx}
                          file={f}
                          onRemove={() => removeFile(idx)}
                          showThumb={true}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* ── Local Workspace: single path input ── */}
            {activeSource === 'workspace' && (
              <div className="workspace-section">
                <input
                  type="file"
                  ref={folderInputRef}
                  style={{ display: 'none' }}
                  // @ts-ignore
                  webkitdirectory=""
                  directory=""
                  onChange={handleFolderBrowse}
                />
                <div className="workspace-path-row">
                  <div className="workspace-path-input-wrap">
                    <FolderOpen size={13} />
                    <input
                      className="workspace-path-input"
                      type="text"
                      placeholder="C:\Users\HP\datasets\  or  /mnt/datasets/"
                      value={workspacePath}
                      onChange={e => setWorkspacePath(e.target.value)}
                    />
                  </div>
                  <button
                    className="browse-folder-btn"
                    onClick={() => folderInputRef.current?.click()}
                    title="Browse for a folder"
                  >
                    <FolderOpen size={13} /> Browse Folder
                  </button>
                </div>
                {workspacePath && (
                  <div className="path-verified">
                    <Check size={12} /> Path set: <code style={{ fontFamily: 'var(--font-mono)', fontSize: 11, marginLeft: 4 }}>{workspacePath}</code>
                  </div>
                )}
              </div>
            )}

            {/* ── CRM: connect panel ── */}
            {activeSource === 'crm' && <CrmPanel />}

            {/* Storage path row (show for upload/media) */}
            {showDropZone && (
              <>
                <div className="storage-path-label">Storage / Virtual Cluster Path:</div>
                <div className="storage-path-row">
                  <div className="storage-path-input-wrap">
                    <Folder size={13} />
                    <input
                      className="storage-path-input"
                      type="text"
                      defaultValue="/mnt/storage/research/q3-briefs/financial_transcripts"
                      placeholder="/mnt/storage/research/..."
                    />
                  </div>
                  <button className="start-ingest-btn" onClick={handleStartIngest} disabled={ingestLoading}>
                    {ingestLoading
                      ? <><Loader2 size={14} className="animate-spin" /> Ingesting…</>
                      : <>Start Ingest <ArrowRight size={14} /></>}
                  </button>
                </div>

                <div className="domain-label">Assigned Domain</div>
                <select className="domain-select" value={domain} onChange={e => setDomain(e.target.value)}>
                  {['Research & Financial Briefs', 'Engineering Standards', 'Legal & Compliance', 'Operations & Maintenance', 'Safety & SOPs', 'Custom Domain…'].map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </>
            )}
          </div>

          {/* Add to Database */}
          <div className="add-to-db-section">
            <div className="add-to-db-header">
              <div className="add-to-db-title">Add to Database</div>
              <input type="file" ref={dbFileInputRef} style={{ display: 'none' }} onChange={e => { const f = e.target.files?.[0]; if (f) onAddDoc(f); }} />
              <button className="db-circular-add-btn" onClick={() => dbFileInputRef.current?.click()} title="Upload organisation document to ChromaDB">
                <Plus size={15} />
              </button>
            </div>
            <p className="add-to-db-desc">Ingest organisation standards, manuals, and SOPs into the local ChromaDB vector store for sovereign grounding.</p>
            <div className="db-documents-grid">
              {databaseDocs.map((doc, idx) => (
                <div key={idx} className="db-doc-card" title={doc.name}>
                  <Database size={14} className="db-doc-icon" />
                  <div>
                    <div className="db-doc-name">{doc.name}</div>
                    <div className="db-doc-meta">{doc.size} · {doc.date}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </main>

        {/* ── RIGHT: Sessions Panel ── */}
        <aside className="sessions-panel">
          <div className="sessions-panel-header">
            <div className="sessions-panel-title">
              <MessageSquare size={13} />
              Recent Sessions
            </div>
            <button className="sessions-new-btn" onClick={onNewSession} title="New session">
              <Plus size={13} />
            </button>
          </div>

          <div className="sessions-list">
            {Object.values(conversations)
              .sort((a, b) => b.timestamp - a.timestamp)
              .map(conv => (
                <div
                  key={conv.id}
                  className="session-item"
                  onClick={() => onSelectConversation(conv.id)}
                  title={conv.title}
                >
                  <div className="session-item-icon">
                    <FileText size={12} />
                  </div>
                  <div className="session-item-body">
                    <div className="session-item-title">
                      {conv.title.length > 28 ? conv.title.slice(0, 25) + '…' : conv.title}
                    </div>
                    <div className="session-item-meta">
                      <Clock size={9} />
                      {relTime(conv.timestamp)}
                    </div>
                  </div>
                  <ChevronRight size={12} className="session-item-arrow" />
                </div>
              ))}
          </div>

          <div className="sessions-panel-footer">
            <span className="sessions-airgap-dot" />
            All inference local · 0 calls
          </div>
        </aside>
      </div>

      {/* Bottom Status Bar */}
      <div className="pipeline-status-bar">
        <div className="status-bar-left">
          <span className="status-bar-item">Sovereign OS</span>
          <span style={{ color: 'var(--border-subtle)' }}>•</span>
          <span className="status-bar-item">Data Vector Isolation Layer</span>
          <span style={{ color: 'var(--border-subtle)' }}>•</span>
          <span className="status-bar-item">Status: <span className="status-ok">All Ensembles Operational</span></span>
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          <span>API: v2.4 stream</span>
          <span>Build: 884629</span>
        </div>
      </div>

      {/* Synthesis Stream Footer */}
      <div className="synthesis-stream-bar">
        <div className="stream-bar-left">
          <span className="stream-bar-dot" />
          <div style={{ minWidth: 0 }}>
            <div className="stream-bar-label">Vajra Synthesis Stream</div>
            <div className="stream-bar-text">
              "Acme Global Enterprise deal migration ($246,500) completed SOC-2 review with 94% health score. Vectors ready for query evaluation."
            </div>
          </div>
        </div>
        <button className="test-query-btn" onClick={handleGoToChat}>
          Test Query in Ask Vajra <ArrowRight size={12} />
        </button>
      </div>
    </div>
  );
}

// ─── Agent Process Nodes ──────────────────────────────────────────────────────
function AgentTrace({ nodes, activeStage, popoverNode, setPopoverNode }) {
  if (!nodes || nodes.length === 0) return null;
  return (
    <div className="process-indicator-row">
      {nodes.map((node, index) => {
        const isCompleted = activeStage > index + 1;
        const isActive = activeStage === index + 1 || index < activeStage;
        const isPopoverOpen = popoverNode === node.id;
        return (
          <React.Fragment key={node.id}>
            <div
              className={`process-node ${isCompleted || isActive ? 'completed' : ''} ${isActive && !isCompleted ? 'active' : ''}`}
              onClick={() => setPopoverNode(isPopoverOpen ? null : node.id)}
              title="Click to view model rationale"
            >
              <div className="node-dot" />
              <span className="node-label">{node.label}</span>
              {isPopoverOpen && (
                <div className="node-popover" onClick={e => e.stopPropagation()}>
                  <div className="popover-stage-title">STAGE: {node.label}</div>
                  <div className="popover-model-name">{node.model}</div>
                  <p className="popover-explanation">{node.reason}</p>
                </div>
              )}
            </div>
            {index < nodes.length - 1 && (
              <div className="process-connector-arrow"><ChevronRight size={12} /></div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [currentView, setCurrentView] = useState('homepage'); // 'homepage' | 'pipeline' | 'active'
  const [conversations, setConversations] = useState(PRESET_CONVERSATIONS);
  const [activeChatId, setActiveChatId] = useState(null);

  // Multi-turn input state
  const [promptText, setPromptText] = useState('');
  const [attachedFiles, setAttachedFiles] = useState([]); // files carried from pipeline or attached in chat
  const [useKB, setUseKB] = useState(false); // Knowledge Base toggle: search indexed company data
  const [useDocumentContext, setUseDocumentContext] = useState(true);

  const [activePopoverNode, setActivePopoverNode] = useState(null);
  const [databaseDocs, setDatabaseDocs] = useState(INITIAL_DATABASE_DOCS);

  const loadDatabaseDocuments = useCallback(async () => {
    try {
      const result = await api.listDocuments();
      // Show ALL documents (indexed or not) — backend now returns everything.
      // Files appear immediately after upload; "Indexing" badge shown for pending ones.
      setDatabaseDocs((result.documents || []).map(doc => ({
        ...doc,
        size: doc.size_human || fmtSize(doc.size || 0),
        date: doc.indexed
          ? (doc.domain ? `Indexed · ${doc.domain}` : 'Indexed')
          : 'Indexing…',
        type: doc.name.split('.').pop(),
      })));
    } catch (err) {
      console.error('Could not load local database documents:', err.message);
    }
  }, []);

  // Permission / processing state
  const [pendingPermission, setPendingPermission] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Attach popover
  const [attachPopoverOpen, setAttachPopoverOpen] = useState(false);
  const attachPopoverRef = useRef(null);
  const attachBtnRef = useRef(null);

  const dbInputRef = useRef(null);
  const chatThreadRef = useRef(null);
  const filePickerRef = useRef(null);
  const streamAbortRef = useRef(null); // holds the SSE abort function

  useEffect(() => { loadDatabaseDocuments(); }, [loadDatabaseDocuments]);

  // Auto-scroll chat thread on new messages
  useEffect(() => {
    if (chatThreadRef.current) {
      chatThreadRef.current.scrollTop = chatThreadRef.current.scrollHeight;
    }
  }, [conversations, activeChatId]);

  // Close attach popover on outside click or Escape
  useEffect(() => {
    if (!attachPopoverOpen) return;
    const handleClick = (e) => {
      if (
        attachPopoverRef.current && !attachPopoverRef.current.contains(e.target) &&
        attachBtnRef.current && !attachBtnRef.current.contains(e.target)
      ) {
        setAttachPopoverOpen(false);
      }
    };
    const handleKey = (e) => { if (e.key === 'Escape') setAttachPopoverOpen(false); };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [attachPopoverOpen]);

  // Helper: add files from attach popover
  const handleAttachFiles = useCallback((files) => {
    setAttachedFiles(prev => {
      const names = new Set(prev.map(f => f.name));
      return [...prev, ...files.filter(f => !names.has(f.name))];
    });
  }, []);

  // Helper: add workspace path chip from attach popover
  const handleAttachWorkspace = useCallback((path) => {
    setAttachedFiles(prev => {
      const already = prev.find(f => f.isWorkspace);
      if (already) {
        return prev.map(f => f.isWorkspace ? { name: path, size: 'Workspace', isWorkspace: true } : f);
      }
      return [...prev, { name: path, size: 'Workspace', isWorkspace: true }];
    });
  }, []);

  // Add a document to ChromaDB list + upload + ingest
  const handleAddDoc = async (file) => {
    // Optimistically add to UI
    setDatabaseDocs(prev => [{
      name: file.name,
      size: fmtSize(file.size),
      date: 'Indexing…',
      type: file.name.split('.').pop(),
    }, ...prev]);
    try {
      const uploadResult = await api.uploadFiles([file]);
      const documentIds = (uploadResult.documents || []).map(doc => doc.document_id);
      if (documentIds.length > 0) {
        const ingestResult = await api.ingestDocuments({ documentIds, domain: 'Organisation Documents' });
        if (ingestResult.errors?.length) throw new Error(ingestResult.errors[0].error);
        await loadDatabaseDocuments();
        // Update date label
        setDatabaseDocs(prev => prev.map(d =>
          d.name === file.name && d.date === 'Indexing…'
            ? { ...d, date: 'Indexed just now' }
            : d
        ));
      }
    } catch (err) {
      console.error('Ingest failed:', err.message);
      setDatabaseDocs(prev => prev.map(d =>
        d.name === file.name && d.date === 'Indexing…'
          ? { ...d, date: 'Ingest failed' }
          : d
      ));
    }
  };


  // Poll permissions while processing
  useEffect(() => {
    if (!isProcessing) { setPendingPermission(null); return; }
    const interval = setInterval(async () => {
      try {
        const res = await api.getPendingPermissions();
        if (res.pending && Object.keys(res.pending).length > 0) {
          const taskId = Object.keys(res.pending)[0];
          setPendingPermission({ id: taskId, ...res.pending[taskId] });
        } else {
          setPendingPermission(null);
        }
      } catch (e) { console.error('Permission poll failed', e); }
    }, 1500);
    return () => clearInterval(interval);
  }, [isProcessing]);

  const handleResolvePermission = async (approved) => {
    if (!pendingPermission) return;
    try {
      await api.resolvePermission(pendingPermission.id, approved);
      setPendingPermission(null);
    } catch (e) { alert('Failed to resolve permission: ' + e.message); }
  };

  const handleSelectConversation = (chatId) => {
    setActiveChatId(chatId);
    setCurrentView('active');
    setActivePopoverNode(null);
    setPromptText('');
  };

  // Navigate to a new blank chat (with optionally pre-loaded files from pipeline)
  const handleNavigateToChat = (files = []) => {
    setAttachedFiles(files);
    setActiveChatId(null);
    setCurrentView('active');
    setPromptText('');
  };

  const handleNewSession = () => {
    setAttachedFiles([]);
    setActiveChatId(null);
    setPromptText('');
    setCurrentView('active');
  };

  // ── Submit: real upload + SSE streaming ──────────────────────────────────
  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!promptText.trim() && attachedFiles.length === 0) return;
    if (isProcessing) return;

    // Abort any in-flight stream before starting a new one
    if (streamAbortRef.current) { streamAbortRef.current(); streamAbortRef.current = null; }

    const snapshotFiles = [...attachedFiles];
    const userMsg = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: promptText,
      files: snapshotFiles,
      timestamp: Date.now(),
    };

    let chatId = activeChatId;

    // If no active conversation → create one
    if (!chatId) {
      chatId = `chat-${Date.now()}`;
      const newConv = {
        id: chatId,
        title: promptText.slice(0, 35) || (snapshotFiles[0]?.name ?? 'New Session'),
        timestamp: Date.now(),
        messages: [],
        documentIds: [],
      };
      setConversations(prev => ({ ...prev, [chatId]: newConv }));
      setActiveChatId(chatId);
    }

    // Build history from existing messages in this conversation (before new user msg)
    const existingMsgs = conversations[chatId]?.messages || [];
    const conversationDocumentIds = conversations[chatId]?.documentIds || [];
    const history = existingMsgs
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({
        role: m.role,
        content: m.role === 'user' ? m.content : (m._rawText || ''),
      }))
      .filter(m => m.content);

    // Append user message to UI
    setConversations(prev => ({
      ...prev,
      [chatId]: {
        ...prev[chatId],
        messages: [...(prev[chatId]?.messages || []), userMsg],
      },
    }));

    setPromptText('');
    setAttachedFiles([]);
    setIsProcessing(true);

    // Step 1: Upload actual File objects → get server paths
    let serverPaths = [];
    let newlyUploadedDocumentIds = [];
    const realFiles = snapshotFiles.filter(f => f instanceof File);
    const workspaceChip = snapshotFiles.find(f => f.isWorkspace);
    try {
      if (realFiles.length > 0) {
        const uploadResult = await api.uploadFiles(realFiles);
        serverPaths = uploadResult.paths || [];
        newlyUploadedDocumentIds = (uploadResult.documents || []).map(doc => doc.document_id);
      }
      if (workspaceChip) {
        serverPaths.push(workspaceChip.name); // pass path string as-is
      }
    } catch (uploadErr) {
      console.warn('Upload failed — continuing without file paths:', uploadErr.message);
    }

    // Persist sources on the conversation, not on the transient composer.
    // Follow-up questions will keep this scope after attachedFiles is cleared.
    const activeDocumentIds = [...new Set([...conversationDocumentIds, ...newlyUploadedDocumentIds])];
    if (newlyUploadedDocumentIds.length > 0) {
      setConversations(prev => ({
        ...prev,
        [chatId]: { ...prev[chatId], documentIds: activeDocumentIds },
      }));
    }

    // Step 2: Insert streaming assistant placeholder
    const pendingMsgId = `msg-${Date.now()}-stream`;
    setConversations(prev => ({
      ...prev,
      [chatId]: {
        ...prev[chatId],
        messages: [
          ...(prev[chatId]?.messages || []),
          {
            id: pendingMsgId,
            role: 'assistant',
            nodes: [],
            _rawText: '',
            proseJsx: (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-secondary)' }}>
                <Loader2 className="animate-spin" size={16} />
                Vajra is thinking…
              </div>
            ),
            deliverable: null,
            timestamp: Date.now(),
          },
        ],
      },
    }));

    // Step 3: Open SSE stream — update bubble token by token
    let accumulated = '';

    // use_active_documents = true when:
    //   a) files were attached (document-scoped retrieval), OR
    //   b) KB toggle is ON (search full shared knowledge base)
    const useActiveDocuments = activeDocumentIds.length > 0 || useKB;

    // Refresh DB doc list after upload so new files show up immediately
    if (newlyUploadedDocumentIds.length > 0) {
      loadDatabaseDocuments();
    }

    const abort = api.streamTask(
      userMsg.content,
      history,
      serverPaths,
      activeDocumentIds,
      useActiveDocuments,

      // onToken
      (token) => {
        accumulated += token;
        const snapshot = accumulated; // closure capture
        setConversations(prev => {
          const conv = prev[chatId];
          if (!conv) return prev;
          return {
            ...prev,
            [chatId]: {
              ...conv,
              messages: conv.messages.map(m =>
                m.id === pendingMsgId
                  ? {
                      ...m,
                      _rawText: snapshot,
                      proseJsx: (
                        <div className="react-markdown">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{snapshot}</ReactMarkdown>
                        </div>
                      ),
                    }
                  : m
              ),
            },
          };
        });
      },
      // onDone
      () => {
        streamAbortRef.current = null;
        setIsProcessing(false);
      },
      // onError
      (errMsg) => {
        streamAbortRef.current = null;
        setConversations(prev => ({
          ...prev,
          [chatId]: {
            ...prev[chatId],
            messages: (prev[chatId]?.messages || []).map(m =>
              m.id === pendingMsgId
                ? { ...m, proseJsx: <p style={{ color: 'var(--danger-red)' }}>Error: {errMsg}</p> }
                : m
            ),
          },
        }));
        setIsProcessing(false);
      }
    );
    streamAbortRef.current = abort;
  };


  const handleDownload = (filename) => {
    const blob = new Blob([
      `SOVEREIGN AIR-GAPPED WORKBENCH DELIVERABLE\nFile: ${filename}\nStatus: VERIFIED ON-PREMISE\nZero cloud telemetry. 100% sovereign inference.`
    ], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  };

  const activeChat = conversations[activeChatId];

  // ── Permission Modal (shared) ──
  const PermissionModal = () => pendingPermission ? (
    <div className="permission-modal-overlay">
      <div className="permission-modal">
        <div className="permission-modal-header">
          <ShieldCheck size={18} color="var(--warning-amber)" />
          <h3>Action Requires Approval</h3>
        </div>
        <div className="permission-modal-body">
          <p>The agent is requesting permission to <strong>{pendingPermission.action}</strong>.</p>
          {pendingPermission.details && (
            <div className="prose-code-block" style={{ marginTop: 10, fontSize: '0.82rem' }}>{pendingPermission.details}</div>
          )}
        </div>
        <div className="permission-modal-actions">
          <button className="permission-btn deny" onClick={() => handleResolvePermission(false)}><X size={13} /> Deny</button>
          <button className="permission-btn allow" onClick={() => handleResolvePermission(true)}><Check size={13} /> Allow Execution</button>
        </div>
      </div>
    </div>
  ) : null;

  // ── VIEW: Homepage ──
  if (currentView === 'homepage') {
    return <HomePage onEnterApp={() => setCurrentView('pipeline')} />;
  }

  // ── VIEW: Pipeline ──
  if (currentView === 'pipeline') {
    return (
      <>
        <PermissionModal />
        <PipelinePage
          onNavigateToChat={handleNavigateToChat}
          databaseDocs={databaseDocs}
          onAddDoc={handleAddDoc}
          onDatabaseChanged={loadDatabaseDocuments}
          dbInputRef={dbInputRef}
          conversations={conversations}
          onSelectConversation={handleSelectConversation}
          onNewSession={handleNewSession}
        />
      </>
    );
  }

  // ── VIEW: Chat (active) ──
  return (
    <div className="app-shell">
      <PermissionModal />

      {/* Grid background */}
      <div className="background-grid-container" aria-hidden="true">
        {Array.from({ length: 140 }).map((_, i) => <div key={i} className="grid-block" />)}
      </div>
      <div className="vignette-overlay" aria-hidden="true" />

      {/* Sidebar */}
      <aside className={`sidebar ${isSidebarOpen ? '' : 'collapsed'}`}>
        <div className="sidebar-header">
          {isSidebarOpen ? (
            <div className="sidebar-brand" onClick={() => setCurrentView('pipeline')}>
              <div className="brand-monogram">V</div>
              <span className="brand-text">Vajra</span>
            </div>
          ) : (
            <div className="sidebar-brand" onClick={() => setCurrentView('pipeline')} title="Vajra AI">
              <div className="brand-monogram">V</div>
            </div>
          )}
          <button className="toggle-sidebar-btn" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
            {isSidebarOpen ? <PanelLeftClose size={14} /> : <PanelLeftOpen size={14} />}
          </button>
        </div>

        <button className="new-chat-btn" onClick={handleNewSession} title="New session">
          <Plus size={13} />
          {isSidebarOpen && <span>New Session</span>}
        </button>

        {isSidebarOpen && <div className="sidebar-section-label">Previous Chats</div>}

        <div className="chat-history-list">
          {Object.values(conversations)
            .sort((a, b) => b.timestamp - a.timestamp)
            .map(chat => (
              <div
                key={chat.id}
                className={`chat-item ${currentView === 'active' && activeChatId === chat.id ? 'active' : ''}`}
                onClick={() => handleSelectConversation(chat.id)}
                title={chat.title}
              >
                <FileText size={13} style={{ opacity: 0.65, flexShrink: 0 }} />
                {isSidebarOpen && <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{chat.title}</span>}
              </div>
            ))}
        </div>

        <div className="sidebar-footer">
          <div className="airgap-indicator-dot" />
          {isSidebarOpen && <span>All inference local · 0 calls</span>}
        </div>
      </aside>

      {/* Main viewport */}
      <main className="main-viewport">
        <header className="viewport-topbar">
          <div className="topbar-title">
            <span
              style={{ cursor: 'pointer', opacity: 0.5, fontSize: 12, marginRight: 8 }}
              onClick={() => setCurrentView('pipeline')}
              title="Back to Pipeline"
            >← Pipeline</span>
            {activeChat ? activeChat.title : 'New Session'}
          </div>
          <div className="topbar-meta">
            <span className="topbar-badge">OLLAMA RUNTIME</span>
            <span className="topbar-badge">4GB VRAM</span>
            <span style={{ color: 'var(--success-green)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>● 127.0.0.1 LOCK</span>
          </div>
        </header>

        {/* ── Chat Thread ── */}
        <div className="chat-thread" ref={chatThreadRef}>
          {(!activeChat || activeChat.messages.length === 0) && (
            <div className="chat-thread-empty">
              <div className="chat-empty-icon"><Zap size={28} /></div>
              <div className="chat-empty-title">Ask Vajra anything</div>
              <div className="chat-empty-sub">
                {attachedFiles.length > 0
                  ? `${attachedFiles.length} file${attachedFiles.length > 1 ? 's' : ''} ready — type a prompt below`
                  : 'Type a prompt below to start a sovereign AI session'}
              </div>
            </div>
          )}

          {activeChat?.messages.map((msg, idx) => {
            if (msg.role === 'user') {
              return (
                <div key={msg.id} className="chat-bubble-user">
                  <div className="chat-bubble-user-inner">
                    {msg.files && msg.files.length > 0 && (
                      <div className="chat-bubble-files">
                        {msg.files.map((f, fi) => (
                          <FileChip key={fi} file={f} showThumb={false} />
                        ))}
                      </div>
                    )}
                    {msg.content && <div className="chat-bubble-text">{msg.content}</div>}
                  </div>
                  <div className="chat-bubble-time">{relTime(msg.timestamp)}</div>
                </div>
              );
            }

            // Assistant message
            return (
              <div key={msg.id} className="chat-bubble-assistant">
                <div className="chat-assistant-avatar">V</div>
                <div className="chat-assistant-body">
                  {msg.nodes && msg.nodes.length > 0 && (
                    <AgentTrace
                      nodes={msg.nodes}
                      activeStage={msg.nodes.length}
                      popoverNode={activePopoverNode}
                      setPopoverNode={setActivePopoverNode}
                    />
                  )}
                  <article className="prose-output-panel">{msg.proseJsx}</article>
                  {msg.deliverable && (
                    <div className="deliverable-strip">
                      <div className="deliverable-strip-left">
                        <div className="deliverable-icon-box">
                          {msg.deliverable.type === 'docx' && <FileText size={16} />}
                          {msg.deliverable.type === 'py' && <FileCode size={16} />}
                          {msg.deliverable.type === 'xlsx' && <FileText size={16} />}
                        </div>
                        <div>
                          <div className="deliverable-name">{msg.deliverable.name}</div>
                          <div className="deliverable-meta">{msg.deliverable.size} · Verified Sovereign Deliverable</div>
                        </div>
                      </div>
                      <div className="deliverable-actions">
                        <button className="deliverable-action-btn" onClick={() => handleDownload(msg.deliverable.name)}>
                          <Download size={12} /> <span>Download</span>
                        </button>
                        <button className="deliverable-action-btn" onClick={() => handleDownload(msg.deliverable.name)}>
                          <ExternalLink size={12} /> <span>Open</span>
                        </button>
                      </div>
                    </div>
                  )}
                  <div className="chat-bubble-time" style={{ marginTop: 6 }}>{relTime(msg.timestamp)}</div>
                </div>
              </div>
            );
          })}
        </div>

        {/* ── Sticky Chat Input Bar ── */}
        <div className="chat-input-bar">
          <div className="chat-context-toggle" role="group" aria-label="Answer source">
            <button
              type="button"
              className={useDocumentContext ? 'active' : ''}
              onClick={() => setUseDocumentContext(true)}
              title="Answer only from files attached to this chat"
            >
              Ask documents
            </button>
            <button
              type="button"
              className={!useDocumentContext ? 'active' : ''}
              onClick={() => setUseDocumentContext(false)}
              title="Ignore attached files and answer from the reasoning model's general knowledge"
            >
              Ask generally
            </button>
          </div>
          {/* File chips row */}
          {attachedFiles.length > 0 && (
            <div className="chat-files-row">
              {attachedFiles.map((f, idx) => (
                <FileChip
                  key={f.name + idx}
                  file={f}
                  onRemove={() => setAttachedFiles(prev => prev.filter((_, i) => i !== idx))}
                  showThumb={true}
                />
              ))}
            </div>
          )}

          <form className="chat-input-form" onSubmit={handleSubmit}>
            {/* + button with popover */}
            <div className="attach-btn-wrap" style={{ position: 'relative', flexShrink: 0 }}>
              <button
                ref={attachBtnRef}
                type="button"
                className={`chat-attach-btn ${attachPopoverOpen ? 'active' : ''}`}
                onClick={() => setAttachPopoverOpen(v => !v)}
                title="Add files, images or workspace"
              >
                <Plus size={16} style={{ transition: 'transform 0.2s', transform: attachPopoverOpen ? 'rotate(45deg)' : 'rotate(0deg)' }} />
              </button>
              {attachPopoverOpen && (
                <div ref={attachPopoverRef}>
                  <AttachPopover
                    onFiles={handleAttachFiles}
                    onWorkspacePath={handleAttachWorkspace}
                    onClose={() => setAttachPopoverOpen(false)}
                  />
                </div>
              )}
            </div>

            <textarea
              className="chat-input-textarea"
              placeholder={isProcessing ? 'Vajra is thinking…' : 'Type your prompt or ask a follow-up question…'}
              value={promptText}
              disabled={isProcessing}
              onChange={e => setPromptText(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              rows={1}
            />
            <button
              type="submit"
              className="chat-send-btn"
              disabled={isProcessing || (!promptText.trim() && attachedFiles.length === 0)}
              title="Send"
            >
              {isProcessing ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            </button>
          </form>

          <div className="chat-input-hint">
            Press <kbd>Enter</kbd> to send · <kbd>Shift+Enter</kbd> for new line · <Paperclip size={9} style={{ display: 'inline', verticalAlign: 'middle' }} /> to attach files
          </div>
        </div>
      </main>
    </div>
  );
}
