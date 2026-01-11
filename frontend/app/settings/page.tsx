'use client'

import { useState, useEffect } from 'react'
import Layout from '../../components/Layout'
import { api } from '../../lib/api'
import { AuditEntry } from '../../types'
import { format } from 'date-fns'

export default function SettingsPage() {
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [settings, setSettings] = useState({
    poll_interval_seconds: '300',
    ipv6_enabled: 'true',
    discord_webhook_url: '',
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [audit, pollInterval, ipv6Enabled, discordWebhook] = await Promise.allSettled([
        api.getAuditLog(20, 0),
        api.getSetting('poll_interval_seconds').catch(() => ({ value: '300' })),
        api.getSetting('ipv6_enabled').catch(() => ({ value: 'true' })),
        api.getSetting('discord_webhook_url').catch(() => ({ value: '' })),
      ])

      if (audit.status === 'fulfilled') {
        setAuditEntries(audit.value)
      }

      setSettings({
        poll_interval_seconds: pollInterval.status === 'fulfilled' ? pollInterval.value.value : '300',
        ipv6_enabled: ipv6Enabled.status === 'fulfilled' ? ipv6Enabled.value.value : 'true',
        discord_webhook_url: discordWebhook.status === 'fulfilled' ? discordWebhook.value.value : '',
      })
    } catch (error) {
      console.error('Failed to load settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)

    try {
      await Promise.all([
        api.updateSetting('poll_interval_seconds', settings.poll_interval_seconds),
        api.updateSetting('ipv6_enabled', settings.ipv6_enabled),
        api.updateSetting('discord_webhook_url', settings.discord_webhook_url),
      ])
      alert('Settings saved successfully')
    } catch (error: any) {
      console.error('Settings save error:', error)
      const errorMessage = typeof error === 'object' && error.message 
        ? error.message 
        : typeof error === 'string' 
        ? error 
        : 'Failed to save settings'
      alert(errorMessage)
    } finally {
      setSaving(false)
    }
  }

  const formatAuditTimestamp = (timestamp: string) => {
    try {
      return format(new Date(timestamp), 'yyyy-MM-dd HH:mm:ss')
    } catch (error) {
      return timestamp
    }
  }

  const formatAuditDetails = (details: any) => {
    if (!details) return 'No details'
    
    if (typeof details === 'string') return details
    
    // Format common detail patterns
    if (details.fqdn && details.type) {
      return `${details.fqdn} (${details.type})`
    }
    
    if (details.records_processed !== undefined) {
      return `Processed: ${details.records_processed}, Updated: ${details.records_updated || 0}, Failed: ${details.records_failed || 0}`
    }
    
    return JSON.stringify(details, null, 2)
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="mt-2 text-gray-700">
            Configure DDNS manager settings and view audit logs
          </p>
        </div>

        <div className="space-y-6">
          {/* Settings Form */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Configuration
              </h3>
              
              <form onSubmit={handleSaveSettings} className="space-y-4">
                <div>
                  <label htmlFor="poll-interval" className="block text-sm font-medium text-gray-700">
                    Poll Interval (seconds)
                  </label>
                  <input
                    type="number"
                    id="poll-interval"
                    min="60"
                    max="7200"
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    value={settings.poll_interval_seconds}
                    onChange={(e) => setSettings({ ...settings, poll_interval_seconds: e.target.value })}
                  />
                  <p className="mt-1 text-sm text-gray-500">
                    How often to check for IP changes (60-7200 seconds)
                  </p>
                </div>

                <div className="flex items-center">
                  <input
                    id="ipv6-enabled"
                    type="checkbox"
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    checked={settings.ipv6_enabled === 'true'}
                    onChange={(e) => setSettings({ ...settings, ipv6_enabled: e.target.checked ? 'true' : 'false' })}
                  />
                  <label htmlFor="ipv6-enabled" className="ml-2 block text-sm text-gray-900">
                    Enable IPv6 support
                  </label>
                </div>

                <div>
                  <label htmlFor="discord-webhook" className="block text-sm font-medium text-gray-700">
                    Discord Webhook URL (optional)
                  </label>
                  <input
                    type="url"
                    id="discord-webhook"
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="https://discord.com/api/webhooks/..."
                    value={settings.discord_webhook_url}
                    onChange={(e) => setSettings({ ...settings, discord_webhook_url: e.target.value })}
                  />
                  <p className="mt-1 text-sm text-gray-500">
                    Receive notifications when IP changes occur
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save Settings'}
                </button>
              </form>
            </div>
          </div>

          {/* Audit Log */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Recent Activity
              </h3>
              
              {loading ? (
                <div className="flex justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : auditEntries.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No activity recorded</p>
              ) : (
                <div className="flow-root">
                  <ul className="-mb-8">
                    {auditEntries.map((entry, index) => (
                      <li key={entry.id}>
                        <div className="relative pb-8">
                          {index !== auditEntries.length - 1 && (
                            <span className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" />
                          )}
                          <div className="relative flex space-x-3">
                            <div>
                              <span className={`h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white ${
                                entry.action.includes('sync') 
                                  ? 'bg-blue-500' 
                                  : entry.action.includes('create') 
                                  ? 'bg-green-500'
                                  : entry.action.includes('update')
                                  ? 'bg-yellow-500'
                                  : entry.action.includes('delete')
                                  ? 'bg-red-500'
                                  : 'bg-gray-500'
                              }`}>
                                <span className="text-white text-xs font-medium">
                                  {entry.action.charAt(0).toUpperCase()}
                                </span>
                              </span>
                            </div>
                            <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                              <div>
                                <p className="text-sm text-gray-900">
                                  <span className="font-medium capitalize">
                                    {entry.action.replace('_', ' ')}
                                  </span>
                                </p>
                                {entry.details && (
                                  <div className="mt-1 text-sm text-gray-600">
                                    <pre className="whitespace-pre-wrap font-mono text-xs bg-gray-50 p-2 rounded">
                                      {formatAuditDetails(entry.details)}
                                    </pre>
                                  </div>
                                )}
                              </div>
                              <div className="text-right text-sm whitespace-nowrap text-gray-500">
                                {formatAuditTimestamp(entry.ts)}
                              </div>
                            </div>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* System Information */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                System Information
              </h3>
              
              <dl className="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Version</dt>
                  <dd className="mt-1 text-sm text-gray-900">1.0.0</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">API Endpoint</dt>
                  <dd className="mt-1 text-sm text-gray-900 font-mono">
                    {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8081'}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Documentation</dt>
                  <dd className="mt-1 text-sm">
                    <a 
                      href="https://github.com/yourusername/ddns-manager" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-500"
                    >
                      GitHub Repository
                    </a>
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Support</dt>
                  <dd className="mt-1 text-sm">
                    <a 
                      href="https://github.com/yourusername/ddns-manager/issues" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-500"
                    >
                      Report Issues
                    </a>
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}