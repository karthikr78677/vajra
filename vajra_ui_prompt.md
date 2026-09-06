# 🎨 Vajra AI Workbench — Complete UI Design Prompt
### For the Frontend Team

---

## 🧠 Project Overview

**Vajra** is a **self-hosted, air-gapped AI workbench** built for industrial and enterprise use.
It runs entirely on local hardware (no cloud), using local Ollama LLMs for:

- **Reasoning** — Q&A, tool-calling, document analysis
- **Coding** — multi-file code generation (HTML/CSS/JS/Python)
- **Vision** — image analysis, PDF/OCR extraction

The UI must feel like a **premium SaaS product** (think Linear, Vercel Dashboard, or Notion AI) — but adapted for industrial AI workflows.

---

## 🎯 Design Philosophy

| Principle | Requirement |
|---|---|
| **Dark-first** | Default dark mode (#0d1117 base, #161b22 surfaces) |
| **Glassmorphism** | Translucent panels with backdrop-filter blur for cards and sidebars |
| **Responsive** | Works on 1920×1080 desktops AND 1280×800 laptops |
| **Real-time feel** | Streaming output (tokens appear word by word), live progress indicators |
| **Industrial** | Vajra is used in factories/plants — UI must be legible, not just pretty |
| **Premium animations** | Subtle micro-animations, smooth transitions (0.2–0.3s ease), no janky jumps |

### Color Palette
```
Background (darkest)  : #0d1117
Surface (panels)      : #161b22
Surface elevated      : #1c2128
Border                : #30363d
Text primary          : #e6edf3
Text secondary        : #8b949e
Accent (Vajra blue)   : #58a6ff
Accent hover          : #79c0ff
Success green         : #3fb950
Warning amber         : #d29922
Danger red            : #f85149
Gradient accent       : linear-gradient(135deg, #58a6ff, #a371f7)
```

### Typography
- **Font**: `Inter` (headings) + `JetBrains Mono` (code / model output)
- Import from Google Fonts

---

## 🏗️ Application Structure — Pages & Sections

---

### 1. 🔐 Authentication Page (`/login`, `/signup`)

**Design:**
- Full-screen dark background with an animated subtle particle/grid overlay
- Centered glassmorphism card (frosted glass, border glow)
- Vajra logo + tagline: *"Intelligence. Sovereign. On-Premise."*

**Login Form:**
- Email + Password fields (with show/hide password toggle)
- "Remember me" checkbox
- `Sign In` button (gradient accent, glow on hover)
- Link to Sign Up
- Optional: `Sign in with SSO / LDAP` button for enterprise use

**Sign Up Form:**
- Full Name, Email, Password, Confirm Password
- Role selector dropdown: `Admin | Analyst | Engineer | Viewer`
- Terms & Conditions checkbox
- `Create Account` button

**Extras:**
- Error toast notifications (e.g., "Invalid credentials")
- Forgot password link
- Smooth slide/fade transition between login ↔ signup forms

---

### 2. 🏠 Dashboard / Home Page (`/dashboard`)

**Layout:** Left sidebar + main content area + right panel (collapsible)

**Left Sidebar (fixed, collapsible):**
- Vajra logo at top
- Navigation links with icons:
  - 🏠 Dashboard
  - 💬 Chat / Agent
  - 📁 File Manager
  - 🧠 Model Manager
  - ⚙️ Settings
  - 📊 Usage & Logs
  - 👤 Profile
- Collapse/expand toggle button at bottom
- Online status badge (🟢 Ollama Connected / 🔴 Offline)
- Active model pill: e.g., `🤖 qwen2.5-coder:3b`

**Main Content — Dashboard Cards:**
- **Welcome Banner**: "Good morning, [User]. Vajra is ready." with today's date
- **Quick Stats Cards** (glassmorphism):
  - Total Tasks Run Today
  - Files Generated
  - Models Available
  - Avg. Response Time
- **Recent Activity Feed**: Last 10 tasks with type icon, query preview, timestamp
- **Quick Action Buttons**:
  - `+ New Chat Session`
  - `📤 Upload Document`
  - `🔧 Build a Project`
- **System Status Panel** (right side):
  - GPU VRAM usage bar
  - RAM usage bar
  - Ollama model loaded indicator
  - CPU temperature (if available)

---

### 3. 💬 Agent Chat Page (`/chat`)

This is the **core feature** — the main interaction UI.

**Layout:** 3-column (sidebar | chat area | context panel)

#### Left: Session Sidebar
- `+ New Session` button
- List of past sessions with:
  - Mode icon (🧠 Reasoning | 💻 Coding | 👁️ Vision)
  - Session title (auto-generated from first query)
  - Timestamp
  - Delete session button (appears on hover)
- Search bar to filter past sessions

#### Center: Chat Area
- Clean chat bubbles:
  - **User messages**: right-aligned, accent color background
  - **Agent messages**: left-aligned, surface elevated background, with avatar (Vajra logo icon)
- **Streaming output**: text appears token by token with a blinking cursor
- **Agent Trace Accordion**: collapsible section below each response showing:
  - Step number, Action type (write_file / analyze_image / calculate)
  - Thought text
  - Observation (result)
  - Color-coded: ✅ success, ❌ failure, ⚠️ warning
- **File output cards**: when agent generates files, show a card with:
  - File name + extension icon (📄 .html, 🎨 .css, ⚡ .js)
  - File size
  - `📋 Copy` and `📥 Download` buttons
  - `🌐 Open in Browser` button (for HTML files)
  - Code preview (syntax highlighted, collapsible)

#### Input Area (bottom, sticky):
- **Multi-line text input** (auto-expands up to 6 lines)
- **Mode selector tabs**: `🧠 Reasoning` | `💻 Coding` | `👁️ Vision` (with keyboard shortcuts)
- **Attach buttons**:
  - `📎 Upload File` — opens file picker (supports: .png, .jpg, .pdf, .txt, .csv, .docx)
  - `📁 Paste Path` — input field for manual path entry (for local files)
  - `🗂️ Multiple Files` — upload multiple files at once, shows thumbnail grid preview
- **Send button** (gradient, animated on hover)
- **Stop Generation** button (appears during streaming, red, pulsing)
- Character/token counter (bottom right of input)
- Example prompts (chips below input when input is empty):
  - `"Analyse this P&ID diagram"`
  - `"Build a snake game with index.html, style.css, script.js"`
  - `"Summarise this PDF report"`

#### Right: Context Panel (collapsible)
- **Active Model**: name, size, task type badge
- **Session Info**: token usage, duration, task count
- **Workspace Path**: current output directory with `📁 Open Folder` link
- **Uploaded Files**: thumbnails/list of all files uploaded in this session

---

### 4. 📤 File Upload & Management (`/files`)

**Features:**
- **Drag & Drop Zone**: large glassmorphism drop area with animated dashed border
- **Multiple file upload**: select many files at once, shows a progress list
- **Path input**: text field to enter an absolute local path (e.g., `C:\Users\HP\Documents\report.pdf`)
- **File List Table** with columns:
  - Checkbox (for bulk actions)
  - File icon + name
  - Type (PDF / Image / Text)
  - Size
  - Uploaded at
  - Actions: `Analyse` | `Extract Text` | `Delete`
- **Bulk Actions Toolbar**: Delete Selected, Download Selected, Send to Agent
- **Preview Panel** (right slide-out):
  - Image: actual preview
  - PDF: page count, metadata
  - Text: first 500 characters preview
- **Filter & Sort** bar: filter by type, sort by name/date/size

---

### 5. 🧠 Model Manager (`/models`)

**Overview Cards** — one card per task type:

```
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│  🧠 REASONING        │  │  💻 CODING           │  │  👁️ VISION          │
│  qwen2.5:3b         │  │  qwen2.5-coder:3b    │  │  moondream:latest   │
│  ● Active           │  │  ● Active            │  │  ● Active           │
│  [Change Model ▼]   │  │  [Change Model ▼]    │  │  [Change Model ▼]   │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

**Installed Models Table:**
- Model name, size on disk, quantization level (Q4, Q8)
- Last used timestamp
- Actions: `Set as Reasoning` | `Set as Coding` | `Set as Vision` | `Delete`

**Pull New Model Section:**
- Input field: `ollama pull <model-name>`
- Popular model chips: `qwen2.5:7b` | `llama3.1:8b` | `codellama:7b` | `phi4:latest`
- Real-time download progress bar with speed (MB/s) and ETA

**Ollama Status Card:**
- Connection status badge
- Server URL (editable)
- `Test Connection` button
- GPU VRAM used / available bar

---

### 6. ⚙️ Settings Page (`/settings`)

Organized into tabbed sections:

#### Tab 1: 🏢 Workspace
- Vajra Workspace root path (file picker)
- Max file size limit (slider)
- Allowed file types (multi-select chips)
- Auto-delete temp files toggle

#### Tab 2: 🤖 AI Configuration
- Ollama Base URL input
- Request timeout slider (30s – 300s)
- Max retries spinner
- Default task mode selector (Reasoning / Coding / Vision)
- Streaming output toggle (on/off)
- Context passing toggle (pass previous files to next file generation — on/off)

#### Tab 3: 🔐 Security
- Enable workspace path restriction toggle
- Allowed workspace directories (add/remove list)
- API key management (for future cloud model integration)
- Session timeout (minutes)

#### Tab 4: 🎨 Appearance
- Theme: Dark | Light | System
- Accent color picker (preset swatches)
- Font size (Small / Medium / Large)
- Code font selector (JetBrains Mono / Fira Code / Cascadia Code)
- Animation speed (None / Subtle / Full)

#### Tab 5: 🔔 Notifications
- Desktop notifications toggle
- Sound effects toggle
- Show agent trace by default toggle
- Auto-scroll to latest output toggle

**Save/Reset buttons** — sticky at page bottom. Show toast: "Settings saved ✅"

---

### 7. 📊 Usage & Logs (`/logs`)

**Usage Overview:**
- Bar chart: tasks per day (last 7 days), color-coded by type
- Pie chart: Reasoning vs Coding vs Vision breakdown
- Cards: Total queries, Files created, Errors, Avg response time

**Live Log Viewer:**
- Real-time streaming log viewer (like a terminal but styled)
- Color-coded log levels: INFO (blue), WARNING (amber), ERROR (red), DEBUG (gray)
- Search/filter input
- Auto-scroll toggle
- Download logs button

**Task History Table:**
- Session ID, Task type, Query preview, Status, Duration, Timestamp
- Expandable row to show full agent trace

---

### 8. 👤 Profile Page (`/profile`)

- Avatar (initials or uploaded photo)
- Full name, email, role badge
- Change password form
- API tokens (generate / revoke for programmatic access)
- Active sessions list with `Revoke` button

---

## 🧩 Global UI Components

### 🔔 Toast Notifications
- Top-right corner, auto-dismiss after 4s
- Types: Success ✅, Error ❌, Warning ⚠️, Info ℹ️
- Smooth slide-in animation

### ⌨️ Command Palette (`Ctrl+K`)
- Full-screen overlay, fuzzy search across all pages and actions
- E.g., "New chat", "Upload file", "Change coding model", "Open logs"

### 🌐 Status Bar (bottom of screen)
- 🟢 Ollama: Connected | Current model | GPU VRAM | App version

### 💡 Onboarding Tour
- First-time user gets a step-by-step highlight tour of each section
- Skippable, resumable from Help menu

---

## 🔌 Backend API Contract (for the team to align with)

The frontend connects to a **local FastAPI backend** (already built). Key endpoints:

```
POST   /api/chat          → send query, returns streamed SSE response
GET    /api/models        → list all Ollama models
POST   /api/models/pull   → pull a new model
PUT    /api/config        → update router_config.yaml
POST   /api/upload        → upload file(s), returns filepath(s)
GET    /api/logs          → fetch system logs
GET    /api/health        → Ollama connection + GPU status
POST   /api/auth/login    → JWT login
POST   /api/auth/signup   → register user
GET    /api/sessions      → list past chat sessions
DELETE /api/sessions/{id} → delete a session
```

The streaming chat endpoint (`/api/chat`) uses **Server-Sent Events (SSE)** — implement with `EventSource` on the frontend to render tokens in real time.

---

## 🛠️ Recommended Tech Stack (for the UI team)

| Layer | Recommendation |
|---|---|
| Framework | **Next.js 14** (App Router) or **Vite + React** |
| Styling | **Tailwind CSS** + custom CSS variables for the glassmorphism |
| Icons | **Lucide React** or **Heroicons** |
| Charts | **Recharts** or **Chart.js** |
| Code highlighting | **Prism.js** or **Shiki** |
| Animations | **Framer Motion** |
| State | **Zustand** (lightweight) |
| API client | **Axios** + custom SSE hook for streaming |
| Auth | **JWT stored in httpOnly cookie** |

---

## 📐 Wireframe Priority Order

Build in this order:

1. `Authentication` (Login / Signup)
2. `Chat Page` (core feature — this is what users use 90% of the time)
3. `Model Manager` (users need to change models)
4. `Settings` (configuration)
5. `Dashboard` (overview)
6. `File Manager` (upload & management)
7. `Logs & Usage`
8. `Profile`

---

## ✅ Definition of "Done" for each page

A page is complete when:
- [ ] All described sections are implemented
- [ ] Dark mode is default and looks premium
- [ ] Responsive at 1280px and 1920px widths
- [ ] All buttons have hover + active states
- [ ] Loading states are shown during API calls (skeletons, spinners)
- [ ] Error states are handled gracefully (toast + retry button)
- [ ] Streaming output works (SSE tokens render in real time)
- [ ] Keyboard shortcuts work (Ctrl+K command palette, Enter to send, Escape to close modals)
