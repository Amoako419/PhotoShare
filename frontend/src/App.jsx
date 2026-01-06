import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { TenantProvider } from './contexts/TenantContext';
import AppShell from './components/AppShell';
import LandingPage from './pages/LandingPage';
import SignupPage from './pages/SignupPage';
import AdminSignupPage from './pages/AdminSignupPage';
import MemberSignupPage from './pages/MemberSignupPage';
import LoginPage from './pages/LoginPage';
import SetupWizardPage from './pages/SetupWizardPage';
import HomePage from './pages/HomePage';
import DashboardPage from './pages/DashboardPage';
import AlbumPage from './pages/AlbumPage';
import UploadPage from './pages/UploadPage';
import SettingsPage from './pages/SettingsPage';
import PlatformDashboard from './pages/PlatformDashboard';
import ChurchStatsPage from './pages/ChurchStatsPage';
import ProtectedRoute from './components/ProtectedRoute';
import AdminRoute from './components/AdminRoute';
import SuperAdminRoute from './components/SuperAdminRoute';

function App() {
  return (
    <TenantProvider>
      <Router>
        <div className="App">
          <Routes>
            {/* Public routes - no AppShell */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/signup" element={<MemberSignupPage />} />
            <Route path="/admin-signup" element={<AdminSignupPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/setup-wizard" element={<SetupWizardPage />} />
            
            {/* Superadmin routes - with AppShell */}
            <Route 
              path="/platform" 
              element={<Navigate to="/platform/dashboard" replace />}
            />
            <Route 
              path="/platform/dashboard" 
              element={
                <SuperAdminRoute>
                  <AppShell>
                    <PlatformDashboard />
                  </AppShell>
                </SuperAdminRoute>
              } 
            />
            <Route 
              path="/platform/churches/:churchId/stats" 
              element={
                <SuperAdminRoute>
                  <AppShell>
                    <ChurchStatsPage />
                  </AppShell>
                </SuperAdminRoute>
              } 
            />
            
            {/* Member routes - with AppShell */}
            <Route 
              path="/home" 
              element={
                <ProtectedRoute allowedRoles={['member', 'admin']}>
                  <AppShell>
                    <HomePage />
                  </AppShell>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/albums" 
              element={
                <ProtectedRoute allowedRoles={['member', 'admin']}>
                  <AppShell>
                    <HomePage />
                  </AppShell>
                </ProtectedRoute>
              } 
            />
            
            {/* Admin routes - with AppShell */}
            <Route 
              path="/admin" 
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <AppShell>
                    <DashboardPage />
                  </AppShell>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/upload" 
              element={
                <AdminRoute>
                  <AppShell>
                    <UploadPage />
                  </AppShell>
                </AdminRoute>
              } 
            />
            <Route 
              path="/settings" 
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <AppShell>
                    <SettingsPage />
                  </AppShell>
                </ProtectedRoute>
              } 
            />
            
            {/* Shared routes - with AppShell */}
            <Route 
              path="/album/:id" 
              element={
                <ProtectedRoute allowedRoles={['member', 'admin']}>
                  <AppShell>
                    <AlbumPage />
                  </AppShell>
                </ProtectedRoute>
              } 
            />
            
            {/* Legacy dashboard route - redirect based on role */}
            <Route path="/dashboard" element={<Navigate to="/admin" replace />} />
          </Routes>
        </div>
      </Router>
    </TenantProvider>
  );
}

export default App;
