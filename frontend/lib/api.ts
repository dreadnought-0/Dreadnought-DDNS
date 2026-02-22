import { TrackedRecord, TrackedRecordCreate, TrackedRecordUpdate, SyncStatus, SyncResult, ImportRequest, AuditEntry, Domain, DomainCreate, DomainUpdate } from '../types'

// Dynamic API base URL resolution.
// Priority:
//   1. NEXT_PUBLIC_API_URL env var (set this for any non-trivial deployment)
//   2. window.location.origin (works when the frontend and API share the same
//      origin, e.g. behind a reverse proxy that routes /api/* to the backend)
//   3. SSR fallback – 'http://localhost:8081' for local development
//
// For direct Docker Compose access (frontend on :8082, API on :8081) docker-compose.yml
// already sets NEXT_PUBLIC_API_URL=http://localhost:8081, so the fallback is never used.
const getApiBase = () => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL
  }

  if (typeof window !== 'undefined') {
    return window.location.origin
  }

  return 'http://localhost:8081'
}

async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const API_BASE = getApiBase() // Get fresh API base for each request
  const url = `${API_BASE}${endpoint}`
  
  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`
    try {
      const errorData = await response.json()
      errorMessage = errorData.detail || errorMessage
    } catch (e) {
      // Use default error message
    }
    throw new Error(errorMessage)
  }

  const contentType = response.headers.get('content-type')
  if (contentType && contentType.includes('application/json')) {
    return response.json()
  }
  
  return response.text()
}

export const api = {
  // Auth
  login: async (email: string, password: string) => {
    return fetchApi('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  },

  logout: async () => {
    return fetchApi('/api/auth/logout', {
      method: 'POST',
    })
  },

  getCurrentUser: async () => {
    return fetchApi('/api/auth/me')
  },

  // Records
  getRecords: async (filters?: { domain?: string; fqdn?: string; record_type?: string }): Promise<TrackedRecord[]> => {
    const params = new URLSearchParams()
    if (filters?.domain) params.set('domain', filters.domain)
    if (filters?.fqdn) params.set('fqdn', filters.fqdn)
    if (filters?.record_type) params.set('record_type', filters.record_type)
    
    const query = params.toString() ? `?${params.toString()}` : ''
    return fetchApi(`/api/records${query}`)
  },

  createRecord: async (record: TrackedRecordCreate): Promise<TrackedRecord> => {
    return fetchApi('/api/records', {
      method: 'POST',
      body: JSON.stringify(record),
    })
  },

  updateRecord: async (id: number, record: TrackedRecordUpdate): Promise<TrackedRecord> => {
    return fetchApi(`/api/records/${id}`, {
      method: 'PUT',
      body: JSON.stringify(record),
    })
  },

  deleteRecord: async (id: number, deleteFromCloudflare: boolean = true) => {
    const params = new URLSearchParams()
    params.set('delete_from_cloudflare', deleteFromCloudflare.toString())
    return fetchApi(`/api/records/${id}?${params.toString()}`, {
      method: 'DELETE',
    })
  },

  // Sync
  manualSync: async (): Promise<SyncResult> => {
    return fetchApi('/api/sync', {
      method: 'POST',
    })
  },

  getStatus: async (): Promise<SyncStatus> => {
    return fetchApi('/api/status')
  },

  // Import
  importRecords: async (importData: ImportRequest) => {
    return fetchApi('/api/import', {
      method: 'POST',
      body: JSON.stringify(importData),
    })
  },

  // Audit
  getAuditLog: async (limit: number = 50, offset: number = 0): Promise<AuditEntry[]> => {
    const params = new URLSearchParams()
    params.set('limit', limit.toString())
    params.set('offset', offset.toString())
    return fetchApi(`/api/audit?${params.toString()}`)
  },

  // Settings
  getSetting: async (key: string) => {
    return fetchApi(`/api/settings/${key}`)
  },

  updateSetting: async (key: string, value: string) => {
    return fetchApi(`/api/settings/${key}`, {
      method: 'PUT',
      body: JSON.stringify({ value }),
    })
  },

  // Domains
  getDomains: async (): Promise<Domain[]> => {
    return fetchApi('/api/domains')
  },

  createDomain: async (domain: DomainCreate): Promise<Domain> => {
    return fetchApi('/api/domains', {
      method: 'POST',
      body: JSON.stringify(domain),
    })
  },

  updateDomain: async (id: number, domain: DomainUpdate): Promise<Domain> => {
    return fetchApi(`/api/domains/${id}`, {
      method: 'PUT',
      body: JSON.stringify(domain),
    })
  },

  deleteDomain: async (id: number) => {
    return fetchApi(`/api/domains/${id}`, {
      method: 'DELETE',
    })
  },
}