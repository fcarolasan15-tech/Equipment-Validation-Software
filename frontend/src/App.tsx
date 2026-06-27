import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './pages/Login'
import ChangePassword from './pages/ChangePassword'
import Dashboard from './pages/Dashboard'
import AssetList from './pages/AssetList'
import AssetDetail from './pages/AssetDetail'
import AssetNew from './pages/AssetNew'
import ProjectList from './pages/ProjectList'
import ProjectNew from './pages/ProjectNew'
import ProjectWorkspace from './pages/ProjectWorkspace'
import RecordEditor from './pages/RecordEditor'
import TemplateLibrary from './pages/TemplateLibrary'
import ApprovalQueue from './pages/ApprovalQueue'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('evs_token')
  if (!token) return <Navigate to="/login" replace />
  return <Layout>{children}</Layout>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/change-password" element={<ChangePassword />} />

        <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
        <Route path="/assets" element={<PrivateRoute><AssetList /></PrivateRoute>} />
        <Route path="/assets/new" element={<PrivateRoute><AssetNew /></PrivateRoute>} />
        <Route path="/assets/:id" element={<PrivateRoute><AssetDetail /></PrivateRoute>} />
        <Route path="/projects" element={<PrivateRoute><ProjectList /></PrivateRoute>} />
        <Route path="/projects/new" element={<PrivateRoute><ProjectNew /></PrivateRoute>} />
        <Route path="/projects/:id" element={<PrivateRoute><ProjectWorkspace /></PrivateRoute>} />
        <Route path="/projects/:id/records/:stage" element={<PrivateRoute><RecordEditor /></PrivateRoute>} />
        <Route path="/templates" element={<PrivateRoute><TemplateLibrary /></PrivateRoute>} />
        <Route path="/approvals" element={<PrivateRoute><ApprovalQueue /></PrivateRoute>} />

        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
