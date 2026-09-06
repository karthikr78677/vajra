import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Check for pending permissions
  getPendingPermissions: async () => {
    const response = await apiClient.get('/permissions/pending');
    return response.data;
  },

  // Approve or deny a permission request
  resolvePermission: async (taskId, approved) => {
    const response = await apiClient.post('/permissions/approve', {
      task_id: taskId,
      approved: approved
    });
    return response.data;
  },
  
  // Submit a task for full processing (non-streaming fallback if needed)
  processTask: async (query, filePaths = []) => {
    const response = await apiClient.post('/process', {
      query,
      file_paths: filePaths
    });
    return response.data;
  }
};

// Expose the base URL for SSE EventSource
export const SSE_URL = `${API_BASE_URL}/stream`;
