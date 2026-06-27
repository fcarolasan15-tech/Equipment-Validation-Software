import api from './client'

export const login = (email: string, password: string) =>
  api.post('/auth/token', new URLSearchParams({ username: email, password }),
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })

export const getMe = () => api.get('/auth/me')

export const changePassword = (current_password: string, new_password: string) =>
  api.post('/auth/change-password', { current_password, new_password })
