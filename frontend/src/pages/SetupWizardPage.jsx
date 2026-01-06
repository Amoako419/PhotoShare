import { useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import api from '../lib/api';

const SetupWizardPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [church, setChurch] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Form data
  const [formData, setFormData] = useState({
    logo: null,
    coverImage: null,
    confirmation: false
  });
  
  // Preview URLs
  const [logoPreview, setLogoPreview] = useState(null);
  const [coverPreview, setCoverPreview] = useState(null);

  useEffect(() => {
    if (location.state?.church && location.state?.user) {
      setChurch(location.state.church);
      setUser(location.state.user);
    } else {
      // Redirect if no state is passed
      navigate('/admin');
    }
  }, [location, navigate]);

  const handleFileChange = (e, type) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select an image file');
      return;
    }
    
    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setError('Image must be smaller than 5MB');
      return;
    }
    
    setError('');
    
    if (type === 'logo') {
      setFormData(prev => ({ ...prev, logo: file }));
      setLogoPreview(URL.createObjectURL(file));
    } else if (type === 'cover') {
      setFormData(prev => ({ ...prev, coverImage: file }));
      setCoverPreview(URL.createObjectURL(file));
    }
  };

  const handleRemoveFile = (type) => {
    if (type === 'logo') {
      setFormData(prev => ({ ...prev, logo: null }));
      if (logoPreview) URL.revokeObjectURL(logoPreview);
      setLogoPreview(null);
    } else if (type === 'cover') {
      setFormData(prev => ({ ...prev, coverImage: null }));
      if (coverPreview) URL.revokeObjectURL(coverPreview);
      setCoverPreview(null);
    }
  };

  const handleNext = () => {
    setCurrentStep(prev => Math.min(prev + 1, 4));
    setError('');
  };

  const handleBack = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
    setError('');
  };

  const handleActivate = async () => {
    if (!formData.confirmation) {
      setError('Please confirm to activate your church');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      const formDataToSend = new FormData();
      formDataToSend.append('confirmation', 'true');
      
      if (formData.logo) {
        formDataToSend.append('logo', formData.logo);
      }
      
      if (formData.coverImage) {
        formDataToSend.append('cover_image', formData.coverImage);
      }
      
      const response = await api.post('/api/v1/core/church/activate/', formDataToSend, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      console.log('Church activated:', response.data);
      
      // Move to success step
      setCurrentStep(4);
      
    } catch (err) {
      console.error('Activation error:', err);
      setError(
        err.response?.data?.error ||
        'Failed to activate church. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  if (!church || !user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  const steps = [
    { number: 1, title: 'Welcome', icon: '👋' },
    { number: 2, title: 'Branding', icon: '🎨' },
    { number: 3, title: 'Confirm', icon: '✓' },
    { number: 4, title: 'Complete', icon: '🎉' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 py-12">
      <div className="container mx-auto px-4">
        <div className="max-w-4xl mx-auto">
          {/* Progress Steps */}
          <div className="mb-12">
            <div className="flex items-center justify-between">
              {steps.map((step, index) => (
                <div key={step.number} className="flex items-center flex-1">
                  <div className="flex flex-col items-center flex-1">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold transition-all ${
                      currentStep >= step.number
                        ? 'bg-indigo-600 text-white shadow-lg'
                        : 'bg-gray-200 text-gray-500'
                    }`}>
                      {currentStep > step.number ? '✓' : step.icon}
                    </div>
                    <span className={`mt-2 text-sm font-medium ${
                      currentStep >= step.number ? 'text-indigo-600' : 'text-gray-500'
                    }`}>
                      {step.title}
                    </span>
                  </div>
                  {index < steps.length - 1 && (
                    <div className={`h-1 flex-1 mx-2 transition-all ${
                      currentStep > step.number ? 'bg-indigo-600' : 'bg-gray-200'
                    }`} />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Content Card */}
          <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100 min-h-[500px]">
            {error && (
              <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {/* Step 1: Welcome */}
            {currentStep === 1 && (
              <div className="text-center space-y-6">
                <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-2xl mb-4 shadow-lg">
                  <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                </div>
                
                <h1 className="text-4xl font-bold text-gray-900">
                  Welcome to PhotoShare!
                </h1>
                
                <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                  Let's set up your church's photo sharing platform
                </p>

                {/* Church Info */}
                <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border border-indigo-100 max-w-md mx-auto mt-8">
                  <div className="space-y-3 text-left">
                    <div>
                      <span className="text-sm text-gray-600">Church Name</span>
                      <p className="font-semibold text-gray-900 text-lg">{church.name}</p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-600">Church Code</span>
                      <p className="font-mono font-bold text-indigo-600 text-lg">{church.church_code}</p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-600">Admin</span>
                      <p className="font-semibold text-gray-900">{user.email}</p>
                    </div>
                  </div>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 max-w-md mx-auto mt-6">
                  <p className="text-sm text-blue-900">
                    This wizard will help you customize your church's branding and activate your account.
                  </p>
                </div>

                <button
                  onClick={handleNext}
                  className="mt-8 bg-indigo-600 text-white px-8 py-4 rounded-xl text-lg font-semibold hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-300 transition-all shadow-lg"
                >
                  Get Started →
                </button>
              </div>
            )}

            {/* Step 2: Branding */}
            {currentStep === 2 && (
              <div className="space-y-8">
                <div className="text-center">
                  <h2 className="text-3xl font-bold text-gray-900 mb-2">
                    Customize Your Branding
                  </h2>
                  <p className="text-gray-600">
                    Add your church logo and cover image (optional)
                  </p>
                </div>

                {/* Logo Upload */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-3">
                    Church Logo
                  </label>
                  {logoPreview ? (
                    <div className="relative inline-block">
                      <img
                        src={logoPreview}
                        alt="Logo preview"
                        className="w-40 h-40 object-cover rounded-xl border-2 border-gray-200 shadow-md"
                      />
                      <button
                        onClick={() => handleRemoveFile('logo')}
                        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-2 hover:bg-red-600 shadow-lg"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ) : (
                    <label className="flex flex-col items-center justify-center w-full h-48 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:border-indigo-500 transition-colors bg-gray-50">
                      <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        <svg className="w-10 h-10 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        <p className="text-sm text-gray-600 mb-1">
                          <span className="font-semibold">Click to upload</span> or drag and drop
                        </p>
                        <p className="text-xs text-gray-500">PNG, JPG up to 5MB</p>
                      </div>
                      <input
                        type="file"
                        className="hidden"
                        accept="image/*"
                        onChange={(e) => handleFileChange(e, 'logo')}
                      />
                    </label>
                  )}
                </div>

                {/* Cover Image Upload */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-3">
                    Login Cover Image
                  </label>
                  {coverPreview ? (
                    <div className="relative inline-block w-full">
                      <img
                        src={coverPreview}
                        alt="Cover preview"
                        className="w-full h-64 object-cover rounded-xl border-2 border-gray-200 shadow-md"
                      />
                      <button
                        onClick={() => handleRemoveFile('cover')}
                        className="absolute top-4 right-4 bg-red-500 text-white rounded-full p-2 hover:bg-red-600 shadow-lg"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ) : (
                    <label className="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:border-indigo-500 transition-colors bg-gray-50">
                      <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        <svg className="w-10 h-10 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        <p className="text-sm text-gray-600 mb-1">
                          <span className="font-semibold">Click to upload</span> or drag and drop
                        </p>
                        <p className="text-xs text-gray-500">PNG, JPG up to 5MB (recommended: 1920x1080)</p>
                      </div>
                      <input
                        type="file"
                        className="hidden"
                        accept="image/*"
                        onChange={(e) => handleFileChange(e, 'cover')}
                      />
                    </label>
                  )}
                </div>

                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                  <p className="text-sm text-gray-600">
                    <strong>Note:</strong> You can skip this step and add branding later from the settings page.
                  </p>
                </div>

                <div className="flex gap-4">
                  <button
                    onClick={handleBack}
                    className="flex-1 bg-gray-200 text-gray-700 px-6 py-3 rounded-xl font-semibold hover:bg-gray-300 transition-colors"
                  >
                    ← Back
                  </button>
                  <button
                    onClick={handleNext}
                    className="flex-1 bg-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:bg-indigo-700 transition-colors"
                  >
                    Continue →
                  </button>
                </div>
              </div>
            )}

            {/* Step 3: Confirmation */}
            {currentStep === 3 && (
              <div className="space-y-8">
                <div className="text-center">
                  <h2 className="text-3xl font-bold text-gray-900 mb-2">
                    Confirm & Activate
                  </h2>
                  <p className="text-gray-600">
                    Review your setup and activate your church
                  </p>
                </div>

                {/* Summary */}
                <div className="space-y-4">
                  <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border border-indigo-100">
                    <h3 className="font-bold text-gray-900 mb-4 text-lg">Church Details</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Name:</span>
                        <span className="font-semibold text-gray-900">{church.name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Code:</span>
                        <span className="font-mono font-bold text-indigo-600">{church.church_code}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Status:</span>
                        <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-semibold">
                          Pending Activation
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-xl p-6 border border-gray-200">
                    <h3 className="font-bold text-gray-900 mb-4 text-lg">Branding</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Logo:</span>
                        {formData.logo ? (
                          <div className="flex items-center gap-2">
                            <span className="text-green-600 font-semibold">✓ Uploaded</span>
                            <img src={logoPreview} alt="Logo" className="w-10 h-10 object-cover rounded" />
                          </div>
                        ) : (
                          <span className="text-gray-500">Not added</span>
                        )}
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Cover Image:</span>
                        {formData.coverImage ? (
                          <div className="flex items-center gap-2">
                            <span className="text-green-600 font-semibold">✓ Uploaded</span>
                            <img src={coverPreview} alt="Cover" className="w-20 h-10 object-cover rounded" />
                          </div>
                        ) : (
                          <span className="text-gray-500">Not added</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Confirmation Checkbox */}
                <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6">
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.confirmation}
                      onChange={(e) => setFormData(prev => ({ ...prev, confirmation: e.target.checked }))}
                      className="mt-1 w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                    />
                    <div>
                      <p className="font-semibold text-yellow-900 mb-1">I confirm that:</p>
                      <ul className="text-sm text-yellow-800 space-y-1 list-disc list-inside">
                        <li>The church information is correct</li>
                        <li>I am authorized to activate this church</li>
                        <li>I have saved the church code: <span className="font-mono font-bold">{church.church_code}</span></li>
                      </ul>
                    </div>
                  </label>
                </div>

                <div className="flex gap-4">
                  <button
                    onClick={handleBack}
                    disabled={loading}
                    className="flex-1 bg-gray-200 text-gray-700 px-6 py-3 rounded-xl font-semibold hover:bg-gray-300 transition-colors disabled:opacity-50"
                  >
                    ← Back
                  </button>
                  <button
                    onClick={handleActivate}
                    disabled={loading || !formData.confirmation}
                    className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-indigo-700 hover:to-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
                  >
                    {loading ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Activating...
                      </span>
                    ) : (
                      'Activate Church 🚀'
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Step 4: Success */}
            {currentStep === 4 && (
              <div className="text-center space-y-8 py-8">
                <div className="inline-flex items-center justify-center w-24 h-24 bg-gradient-to-br from-green-500 to-emerald-600 rounded-full mb-4 shadow-2xl">
                  <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                
                <h1 className="text-4xl font-bold text-gray-900">
                  Church Activated! 🎉
                </h1>
                
                <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                  Your church is now active and ready to use
                </p>

                <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-8 border border-indigo-100 max-w-md mx-auto">
                  <h3 className="font-bold text-gray-900 mb-4 text-lg">What's Next?</h3>
                  <div className="space-y-4 text-left">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-6 h-6 bg-indigo-600 text-white rounded-full flex items-center justify-center text-sm font-bold">1</div>
                      <p className="text-gray-700">Create albums for your church events</p>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-6 h-6 bg-indigo-600 text-white rounded-full flex items-center justify-center text-sm font-bold">2</div>
                      <p className="text-gray-700">Upload photos to share with members</p>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-6 h-6 bg-indigo-600 text-white rounded-full flex items-center justify-center text-sm font-bold">3</div>
                      <p className="text-gray-700">Share your church code with members</p>
                    </div>
                  </div>
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 max-w-md mx-auto">
                  <p className="text-sm text-yellow-900">
                    <strong>Your Church Code:</strong> <span className="font-mono font-bold text-lg">{church.church_code}</span>
                  </p>
                  <p className="text-xs text-yellow-800 mt-2">
                    Members will need this code to join your church
                  </p>
                </div>

                <button
                  onClick={() => navigate('/admin')}
                  className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-10 py-4 rounded-xl text-lg font-semibold hover:from-indigo-700 hover:to-purple-700 focus:outline-none focus:ring-4 focus:ring-indigo-300 transition-all shadow-lg"
                >
                  Go to Dashboard →
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SetupWizardPage;
