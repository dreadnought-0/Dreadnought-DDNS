'use client'

import { useState, useEffect } from 'react'
import Layout from '../../components/Layout'
import { api } from '../../lib/api'
import { TrackedRecord, TrackedRecordCreate, TrackedRecordUpdate, Domain } from '../../types'
import { PlusIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline'

export default function RecordsPage() {
  const [records, setRecords] = useState<TrackedRecord[]>([])
  const [domains, setDomains] = useState<Domain[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingRecord, setEditingRecord] = useState<TrackedRecord | null>(null)
  const [formData, setFormData] = useState<TrackedRecordCreate>({
    zone_identifier: '',
    domain_id: undefined,
    domain: '',
    host: '',
    type: 'A',
    proxied: false,
    ttl: 300,
  })
  const [filters, setFilters] = useState({
    domain: '',
    fqdn: '',
    type: '',
  })
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [recordToDelete, setRecordToDelete] = useState<TrackedRecord | null>(null)
  const [deleteFromCloudflare, setDeleteFromCloudflare] = useState(false)

  useEffect(() => {
    loadRecords()
    loadDomains()
  }, [filters.domain, filters.fqdn, filters.type])

  const loadRecords = async () => {
    try {
      const data = await api.getRecords(filters)
      setRecords(data)
    } catch (error) {
      console.error('Failed to load records:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadDomains = async () => {
    try {
      const data = await api.getDomains()
      setDomains(data)
    } catch (error) {
      console.error('Failed to load domains:', error)
    }
  }

  const handleAdd = () => {
    setEditingRecord(null)
    setFormData({
      zone_identifier: '',
      domain_id: undefined,
      domain: '',
      host: '',
      type: 'A',
      proxied: false,
      ttl: 300,
    })
    setShowModal(true)
  }

  const handleDomainSelect = (domainId: string) => {
    if (!domainId) {
      setFormData({ ...formData, domain_id: undefined, domain: '', zone_identifier: '' })
      return
    }
    const selected = domains.find(d => d.id === parseInt(domainId))
    if (selected) {
      setFormData({ ...formData, domain_id: selected.id, domain: selected.name, zone_identifier: selected.zone_id })
    }
  }

  const handleEdit = (record: TrackedRecord) => {
    setEditingRecord(record)
    setFormData({
      zone_identifier: record.zone_identifier || '',
      domain: record.domain,
      host: record.host || '@',
      type: record.type,
      proxied: record.proxied,
      ttl: record.ttl,
    })
    setShowModal(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      if (editingRecord) {
        const updateData: TrackedRecordUpdate = {}
        if (formData.zone_identifier !== editingRecord.zone_identifier) updateData.zone_identifier = formData.zone_identifier
        if (formData.domain !== editingRecord.domain) updateData.domain = formData.domain
        if (formData.host !== editingRecord.host) updateData.host = formData.host
        if (formData.type !== editingRecord.type) updateData.type = formData.type
        if (formData.proxied !== editingRecord.proxied) updateData.proxied = formData.proxied
        if (formData.ttl !== editingRecord.ttl) updateData.ttl = formData.ttl
        
        await api.updateRecord(editingRecord.id, updateData)
      } else {
        await api.createRecord(formData)
      }
      
      setShowModal(false)
      await loadRecords()
    } catch (error: any) {
      alert(error.message || 'Operation failed')
    }
  }

  const handleDelete = (record: TrackedRecord) => {
    setRecordToDelete(record)
    setDeleteFromCloudflare(false)
    setShowDeleteModal(true)
  }

  const confirmDelete = async () => {
    if (!recordToDelete) return

    try {
      await api.deleteRecord(recordToDelete.id, deleteFromCloudflare)
      await loadRecords()
      setShowDeleteModal(false)
      setRecordToDelete(null)
    } catch (error: any) {
      alert(error.message || 'Delete failed')
    }
  }

  const getTTLDisplay = (record: TrackedRecord) => {
    if (record.proxied) {
      return 'Auto (300s)'
    }
    return record.ttl === 1 ? 'Auto' : `${record.ttl}s`
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto">
        <div className="sm:flex sm:items-center mb-8">
          <div className="sm:flex-auto">
            <h1 className="text-2xl font-bold text-gray-900">DNS Records</h1>
            <p className="mt-2 text-gray-700">
              Manage your tracked DNS records. Changes are immediately synced to Cloudflare.
            </p>
          </div>
          <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
            <button
              type="button"
              onClick={handleAdd}
              className="inline-flex items-center justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              <PlusIcon className="h-4 w-4 mr-2" />
              Add Record
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white shadow rounded-lg mb-6">
          <div className="px-4 py-5 sm:p-6">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
              <div>
                <label htmlFor="filter-domain" className="block text-sm font-medium text-gray-700">
                  Domain
                </label>
                <input
                  type="text"
                  id="filter-domain"
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="example.com"
                  value={filters.domain}
                  onChange={(e) => setFilters({ ...filters, domain: e.target.value })}
                />
              </div>
              <div>
                <label htmlFor="filter-fqdn" className="block text-sm font-medium text-gray-700">
                  FQDN
                </label>
                <input
                  type="text"
                  id="filter-fqdn"
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="vpn.example.com"
                  value={filters.fqdn}
                  onChange={(e) => setFilters({ ...filters, fqdn: e.target.value })}
                />
              </div>
              <div>
                <label htmlFor="filter-type" className="block text-sm font-medium text-gray-700">
                  Type
                </label>
                <select
                  id="filter-type"
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={filters.type}
                  onChange={(e) => setFilters({ ...filters, type: e.target.value })}
                >
                  <option value="">All Types</option>
                  <option value="A">A</option>
                  <option value="AAAA">AAAA</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Records Table */}
        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : records.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">No records found</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-200">
              {records.map((record) => (
                <li key={record.id}>
                  <div className="px-4 py-4 sm:px-6">
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center">
                          <p className="text-sm font-medium text-blue-600 truncate">
                            {record.fqdn}
                          </p>
                          <span className={`ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            record.type === 'A' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                          }`}>
                            {record.type}
                          </span>
                          {record.proxied && (
                            <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                              Proxied
                            </span>
                          )}
                        </div>
                        <div className="mt-2 flex flex-col">
                          <div className="flex items-center text-sm text-gray-500">
                            <span>Domain: {record.domain}</span>
                            <span className="mx-2">•</span>
                            <span>Host: {record.host || '@'}</span>
                            <span className="mx-2">•</span>
                            <span>TTL: {getTTLDisplay(record)}</span>
                          </div>
                          {record.zone_identifier && (
                            <div className="text-xs text-gray-400 font-mono mt-1">
                              Zone: {record.zone_identifier}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handleEdit(record)}
                          className="text-gray-400 hover:text-blue-500"
                        >
                          <PencilIcon className="h-5 w-5" />
                        </button>
                        <button
                          onClick={() => handleDelete(record)}
                          className="text-gray-400 hover:text-red-500"
                        >
                          <TrashIcon className="h-5 w-5" />
                        </button>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Modal */}
        {showModal && (
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
            <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
              <div className="mt-3">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  {editingRecord ? 'Edit Record' : 'Add Record'}
                </h3>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label htmlFor="domain_select" className="block text-sm font-medium text-gray-700">
                      Select Domain
                    </label>
                    <select
                      id="domain_select"
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      value={formData.domain_id || ''}
                      onChange={(e) => handleDomainSelect(e.target.value)}
                    >
                      <option value="">-- Select a domain --</option>
                      {domains.map((domain) => (
                        <option key={domain.id} value={domain.id}>
                          {domain.name} ({domain.zone_id.substring(0, 8)}...)
                        </option>
                      ))}
                    </select>
                    <p className="mt-1 text-xs text-gray-500">
                      Select from registered domains or{' '}
                      <a href="/domains" className="text-blue-600 hover:text-blue-500">add a new domain</a>
                    </p>
                  </div>

                  <div>
                    <label htmlFor="domain" className="block text-sm font-medium text-gray-700">
                      Domain (auto-filled)
                    </label>
                    <input
                      type="text"
                      id="domain"
                      readOnly
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm bg-gray-50 sm:text-sm"
                      value={formData.domain}
                    />
                  </div>
                  
                  <div>
                    <label htmlFor="host" className="block text-sm font-medium text-gray-700">
                      Host
                    </label>
                    <input
                      type="text"
                      id="host"
                      required
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      placeholder="zabbix (or @ for root domain)"
                      value={formData.host}
                      onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Use @ for root domain or subdomain name (e.g., zabbix, www, mail)
                    </p>
                  </div>
                  
                  <div>
                    <label htmlFor="type" className="block text-sm font-medium text-gray-700">
                      Type
                    </label>
                    <select
                      id="type"
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      value={formData.type}
                      onChange={(e) => setFormData({ ...formData, type: e.target.value as 'A' | 'AAAA' })}
                    >
                      <option value="A">A (IPv4)</option>
                      <option value="AAAA">AAAA (IPv6)</option>
                    </select>
                  </div>
                  
                  <div className="flex items-center">
                    <input
                      id="proxied"
                      type="checkbox"
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      checked={formData.proxied}
                      onChange={(e) => setFormData({ ...formData, proxied: e.target.checked })}
                    />
                    <label htmlFor="proxied" className="ml-2 block text-sm text-gray-900">
                      Proxied (forces TTL to Auto)
                    </label>
                  </div>
                  
                  <div>
                    <label htmlFor="ttl" className="block text-sm font-medium text-gray-700">
                      TTL (seconds)
                    </label>
                    <input
                      type="number"
                      id="ttl"
                      min="1"
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      value={formData.ttl}
                      onChange={(e) => setFormData({ ...formData, ttl: parseInt(e.target.value) })}
                      disabled={formData.proxied}
                    />
                    {formData.proxied && (
                      <p className="mt-1 text-sm text-gray-500">TTL is automatically set to 300s for proxied records</p>
                    )}
                  </div>
                  
                  <div className="flex justify-end space-x-3">
                    <button
                      type="button"
                      onClick={() => setShowModal(false)}
                      className="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      {editingRecord ? 'Update' : 'Create'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {showDeleteModal && recordToDelete && (
          <div className="fixed z-10 inset-0 overflow-y-auto">
            <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:p-0">
              <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setShowDeleteModal(false)}></div>

              <div className="inline-block align-middle bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:max-w-lg sm:w-full sm:p-6">
                <div>
                  <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                    <TrashIcon className="h-6 w-6 text-red-600" />
                  </div>
                  <div className="mt-3 text-center sm:mt-5">
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      Delete DNS Record
                    </h3>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500">
                        Are you sure you want to delete the {recordToDelete.type} record for {recordToDelete.fqdn}?
                      </p>
                    </div>
                    <div className="mt-4">
                      <label className="flex items-center justify-center">
                        <input
                          type="checkbox"
                          checked={deleteFromCloudflare}
                          onChange={(e) => setDeleteFromCloudflare(e.target.checked)}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <span className="ml-2 text-sm text-gray-700">
                          Also delete from Cloudflare
                        </span>
                      </label>
                    </div>
                  </div>
                </div>
                <div className="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
                  <button
                    type="button"
                    onClick={confirmDelete}
                    className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 sm:col-start-2 sm:text-sm"
                  >
                    Yes
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowDeleteModal(false)}
                    className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:col-start-1 sm:text-sm"
                  >
                    No
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}