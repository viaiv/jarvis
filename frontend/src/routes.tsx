import { Route, Routes } from 'react-router-dom'
import { AdminRoute } from './auth/AdminRoute'
import { ProtectedRoute } from './auth/ProtectedRoute'
import App from './App'
import AdminLayout from './layouts/AdminLayout'
import LoginPage from './pages/LoginPage'
import UsersPage from './pages/admin/UsersPage'
import LogsPage from './pages/admin/LogsPage'
import ConfigPage from './pages/admin/ConfigPage'

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <App />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <AdminRoute>
            <AdminLayout />
          </AdminRoute>
        }
      >
        <Route index element={<UsersPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="logs" element={<LogsPage />} />
        <Route path="config" element={<ConfigPage />} />
      </Route>
    </Routes>
  )
}
