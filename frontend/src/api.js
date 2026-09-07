import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  listDocuments: async () => {
    const response = await apiClient.get('/documents');
    return response.data;
  },

  // ── Permissions ─────────────────────────────────────────────────────────────

  getPendingPermissions: async () => {
    const response = await apiClient.get('/permissions/pending');
    return response.data;
  },

  resolvePermission: async (taskId, approved) => {
    const response = await apiClient.post('/permissions/approve', {
      task_id: taskId,
      approved,
    });
    return response.data;
  },

  // ── File Upload ──────────────────────────────────────────────────────────────

  /**
   * Upload one or more File objects to the server.
   * Returns { paths: string[], errors: [] }
   * paths contains the absolute server-side file paths to use in processTask / ingest.
   */
  uploadFiles: async (files) => {
    const form = new FormData();
    files.forEach((f) => {
      if (f instanceof File) form.append('files', f);
    });
    if (!form.has('files')) return { paths: [], documents: [], errors: [] };
    // NOTE: Do NOT set Content-Type header manually — axios sets it
    // automatically with the correct multipart boundary string.
    const response = await apiClient.post('/upload', form);
    return response.data; // { paths, documents, errors }
  },

  // ── ChromaDB Ingest ──────────────────────────────────────────────────────────

  /**
   * Index uploaded files and/or a local workspace folder into ChromaDB.
   * filePaths: absolute server paths returned by uploadFiles()
   * workspacePath: local folder path string from the workspace chip (optional)
   * domain: domain label string
   */
  ingestDocuments: async ({ filePaths = [], documentIds = [], workspacePath = null, domain = 'General' }) => {
    const response = await apiClient.post('/ingest', {
      file_paths: filePaths,
      document_ids: documentIds,
      workspace_path: workspacePath,
      domain,
    });
    return response.data; // { status, indexed_chunks, files, errors }
  },

  // ── Blocking Process (non-streaming fallback) ────────────────────────────────

  processTask: async (query, filePaths = [], history = []) => {
    const response = await apiClient.post('/process', {
      query,
      file_paths: filePaths,
      history,
    });
    return response.data;
  },

  // ── SSE Streaming ────────────────────────────────────────────────────────────

  /**
   * Open an SSE stream for a chat turn.
   *
   * @param {string}   query       Current user prompt
   * @param {Array}    history     Prior {role, content} messages
   * @param {Array}    filePaths   Absolute server paths of uploaded files
   * @param {Function} onToken     Called with each text token chunk: onToken(str)
   * @param {Function} onDone      Called when stream completes
   * @param {Function} onError     Called with error message on failure
   * @returns {Function}           abort() — call to cancel the stream
   */
  streamTask: (query, history = [], filePaths = [], activeDocumentIds = [], useActiveDocuments = true, onToken, onDone, onError) => {
    const abortController = new AbortController();

    (async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            history,
            file_paths: filePaths,
            active_document_ids: activeDocumentIds,
            use_active_documents: useActiveDocuments,
          }),
          signal: abortController.signal,
        });

        if (!response.ok) {
          const text = await response.text();
          throw new Error(`Server error ${response.status}: ${text}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // SSE events are separated by double-newline (\n\n or \r\n\r\n)
          const parts = buffer.split(/\r?\n\r?\n/);
          buffer = parts.pop() ?? ''; // keep the incomplete last chunk

          for (const part of parts) {
            if (!part.trim()) continue;

            // Each SSE event may have multiple lines (id:, event:, data:)
            // We only care about "data:" lines
            const lines = part.split(/\r?\n/);
            for (const line of lines) {
              if (!line.startsWith('data:')) continue;
              const payload = line.slice(5).trim(); // strip "data: "
              if (!payload) continue;

              if (payload === '[DONE]') {
                onDone && onDone();
                return;
              }

              try {
                const parsed = JSON.parse(payload);
                if (parsed.token) onToken && onToken(parsed.token);
                if (parsed.error) {
                  onError && onError(parsed.error);
                  return;
                }
              } catch (_) {
                // Non-JSON data line — treat as raw token text
                if (payload) onToken && onToken(payload);
              }
            }
          }
        }
        // Stream ended without [DONE] — still call done
        onDone && onDone();

      } catch (err) {
        if (err.name === 'AbortError') return; // user cancelled
        onError && onError(err.message || String(err));
      }
    })();

    return () => abortController.abort(); // return abort function
  },

  // ── Delete document from registry ─────────────────────────────────────────
  deleteDocument: async (documentId) => {
    const response = await apiClient.delete(`/documents/${documentId}`);
    return response.data;
  },
};


// Expose the base URL for any direct EventSource usage
export const SSE_URL = `${API_BASE_URL}/stream`;
