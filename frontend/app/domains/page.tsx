'use client'

import { useState, useEffect } from 'react'
import Layout from '../../components/Layout'
import { api } from '../../lib/api'
import { Domain, DomainCreate } from '../../types'
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline'

export default function DomainsPage() {
  const [domains, setDomains] = useState<Domain[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState<DomainCreate>({
    name: '',
    zone_id: '',
  })

  useEffect(() => {
    loadDomains()
  }, [])

  const loadDomains = async () => {
    try {
      const data = await api.getDomains()
      setDomains(data)
    } catch (error) {
      console.error('Failed to load domains:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setFormData({
      name: '',
      zone_id: '',
    })
    setShowModal(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      await api.createDomain(formData)
      setShowModal(false)
      await loadDomains()
    } catch (error: any) {
      alert(error.message || 'Operation failed')
    }
  }

  const handleDelete = async (domain: Domain) => {
    if (!confirm(`Are you sure you want to delete domain ${domain.name}?\n\nNote: You cannot delete domains that have DNS records. Delete those records first.`)) {
      return
    }

    try {
      await api.deleteDomain(domain.id)
      await loadDomains()
    } catch (error: any) {
      alert(error.message || 'Delete failed: ' + (error.response?.data?.detail || error.message))
    }
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto">
        <div className="sm:flex sm:items-center mb-8">
          <div className="sm:flex-auto">
            <h1 className="text-2xl font-bold text-gray-900">Domains</h1>
            <p className="mt-2 text-gray-700">
              Register your Cloudflare domains to use them when adding DNS records.
            </p>
          </div>
          <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
            <button
              type="button"
              onClick={handleAdd}
              className="inline-flex items-center justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              <PlusIcon className="h-4 w-4 mr-2" />
              Add Domain
            </button>
          </div>
        </div>

        {/* Domains List */}
        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          {loading ? (
            <div className="p-8 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : domains.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No domains registered yet. Add your first domain to get started.
            </div>
          ) : (
            <ul className="divide-y divide-gray-200">
              {domains.map((domain) => (
                <li key={domain.id}>
                  <div className="px-4 py-4 sm:px-6 hover:bg-gray-50 flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-blue-600 truncate">
                          {domain.name}
                        </p>
                      </div>
                      <div className="mt-2 sm:flex sm:justify-between">
                        <div className="sm:flex">
                          <p className="text-sm text-gray-500">
                            Zone ID: <span className="font-mono text-gray-700">{domain.zone_id}</span>
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="ml-4 flex-shrink-0">
                      <button
                        onClick={() => handleDelete(domain)}
                        className="inline-flex items-center p-2 border border-transparent rounded-md text-red-600 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                        title="Delete domain"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Add/Edit Modal */}
        {showModal && (
          <div className="fixed z-10 inset-0 overflow-y-auto">
            <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:p-0">
              <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setShowModal(false)}></div>

              <div className="inline-block align-middle bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:max-w-lg sm:w-full sm:p-6">
                <form onSubmit={handleSubmit}>
                  <div>
                    <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                      Add Domain
                    </h3>

                    <div className="space-y-4">
                      <div>
                        <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                          Domain Name
                        </label>
                        <input
                          type="text"
                          id="name"
                          required
                          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                          placeholder="example.com"
                          value={formData.name}
                          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        />
                        <p className="mt-1 text-xs text-gray-500">The domain name (e.g., dreadnought.work)</p>
                      </div>

                      <div>
                        <label htmlFor="zone_id" className="block text-sm font-medium text-gray-700">
                          Cloudflare Zone ID
                        </label>
                        <input
                          type="text"
                          id="zone_id"
                          required
                          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm font-mono"
                          placeholder="3BJnnfSHADoMqYgvaRx8V7D8p5fcRGyQ"
                          maxLength={32}
                          value={formData.zone_id}
                          onChange={(e) => setFormData({ ...formData, zone_id: e.target.value.toLowerCase() })}
                        />
                        <p className="mt-1 text-xs text-gray-500">
                          32-character hexadecimal Zone ID from Cloudflare
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
                    <button
                      type="submit"
                      className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:col-start-2 sm:text-sm"
                    >
                      Add Domain
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowModal(false)}
                      className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:col-start-1 sm:text-sm"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
