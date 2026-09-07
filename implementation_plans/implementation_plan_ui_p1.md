# Vajra Frontend Redesign — UI Template Implementation

## Overview

Redesign the Vajra frontend to match the two UI template images provided:
1. **Home Page** (`ui_tempalte_home_page.jpg`) — A marketing/landing page shown on app load
2. **Main App Page** (`ui_second_page.jpg`) — The "Knowledge Ingestion & Vector Pipeline" page, navigated to via the `>` chevron button

The current app uses a single-page with `landing` and `active` states. We'll add a new `homepage` view that renders on load, and rename the existing landing to the main pipeline page reached by clicking `>`.

---

## Proposed Changes

### Page Flow
```
App Loads → HOME PAGE (ui_tempalte_home_page.jpg)
  └── Click ">" (chevron/play button) → MAIN APP PAGE (ui_second_page.jpg)
        └── Existing conversation/chat functionality preserved
```

---

### Component 1: Home Page (new `homepage` view)

Matches `ui_tempalte_home_page.jpg`:

**Top Navigation Bar** (light/minimal, semi-transparent):
- "vajra" logo (bold) on the left
- Nav links: `Why Sovereign`, `What We Do`, `Latest News`, `Free CRM Audit`, `Get In Touch`
- CTA button: `Schedule a Call Now` (outlined pill)

**Hero Section** (centered):
- Play/chevron icon button `▶` (acts as the navigate-to-app button)
- Large serif headline: `Nothing gets` *through* / `Nothing gets` **Lost** (mixed italic + badge style)
- Subtext: `Strength you can trust - Security you can see`

**App Preview Mockup** (browser window mock):
- Shows the "Ask Vajra" interface in a browser frame
- Includes the query input box with suggestions
- Vajra Synthesis Stream bar at the bottom of the mockup

---

### Component 2: Main App Page (redesigned `landing` → renamed `pipeline`)

Matches `ui_second_page.jpg`:

**Top Bar**:
- "sovereign" branding on left with breadcrumb: `Core Engine / Knowledge & Vector Pipeline`
- Status indicators: `index.vpath://live-q3` (green dot), `Latency: 288s`, `Node: soc2-vault-us-east-1`
- User avatar (Vi) on the right

**Page Title** area:
- `Knowledge Ingestion & Vector Pipeline` (h1)
- `Model Parameters` button (top right)

**Section 1: Select Ingestion Source**
- Label: `1. SELECT INGESTION SOURCE` + supported formats
- 4 source cards in a grid:
  1. 📤 **Upload Local File** (ACTIVE badge, green border) — Direct upload CSV, PDF, JSON, or research transcripts / `Direct chunking`
  2. 🗂️ **Local Workspace** — Mount `vpath://datasets/` storage pool / `Fastest transfer`
  3. 🔗 **Connect HubSpot / CRM** — Automatic real-time sync with deal properties / `Continuous sync`
  4. 🖼️ **Media & Diagrams** — Multi-modal visual embeddings for architectural charts / `Vision-v3`

**Section 2: Target Data & Pipeline Configuration**
- File drop zone (large dashed area):
  - Cloud upload icon
  - "Drop research transcripts, tabular data, or financial PDFs here"
  - Supports multi-file upload up to 250MB per batch. Files encrypted via SOC-2 Type II standards.
  - `Browse Local Explorer` button (outlined)
- Storage/Virtual Cluster Path input:
  - Path verified checkmark
  - Input: `/mnt/storage/research/q3-briefs/financial_transcripts`
  - `Start Ingest →` button (green, right-aligned)
- Assigned Domain dropdown: `Research & Financial Briefs`

**Footer Bar** (dark strip):
- Green dot + `VAJRA SYNTHESIS STREAM`
- Quote: "Acme Global Enterprise deal migration ($246,500) completed SOC-2 review with 94% health score. Vectors ready for query evaluation."
- `Test Query in Ask Vajra →` button (pill, right-aligned)

**Bottom Status Bar**:
- `Sovereign OS` | `Data Vector Isolation Layer` | `Status: All Ensembles Operational`
- `API: v2.4 stream` | `Build: 884629`

---

### Files to Modify

#### [MODIFY] [App.jsx](file:///c:/Users/HP/Downloads/vajra/frontend/src/App.jsx)
- Add new `currentView === 'homepage'` state as the default (replaces 'landing')
- Add `HomePage` component with full marketing page layout
- Add `PipelinePage` component matching `ui_second_page.jpg` (replaces old landing page)
- The `>` / chevron button on home page navigates to `'pipeline'` view
- Preserve existing `active` view (conversation) logic

#### [MODIFY] [index.css](file:///c:/Users/HP/Downloads/vajra/frontend/src/index.css)
- Add new CSS variables for the blue-accent dark theme used in the main app page
- Add styles for: nav bar, hero section, browser mockup, source cards, drop zone, footer stream bar
- Preserve all existing styles for conversation view

#### [MODIFY] [index.html](file:///c:/Users/HP/Downloads/vajra/frontend/index.html)
- Update title to `Vajra — Sovereign AI Workbench`
- Add Inter font (used in the template designs)

---

## Verification Plan

### Manual Verification
1. App loads → Home page displays with nav bar, hero text, and browser mockup
2. Click the `▶` button → navigates to the pipeline/main page
3. Pipeline page shows all 4 source cards, file drop zone, path input, domain dropdown
4. Clicking a chat session from sidebar → shows conversation view (unchanged)
5. All hover animations and micro-interactions work smoothly
