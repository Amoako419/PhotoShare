import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTenant } from '../contexts/TenantContext';
import AuthNav from '../components/AuthNav';
import api from '../lib/api';

const LoginPage = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [loginVisuals, setLoginVisuals] = useState({
    church_name: null,
    login_cover_image: null,
  });
  
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { fetchBranding } = useTenant();

  useEffect(() => {
    // Try to fetch login branding if church_code is available
    const churchCode = searchParams.get('church') || localStorage.getItem('last_church_code');
    if (churchCode) {
      fetchLoginVisuals(churchCode);
    }
  }, []);

  const fetchLoginVisuals = async (churchCode) => {
    try {
      const response = await api.get(`/api/v1/tenants/branding/public/?church_code=${churchCode}`);
      setLoginVisuals(response.data);
      // Save for next login
      localStorage.setItem('last_church_code', churchCode);
    } catch (err) {
      console.error('Failed to fetch login visuals:', err);
      // Fail silently - show default background
    }
  };

  const extractChurchCodeFromEmail = (email) => {
    // Simple heuristic: if email domain exists, we could map it
    // For now, just return null
    return null;
  };

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    // Clear error when user starts typing
    if (error) setError('');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await api.post('/api/v1/core/auth/login/', {
        email: formData.email,
        password: formData.password
      });

      // Success - JWT is stored in httpOnly cookie by backend
      
      // Fetch user info to determine role
      try {
        const userResponse = await api.get('/api/v1/core/auth/user/');
        const userRole = userResponse.data.user?.role;
        
        // Only fetch tenant branding for non-superadmin users
        if (userRole !== 'superadmin') {
          try {
            await fetchBranding();
          } catch (brandingErr) {
            console.error('Failed to fetch branding, but login successful:', brandingErr);
            // Don't block navigation if branding fetch fails
          }
        }
        
        // Redirect based on role
        if (userRole === 'superadmin') {
          navigate('/platform/dashboard');
        } else if (userRole === 'admin') {
          navigate('/admin');
        } else {
          navigate('/home');
        }
      } catch (userErr) {
        console.error('Failed to fetch user role:', userErr);
        // Fallback to home if we can't determine role
        navigate('/home');
      }
    } catch (err) {
      setError(
        err.response?.data?.detail || 
        err.response?.data?.message || 
        err.response?.data?.error || 
        'Login failed. Please check your credentials.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <AuthNav />
      
      <div className="flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-600 rounded-2xl mb-4 shadow-lg">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            
            {loginVisuals.church_name && (
              <p className="text-sm text-gray-600 mb-2">{loginVisuals.church_name}</p>
            )}
            
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Welcome Back
            </h1>
            <p className="text-gray-600">
              Sign in to access your church photos
            </p>
          </div>
          
          {/* Form Card */}
          <div className="bg-white rounded-2xl shadow-md p-8 border border-gray-100">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 flex items-start gap-2">
                <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <span className="text-sm">{error}</span>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label htmlFor="email" className="block text-sm font-semibold text-gray-700 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                    </svg>
                  </div>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    required
                    value={formData.email}
                    onChange={handleInputChange}
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-colors"
                    placeholder="your.email@example.com"
                    disabled={loading}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-semibold text-gray-700 mb-2">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </div>
                  <input
                    type="password"
                    id="password"
                    name="password"
                    required
                    value={formData.password}
                    onChange={handleInputChange}
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-colors"
                    placeholder="Enter your password"
                    disabled={loading}
                  />
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  Password is case-sensitive
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Signing In...
                  </span>
                ) : (
                  'Sign In'
                )}
              </button>
            </form>
          </div>

          {/* Sign up link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Don't have an account?{' '}
              <Link to="/signup" className="font-semibold text-indigo-600 hover:text-indigo-500 transition-colors">
                Join with church code
              </Link>
            </p>
          </div>
          
          {/* Admin link */}
          <div className="mt-4 text-center">
            <p className="text-xs text-gray-500">
              Church administrator?{' '}
              <Link to="/admin-signup" className="font-medium text-gray-700 hover:text-gray-900 transition-colors">
                Create church account
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;