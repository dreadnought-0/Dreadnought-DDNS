import {
  TrackedRecord,
  TrackedRecordCreate,
  TrackedRecordUpdate,
  SyncStatus,
  SyncResult,
  ImportRequest,
  AuditEntry,
  Domain,
  DomainCreate,
  DomainUpdate,
} from '../types'

// ---------------------------------------------------------------------------
// Demo in-memory state
// ---------------------------------------------------------------------------

const isDemoLoggedIn = (): boolean => {
  if (typeof window === 'undefined') return false
  return sessionStorage.getItem('demo_logged_in') === 'true'
}

const setDemoLoggedIn = (value: boolean): void => {
  if (typeof window === 'undefined') return
  if (value) {
    sessionStorage.setItem('demo_logged_in', 'true')
  } else {
    sessionStorage.removeItem('demo_logged_in')
  }
}

let domains: Domain[] = [
  {
    id: 1,
    name: 'example.com',
    zone_id: 'abc123def456abc123def456abc12345',
    created_at: '2024-11-01T08:00:00',
    updated_at: '2024-11-01T08:00:00',
  },
  {
    id: 2,
    name: 'demo.net',
    zone_id: 'fedcba9876543210fedcba9876543210',
    created_at: '2024-11-15T10:30:00',
    updated_at: '2024-11-15T10:30:00',
  },
]

let records: TrackedRecord[] = [
  {
    id: 1,
    domain: 'example.com',
    host: 'vpn',
    fqdn: 'vpn.example.com',
    type: 'A',
    proxied: false,
    ttl: 300,
    zone_identifier: 'abc123def456abc123def456abc12345',
    zone_id_cached: 'abc123def456abc123def456abc12345',
    created_at: '2024-11-01T08:05:00',
    updated_at: '2025-02-20T14:22:00',
  },
  {
    id: 2,
    domain: 'example.com',
    host: 'www',
    fqdn: 'www.example.com',
    type: 'A',
    proxied: true,
    ttl: 300,
    zone_identifier: 'abc123def456abc123def456abc12345',
    zone_id_cached: 'abc123def456abc123def456abc12345',
    created_at: '2024-11-01T08:10:00',
    updated_at: '2025-02-20T14:22:00',
  },
  {
    id: 3,
    domain: 'demo.net',
    host: '@',
    fqdn: 'demo.net',
    type: 'A',
    proxied: false,
    ttl: 300,
    zone_identifier: 'fedcba9876543210fedcba9876543210',
    zone_id_cached: 'fedcba9876543210fedcba9876543210',
    created_at: '2024-11-15T10:35:00',
    updated_at: '2025-02-20T14:22:00',
  },
]

let nextId = 100

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

export const showDemoToast = (message: string, type: 'success' | 'error' = 'success'): void => {
  if (typeof window === 'undefined') return
  const toast = document.createElement('div')
  const bg = type === 'success' ? 'bg-green-500' : 'bg-red-500'
  toast.className = `fixed bottom-6 right-6 ${bg} text-white px-5 py-3 rounded-lg shadow-xl z-[200] text-sm font-medium transition-opacity duration-300`
  toast.textContent = message
  document.body.appendChild(toast)
  setTimeout(() => {
    toast.style.opacity = '0'
    setTimeout(() => {
      if (document.body.contains(toast)) document.body.removeChild(toast)
    }, 300)
  }, 3000)
}

// ---------------------------------------------------------------------------
// Demo API
// ---------------------------------------------------------------------------

export const demoApi = {
  // Auth
  login: async (email: string, password: string): Promise<any> => {
    await delay(600)
    if (email === 'me@example.com' && password === 'admin') {
      setDemoLoggedIn(true)
      return { message: 'Login successful' }
    }
    throw new Error('Invalid credentials. Use me@example.com / admin')
  },

  logout: async (): Promise<any> => {
    await delay(200)
    setDemoLoggedIn(false)
    return {}
  },

  getCurrentUser: async (): Promise<any> => {
    await delay(150)
    if (!isDemoLoggedIn()) throw new Error('Not authenticated')
    return { id: 1, email: 'me@example.com', created_at: '2024-11-01T00:00:00' }
  },

  // Records
  getRecords: async (filters?: { domain?: string; fqdn?: string; record_type?: string }): Promise<TrackedRecord[]> => {
    await delay(200)
    let result = [...records]
    if (filters?.domain) result = result.filter((r) => r.domain.includes(filters.domain!))
    if (filters?.fqdn) result = result.filter((r) => r.fqdn.includes(filters.fqdn!))
    if (filters?.record_type) result = result.filter((r) => r.type === filters.record_type)
    return result
  },

  createRecord: async (record: TrackedRecordCreate): Promise<TrackedRecord> => {
    await delay(700)
    const fqdn = record.host === '@' ? record.domain : `${record.host}.${record.domain}`
    const newRecord: TrackedRecord = {
      id: nextId++,
      domain: record.domain,
      host: record.host,
      fqdn,
      type: record.type,
      proxied: record.proxied,
      ttl: record.proxied ? 300 : record.ttl,
      zone_identifier: record.zone_identifier || '',
      zone_id_cached: record.zone_identifier || '',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    records.push(newRecord)
    showDemoToast('Record created successfully')
    return newRecord
  },

  updateRecord: async (id: number, record: TrackedRecordUpdate): Promise<TrackedRecord> => {
    await delay(700)
    const index = records.findIndex((r) => r.id === id)
    if (index === -1) throw new Error('Record not found')
    const updated = { ...records[index], ...record, updated_at: new Date().toISOString() }
    if (record.host || record.domain) {
      const host = record.host ?? records[index].host ?? '@'
      const domain = record.domain ?? records[index].domain
      updated.fqdn = host === '@' ? domain : `${host}.${domain}`
    }
    records[index] = updated
    showDemoToast('Record updated successfully')
    return records[index]
  },

  deleteRecord: async (id: number, _deleteFromCloudflare: boolean = true): Promise<any> => {
    await delay(500)
    records = records.filter((r) => r.id !== id)
    showDemoToast('Record deleted successfully')
    return {}
  },

  // Sync
  manualSync: async (): Promise<SyncResult> => {
    await delay(1800)
    showDemoToast('Sync completed — demo mode, no real changes made')
    return {
      start_time: new Date().toISOString(),
      end_time: new Date().toISOString(),
      duration_seconds: 1.8,
      status: 'completed',
      ip_changed: false,
      ipv4: '203.0.113.42',
      records_processed: records.length,
      records_updated: 0,
      records_failed: 0,
      details: records.map((r) => ({
        fqdn: r.fqdn,
        type: r.type,
        status: 'success',
        message: 'Demo mode — no actual Cloudflare update performed',
      })),
    }
  },

  getStatus: async (): Promise<SyncStatus> => {
    await delay(200)
    return {
      last_seen_ipv4: '203.0.113.42',
      last_seen_ipv6: undefined,
      last_sync_at: new Date(Date.now() - 4 * 60 * 1000).toISOString(),
      last_sync_result: 'Demo mode — sync completed, 3 records processed, 0 updated',
    }
  },

  // Import
  importRecords: async (importData: ImportRequest): Promise<any> => {
    await delay(900)
    if (importData.dry_run) {
      return {
        dry_run: true,
        records_processed: importData.records.length,
        records_created: 0,
        records_failed: 0,
        details: importData.records.map((r) => ({
          domain: r.domain,
          host: r.host,
          ip_version: r.ip_version,
          status: 'would_create',
          message: 'Demo mode — record would be created',
        })),
      }
    }
    const created = importData.records.map((r) => {
      const fqdn = r.host === '@' ? r.domain : `${r.host}.${r.domain}`
      const newRecord: TrackedRecord = {
        id: nextId++,
        domain: r.domain,
        host: r.host,
        fqdn,
        type: r.ip_version === 6 ? 'AAAA' : 'A',
        proxied: r.proxied,
        ttl: r.ttl,
        zone_identifier: '',
        zone_id_cached: '',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
      records.push(newRecord)
      return {
        domain: r.domain,
        host: r.host,
        ip_version: r.ip_version,
        status: 'created',
        message: 'Demo mode — record created in memory',
      }
    })
    showDemoToast(`Imported ${importData.records.length} record(s) successfully`)
    return {
      dry_run: false,
      records_processed: importData.records.length,
      records_created: importData.records.length,
      records_failed: 0,
      details: created,
    }
  },

  // Audit
  getAuditLog: async (_limit: number = 50, _offset: number = 0): Promise<AuditEntry[]> => {
    await delay(200)
    return [
      {
        id: 1,
        ts: new Date(Date.now() - 4 * 60 * 1000).toISOString(),
        action: 'sync_complete',
        details: { records_processed: 3, records_updated: 0, records_failed: 0 },
      },
      {
        id: 2,
        ts: new Date(Date.now() - 35 * 60 * 1000).toISOString(),
        action: 'record_created',
        details: { fqdn: 'vpn.example.com', type: 'A' },
      },
      {
        id: 3,
        ts: new Date(Date.now() - 70 * 60 * 1000).toISOString(),
        action: 'sync_complete',
        details: { records_processed: 3, records_updated: 0, records_failed: 0 },
      },
      {
        id: 4,
        ts: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        action: 'record_created',
        details: { fqdn: 'www.example.com', type: 'A' },
      },
      {
        id: 5,
        ts: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
        action: 'record_created',
        details: { fqdn: 'demo.net', type: 'A' },
      },
    ]
  },

  // Settings
  getSetting: async (key: string): Promise<any> => {
    await delay(100)
    const defaults: Record<string, string> = {
      poll_interval_seconds: '300',
      ipv6_enabled: 'false',
      discord_webhook_url: '',
    }
    return { value: defaults[key] ?? '' }
  },

  updateSetting: async (key: string, value: string): Promise<any> => {
    await delay(400)
    showDemoToast('Settings saved successfully')
    return { key, value }
  },

  // Domains
  getDomains: async (): Promise<Domain[]> => {
    await delay(200)
    return [...domains]
  },

  createDomain: async (domain: DomainCreate): Promise<Domain> => {
    await delay(700)
    const newDomain: Domain = {
      id: nextId++,
      name: domain.name,
      zone_id: domain.zone_id,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    domains.push(newDomain)
    showDemoToast('Domain added successfully')
    return newDomain
  },

  updateDomain: async (id: number, domain: DomainUpdate): Promise<Domain> => {
    await delay(700)
    const index = domains.findIndex((d) => d.id === id)
    if (index === -1) throw new Error('Domain not found')
    domains[index] = { ...domains[index], ...domain, updated_at: new Date().toISOString() }
    showDemoToast('Domain updated successfully')
    return domains[index]
  },

  deleteDomain: async (id: number): Promise<any> => {
    await delay(500)
    const hasRecords = records.some((r) => r.zone_identifier === domains.find((d) => d.id === id)?.zone_id)
    if (hasRecords) throw new Error('Cannot delete domain: it has DNS records. Delete those records first.')
    domains = domains.filter((d) => d.id !== id)
    showDemoToast('Domain deleted successfully')
    return {}
  },
}
