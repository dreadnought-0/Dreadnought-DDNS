'use client'

import { useState } from 'react'
import Layout from '../../components/Layout'
import { api } from '../../lib/api'
import { ImportRecord, ImportRequest } from '../../types'

export default function ImportPage() {
  const [jsonInput, setJsonInput] = useState('')
  const [dryRun, setDryRun] = useState(true)
  const [syncAfterImport, setSyncAfterImport] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setResult(null)

    try {
      const records: ImportRecord[] = JSON.parse(jsonInput)
      
      const importRequest: ImportRequest = {
        records,
        dry_run: dryRun,
        sync_after_import: syncAfterImport && !dryRun,
      }

      const importResult = await api.importRecords(importRequest)
      setResult(importResult)
    } catch (error: any) {
      setResult({
        dry_run: dryRun,
        records_processed: 0,
        records_created: 0,
        records_failed: 1,
        details: [{
          status: 'error',
          message: error.message || 'Import failed'
        }]
      })
    } finally {
      setLoading(false)
    }
  }

  const exampleJson = JSON.stringify([
    {
      "domain": "example.com",
      "host": "vpn",
      "ip_version": 4,
      "ttl": 300,
      "proxied": false
    },
    {
      "domain": "example.com",
      "host": "@",
      "ip_version": 4,
      "ttl": 300,
      "proxied": true
    },
    {
      "domain": "example.com",
      "host": "www",
      "ip_version": 6,
      "ttl": 300,
      "proxied": false
    }
  ], null, 2)

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Import Records</h1>
          <p className="mt-2 text-gray-700">
            Import DNS records from a legacy JSON format. Use dry run mode to preview changes before committing.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Import Form */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Import Configuration
              </h3>
              
              <form onSubmit={handleImport} className="space-y-4">
                <div>
                  <label htmlFor="json-input" className="block text-sm font-medium text-gray-700">
                    JSON Records
                  </label>
                  <textarea
                    id="json-input"
                    rows={12}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm font-mono"
                    placeholder="Paste your JSON records here..."
                    value={jsonInput}
                    onChange={(e) => setJsonInput(e.target.value)}
                    required
                  />
                </div>

                <div className="flex items-center">
                  <input
                    id="dry-run"
                    type="checkbox"
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    checked={dryRun}
                    onChange={(e) => setDryRun(e.target.checked)}
                  />
                  <label htmlFor="dry-run" className="ml-2 block text-sm text-gray-900">
                    Dry run (preview only, don't create records)
                  </label>
                </div>

                <div className="flex items-center">
                  <input
                    id="sync-after-import"
                    type="checkbox"
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    checked={syncAfterImport}
                    onChange={(e) => setSyncAfterImport(e.target.checked)}
                    disabled={dryRun}
                  />
                  <label htmlFor="sync-after-import" className="ml-2 block text-sm text-gray-900">
                    Sync to Cloudflare after import
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      {dryRun ? 'Previewing...' : 'Importing...'}
                    </>
                  ) : (
                    dryRun ? 'Preview Import' : 'Import Records'
                  )}
                </button>
              </form>
            </div>
          </div>

          {/* Example JSON */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Example JSON Format
              </h3>
              
              <div className="bg-gray-50 rounded-md p-4 mb-4">
                <pre className="text-sm text-gray-800 whitespace-pre-wrap">
                  {exampleJson}
                </pre>
              </div>

              <div className="text-sm text-gray-600">
                <h4 className="font-medium mb-2">Field Descriptions:</h4>
                <ul className="list-disc list-inside space-y-1">
                  <li><strong>domain:</strong> The zone name (e.g., &ldquo;example.com&rdquo;)</li>
                  <li><strong>host:</strong> The subdomain or &ldquo;@&rdquo; for root domain</li>
                  <li><strong>ip_version:</strong> 4 for IPv4 (A record) or 6 for IPv6 (AAAA record)</li>
                  <li><strong>ttl:</strong> Time to live in seconds (use 1 for &ldquo;Auto&rdquo;)</li>
                  <li><strong>proxied:</strong> true to enable Cloudflare proxy (forces TTL to Auto)</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Import Results */}
        {result && (
          <div className="mt-8 bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Import Results
                {result.dry_run && (
                  <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                    Preview Mode
                  </span>
                )}
              </h3>
              
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">{result.records_processed}</div>
                  <div className="text-sm text-gray-500">Processed</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {result.records_created || result.details?.filter((d: any) => d.status === 'created' || d.status === 'would_create').length || 0}
                  </div>
                  <div className="text-sm text-gray-500">
                    {result.dry_run ? 'Would Create' : 'Created'}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">{result.records_failed}</div>
                  <div className="text-sm text-gray-500">Failed</div>
                </div>
              </div>

              {result.details && result.details.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-3">Details</h4>
                  <div className="bg-gray-50 rounded-md p-4 max-h-96 overflow-y-auto">
                    {result.details.map((detail: any, index: number) => (
                      <div key={index} className="mb-3 last:mb-0 pb-3 last:pb-0 border-b last:border-b-0 border-gray-200">
                        <div className="flex items-center mb-1">
                          <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                            detail.status === 'created' || detail.status === 'would_create' || detail.status === 'success'
                              ? 'bg-green-500' 
                              : detail.status === 'skipped'
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                          }`}></span>
                          <span className="text-sm font-medium text-gray-900">
                            {detail.host}.{detail.domain}
                          </span>
                          <span className="ml-2 text-xs text-gray-500">
                            IPv{detail.ip_version}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 ml-4">{detail.message}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {result.dry_run && result.records_processed > 0 && (
                <div className="mt-6 bg-blue-50 border border-blue-200 rounded-md p-4">
                  <p className="text-sm text-blue-700">
                    This was a preview. Uncheck &ldquo;Dry run&rdquo; and click &ldquo;Import Records&rdquo; to create the records.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}