import api from './client'

export const listRecords = (project_id?: number) =>
  api.get('/records', { params: project_id ? { project_id } : {} })

export const getRecord = (id: number) => api.get(`/records/${id}`)
export const createRecord = (data: Record<string, unknown>) => api.post('/records', data)
export const updateRecordData = (id: number, field_data: Record<string, unknown>, change_reason?: string) =>
  api.put(`/records/${id}/data`, { field_data, change_reason })
export const submitForReview = (id: number, password: string, meaning?: string) =>
  api.post(`/records/${id}/submit-review`, { password, meaning })
export const signReview = (id: number, password: string, meaning?: string) =>
  api.post(`/records/${id}/sign-review`, { password, meaning })
export const getSignatures = (id: number) => api.get(`/records/${id}/signatures`)
export const approveRecord = (id: number, password: string, meaning?: string) =>
  api.post(`/records/${id}/approve`, { password, meaning })
export const rejectRecord = (id: number) => api.post(`/records/${id}/reject`)
export const renderPdf = (id: number) => api.post(`/records/${id}/render-pdf`)
export const getRenderStatus = (recordId: number, jobId: number) =>
  api.get(`/records/${recordId}/render-status/${jobId}`)
export const getAuditTrail = (id: number) => api.get(`/records/${id}/audit-trail`)
export const listDeviations = (id: number) => api.get(`/records/${id}/deviations`)
export const createDeviation = (id: number, data: Record<string, unknown>) =>
  api.post(`/records/${id}/deviations`, data)
export const closeDeviation = (recordId: number, devId: number) =>
  api.post(`/records/${recordId}/deviations/${devId}/close`)
