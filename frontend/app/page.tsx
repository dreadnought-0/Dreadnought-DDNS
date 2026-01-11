'use client'

import { useState, useEffect } from 'react'
import Layout from '../components/Layout'
import { api } from '../lib/api'
import { SyncStatus, SyncResult, TrackedRecord } from '../types'
import { formatDistanceToNow } from 'date-fns'
import { zonedTimeToUtc, utcToZonedTime, format } from 'date-fns-tz'

export default function DashboardPage() {
  const [status, setStatus] = useState<SyncStatus | null>(null)
  const [records, setRecords] = useState<TrackedRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [statusData, recordsData] = await Promise.all([
        api.getStatus(),
        api.getRecords()
      ])
      setStatus(statusData)
      setRecords(recordsData)
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleManualSync = async () => {
    setSyncing(true)
    setSyncResult(null)
    try {
      const result = await api.manualSync()
      setSyncResult(result)
      // Reload data after sync
      await loadData()
    } catch (error: any) {
      setSyncResult({
        start_time: new Date().toISOString(),
        status: 'error',
        records_processed: 0,
        records_updated: 0,
        records_failed: 0,
        details: [],
        error: error.message || 'Sync failed'
      })
    } finally {
      setSyncing(false)
    }
  }

  const formatLastSync = (timestamp: string | undefined) => {
    if (!timestamp) return 'Never'
    try {
      // Parse the timestamp as UTC and convert to local timezone
      const date = new Date(timestamp)
      return formatDistanceToNow(date, { addSuffix: true })
    } catch (error) {
      return 'Invalid date'
    }
  }

  const formatRecordTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return formatDistanceToNow(date, { addSuffix: true })
    } catch (error) {
      return 'Never'
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="mt-1 text-gray-600 dark:text-gray-400">Monitor your DDNS status and current IP addresses</p>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
          {/* IPv4 Status */}
          <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-blue-600 font-semibold text-sm">IPv4</span>
                  </div>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">Current IPv4</dt>
                    <dd className="text-lg font-medium text-gray-900 dark:text-white">
                      {status?.last_seen_ipv4 || 'Unknown'}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          {/* IPv6 Status */}
          <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                    <span className="text-green-600 font-semibold text-sm">IPv6</span>
                  </div>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">Current IPv6</dt>
                    <dd className="text-lg font-medium text-gray-900 dark:text-white">
                      {status?.last_seen_ipv6 || 'Disabled/Unknown'}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          {/* Last Sync */}
          <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                    <span className="text-purple-600 font-semibold text-sm">📅</span>
                  </div>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">Last Sync</dt>
                    <dd className="text-lg font-medium text-gray-900 dark:text-white">
                      {formatLastSync(status?.last_sync_at)}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          {/* Sync Action */}
          <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <button
                onClick={handleManualSync}
                disabled={syncing}
                className="w-full h-full flex items-center justify-center bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-4 px-4 rounded-md transition-colors"
              >
                {syncing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Syncing...
                  </>
                ) : (
                  'Sync Now'
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Last Sync Result */}
        {status?.last_sync_result && (
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">Last Sync Result</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">{status.last_sync_result}</p>
            </div>
          </div>
        )}

        {/* Current Sync Result */}
        {syncResult && (
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
                Sync Result
                <span className={`ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  syncResult.status === 'completed' 
                    ? 'bg-green-100 text-green-800'
                    : syncResult.status === 'error'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {syncResult.status}
                </span>
              </h3>
              
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">{syncResult.records_processed}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">Processed</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{syncResult.records_updated}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">Updated</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">{syncResult.records_failed}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">Failed</div>
                </div>
              </div>

              {syncResult.error && (
                <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
                  <p className="text-sm text-red-700">{syncResult.error}</p>
                </div>
              )}

              {syncResult.details && syncResult.details.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Details</h4>
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-md p-3 max-h-60 overflow-y-auto">
                    {syncResult.details.map((detail, index) => (
                      <div key={index} className="text-xs mb-2 last:mb-0">
                        <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                          detail.status === 'success' ? 'bg-green-500' : 'bg-red-500'
                        }`}></span>
                        <span className="font-mono text-gray-900 dark:text-white">{detail.fqdn}</span>
                        <span className="text-gray-500 dark:text-gray-400 ml-2">({detail.type})</span>
                        <span className="text-gray-500 dark:text-gray-400 ml-2">- {detail.message}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tracked Records */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
              Tracked Records ({records.length})
            </h3>
            
            {records.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-500 dark:text-gray-400">No records are currently being tracked</p>
                <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">
                  Add records in the Records section to start monitoring your domains
                </p>
              </div>
            ) : (
              <div className="overflow-hidden">
                <div className="flow-root">
                  <div className="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
                    <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
                      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                        <thead>
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              Domain
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              Type
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              Status
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              Last Updated
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                          {records.map((record) => (
                            <tr key={record.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div>
                                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                                    {record.fqdn}
                                  </div>
                                  <div className="text-sm text-gray-500 dark:text-gray-400">
                                    {record.domain}
                                  </div>
                                </div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                  record.type === 'A' 
                                    ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' 
                                    : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                }`}>
                                  {record.type}
                                </span>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div className="flex items-center">
                                  <div className={`flex-shrink-0 w-2.5 h-2.5 rounded-full mr-2 ${
                                    record.zone_id_cached 
                                      ? 'bg-green-400' 
                                      : 'bg-yellow-400'
                                  }`}></div>
                                  <span className="text-sm text-gray-900 dark:text-white">
                                    {record.zone_id_cached ? 'Synced' : 'Pending'}
                                  </span>
                                </div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                                {formatRecordTimestamp(record.updated_at)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  )
}