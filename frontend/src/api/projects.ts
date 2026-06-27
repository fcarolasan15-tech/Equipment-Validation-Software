import api from './client'

export const listProjects = () => api.get('/projects')
export const getProject = (id: number) => api.get(`/projects/${id}`)
export const createProject = (data: Record<string, unknown>) => api.post('/projects', data)
export const advanceStage = (id: number, target_stage: string) =>
  api.post(`/projects/${id}/advance-stage`, { target_stage })
export const getStageGates = (id: number) => api.get(`/projects/${id}/stage-gates`)
