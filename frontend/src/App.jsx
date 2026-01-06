import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { TenantProvider } from './contexts/TenantContext';
import SignupPage from './pages/SignupPage';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import DashboardPage from './pages/DashboardPage';
import AlbumPage from './pages/AlbumPage';
import UploadPage from './pages/UploadPage';
import ProtectedRoute from './components/ProtectedRoute';
import AdminRoute from './components/AdminRoute';

function App() {
  return (
    <TenantProvider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/login" element={<LoginPage />} />
            
            {/* Member routes */}
            <Route 
              path="/home" 
              element={
                <ProtectedRoute allowedRoles={['member', 'admin']}>
                  <HomePage />
                </ProtectedRoute>
              } 
            />
            
            {/* Admin routes */}
            <Route 
              path="/admin" 
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <DashboardPage />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/upload" 
              element={
                <AdminRoute>
                  <UploadPage />
                </AdminRoute>
              } 
            />
            
            {/* Shared routes */}
            <Route 
              path="/album/:id" 
              element={
                <ProtectedRoute allowedRoles={['member', 'admin']}>
                  <AlbumPage />
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
