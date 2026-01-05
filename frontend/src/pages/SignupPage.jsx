import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';

const SignupPage = () => {
  const [step, setStep] = useState(1); // 1: signup, 2: church code
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    churchCode: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const navigate = useNavigate();

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    // Clear error when user starts typing
    if (error) setError('');
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await api.post('/api/v1/core/auth/signup/', {
        email: formData.email,
        password: formData.password
      });

      // Move to step 2 (church code)
      setStep(2);
    } catch (err) {
      setError(
        err.response?.data?.message || 
        err.response?.data?.error || 
        'Signup failed. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleChurchCodeSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await api.post('/api/v1/core/auth/assign_church_anonymous/', {
        email: formData.email,
        church_code: formData.churchCode
      });

      // Success - redirect to dashboard
      navigate('/dashboard');
    } catch (err) {
      setError(
        err.response?.data?.message || 
        err.response?.data?.error || 
        'Invalid church code. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8">
        {step === 1 ? (
          <>
            <h1 className="text-2xl font-bold text-gray-900 text-center mb-8">
              Sign Up
            </h1>
            
            {error && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}

            <form onSubmit={handleSignup} className="space-y-6">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  required
                  value={formData.email}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter your email"
                  disabled={loading}
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                  Password
                </label>
                <input
                  type="password"
                  id="password"
                  name="password"
                  required
                  value={formData.password}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter your password"
                  disabled={loading}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Creating Account...' : 'Sign Up'}
              </button>
            </form>

            <div className="mt-6 text-center">
              <span className="text-sm text-gray-600">
                Already have an account?{' '}
                <a href="/login" className="text-blue-600 hover:text-blue-500">
                  Sign in
                </a>
              </span>
            </div>
          </>
        ) : (
          <>
            <h1 className="text-2xl font-bold text-gray-900 text-center mb-4">
              Join Your Church
            </h1>
            <p className="text-gray-600 text-center mb-8">
              Enter your church code to complete your account setup
            </p>
            
            {error && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}

            <form onSubmit={handleChurchCodeSubmit} className="space-y-6">
              <div>
                <label htmlFor="churchCode" className="block text-sm font-medium text-gray-700 mb-2">
                  Church Code
                </label>
                <input
                  type="text"
                  id="churchCode"
                  name="churchCode"
                  required
                  value={formData.churchCode}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 uppercase"
                  placeholder="Enter church code"
                  disabled={loading}
                />
                <p className="mt-1 text-sm text-gray-500">
                  Contact your church administrator for your church code
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Verifying...' : 'Complete Setup'}
              </button>
            </form>

            <div className="mt-6 text-center">
              <span className="text-sm text-gray-600">
                Wrong email?{' '}
                <button 
                  onClick={() => setStep(1)}
                  className="text-blue-600 hover:text-blue-500"
                  disabled={loading}
                >
                  Start over
                </button>
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default SignupPage;