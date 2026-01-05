import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { TenantProvider } from './contexts/TenantContext';
import SignupPage from './pages/SignupPage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import AlbumPage from './pages/AlbumPage';
import UploadPage from './pages/UploadPage';
import AdminRoute from './components/AdminRoute';

function App() {
  return (
    <TenantProvider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/album/:id" element={<AlbumPage />} />
            <Route 
              path="/upload" 
              element={
                <AdminRoute>
                  <UploadPage />
                </AdminRoute>
              } 
            />
          </Routes>
        </div>
      </Router>
    </TenantProvider>
  );
}

export default App;
