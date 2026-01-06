import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTenant } from '../contexts/TenantContext';
import api from '../lib/api';

const SettingsPage = () => {
  const [settings, setSettings] = useState({
    church_name: '',
    logo_url: null,
    login_cover_image: null,
  });
  const [formData, setFormData] = useState({
    church_name: '',
    logo: null,
    login_cover_image: null,
  });
  const [previews, setPreviews] = useState({
    logo: null,
    cover: null,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();
  const { fetchBranding } = useTenant();

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/v1/core/church/settings/');
      setSettings(response.data);
      setFormData({
        church_name: response.data.church_name || '',
        logo: null,
        login_cover_image: null,
      });
    } catch (err) {
      console.error('Failed to fetch settings:', err);
      setError('Failed to load settings. ' + (err.response?.data?.error || ''));
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      church_name: e.target.value,
    });
    if (error) setError('');
    if (success) setSuccess('');
  };

  const handleFileChange = (e, fieldName) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select an image file');
      return;
    }

    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
      setError('Image must be smaller than 5MB');
      return;
    }

    setFormData({
      ...formData,
      [fieldName]: file,
    });

    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreviews({
        ...previews,
        [fieldName === 'logo' ? 'logo' : 'cover']: reader.result,
      });
    };
    reader.readAsDataURL(file);

    if (error) setError('');
    if (success) setSuccess('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      // Create FormData for multipart upload
      const formDataToSend = new FormData();
      
      if (formData.church_name && formData.church_name !== settings.church_name) {
        formDataToSend.append('church_name', formData.church_name);
      }
      
      if (formData.logo) {
        formDataToSend.append('logo', formData.logo);
      }
      
      if (formData.login_cover_image) {
        formDataToSend.append('login_cover_image', formData.login_cover_image);
      }

      // Check if there's anything to update
      if (formDataToSend.entries().next().done) {
        setError('No changes to save');
        setSaving(false);
        return;
      }

      const response = await api.put('/api/v1/core/church/settings/', formDataToSend, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Update local state with new settings
      setSettings(response.data);
      setFormData({
        church_name: response.data.church_name || '',
        logo: null,
        login_cover_image: null,
      });
      setPreviews({
        logo: null,
        cover: null,
      });

      // Refresh branding in TenantContext
      await fetchBranding();

      setSuccess('Settings saved successfully!');
      
      // Clear file inputs
      const fileInputs = document.querySelectorAll('input[type="file"]');
      fileInputs.forEach(input => input.value = '');

    } catch (err) {
      console.error('Failed to save settings:', err);
      setError(
        err.response?.data?.error ||
        err.response?.data?.detail ||
        'Failed to save settings. Please try again.'
      );
    } finally {
      setSaving(false);
    }
  };

  const handleRemovePreview = (fieldName) => {
    setFormData({
      ...formData,
      [fieldName]: null,
    });
    setPreviews({
      ...previews,
      [fieldName === 'logo' ? 'logo' : 'cover']: null,
    });
    
    // Clear file input
    const input = document.querySelector(`input[name="${fieldName}"]`);
    if (input) input.value = '';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Church Settings</h1>
          <button
            onClick={() => navigate('/admin')}
            className="text-gray-600 hover:text-gray-900"
          >
            ← Back to Dashboard
          </button>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-6">
            {success}
          </div>
        )}

        <div className="bg-white rounded-lg shadow-md p-8">
          <form onSubmit={handleSubmit} className="space-y-8">
            {/* Church Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Church Name
              </label>
              <input
                type="text"
                value={formData.church_name}
                onChange={handleInputChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter church name"
              />
            </div>

            {/* Logo Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Church Logo
              </label>
              <p className="text-sm text-gray-500 mb-3">
                This logo will appear in the navigation bar. Recommended size: 200x200px
              </p>
              
              {(previews.logo || settings.logo_url) && (
                <div className="mb-4">
                  <div className="relative inline-block">
                    <img
                      src={previews.logo || settings.logo_url}
                      alt="Logo preview"
                      className="h-24 w-24 object-contain rounded-md border border-gray-300"
                    />
                    {previews.logo && (
                      <button
                        type="button"
                        onClick={() => handleRemovePreview('logo')}
                        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
              )}
              
              <input
                type="file"
                name="logo"
                accept="image/*"
                onChange={(e) => handleFileChange(e, 'logo')}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
            </div>

            {/* Cover Image Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Login Cover Image
              </label>
              <p className="text-sm text-gray-500 mb-3">
                This image will appear on the login page background. Recommended size: 1920x1080px
              </p>
              
              {(previews.cover || settings.login_cover_image) && (
                <div className="mb-4">
                  <div className="relative inline-block">
                    <img
                      src={previews.cover || settings.login_cover_image}
                      alt="Cover preview"
                      className="h-32 w-56 object-cover rounded-md border border-gray-300"
                    />
                    {previews.cover && (
                      <button
                        type="button"
                        onClick={() => handleRemovePreview('login_cover_image')}
                        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
              )}
              
              <input
                type="file"
                name="login_cover_image"
                accept="image/*"
                onChange={(e) => handleFileChange(e, 'login_cover_image')}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
            </div>

            {/* Submit Button */}
            <div className="flex gap-4">
              <button
                type="submit"
                disabled={saving}
                className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              <button
                type="button"
                onClick={() => navigate('/admin')}
                className="bg-gray-200 text-gray-700 px-6 py-2 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
