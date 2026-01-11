export interface User {
  id: number
  email: string
  created_at: string
}

export interface TrackedRecord {
  id: number
  zone_identifier?: string
  domain: string
  host?: string
  fqdn: string
  type: 'A' | 'AAAA'
  proxied: boolean
  ttl: number
  zone_id_cached?: string
  created_at: string
  updated_at: string
}

export interface TrackedRecordCreate {
  zone_identifier?: string
  domain_id?: number
  domain: string
  host: string
  type: 'A' | 'AAAA'
  proxied: boolean
  ttl: number
}

export interface TrackedRecordUpdate {
  zone_identifier?: string
  domain?: string
  host?: string
  type?: 'A' | 'AAAA'
  proxied?: boolean
  ttl?: number
}

export interface SyncStatus {
  last_seen_ipv4?: string
  last_seen_ipv6?: string
  last_sync_at?: string
  last_sync_result?: string
}

export interface AuditEntry {
  id: number
  ts: string
  action: string
  details?: any
}

export interface ImportRecord {
  domain: string
  host: string
  ip_version: 4 | 6
  ttl: number
  proxied: boolean
}

export interface ImportRequest {
  records: ImportRecord[]
  dry_run: boolean
  sync_after_import: boolean
}

export interface SyncResult {
  start_time: string
  status: 'running' | 'completed' | 'error'
  ipv4?: string
  ipv6?: string
  records_processed: number
  records_updated: number
  records_failed: number
  details: any[]
  end_time?: string
  duration_seconds?: number
  ip_changed?: boolean
  error?: string
}

export interface Domain {
  id: number
  name: string
  zone_id: string
  created_at: string
  updated_at: string
}

export interface DomainCreate {
  name: string
  zone_id: string
}

export interface DomainUpdate {
  name?: string
  zone_id?: string
}