import api from './client'

export const listAssets = (site_id?: number) =>
  api.get('/assets', { params: site_id ? { site_id } : {} })

export const getAsset = (id: number) => api.get(`/assets/${id}`)

export const createAsset = (data: Record<string, unknown>) => api.post('/assets', data)

export const updateRisk = (id: number, data: Record<string, unknown>) =>
  api.put(`/assets/${id}/risk-assessment`, data)

export const getRecommendedScope = (id: number) =>
  api.get(`/assets/${id}/recommended-scope`)
