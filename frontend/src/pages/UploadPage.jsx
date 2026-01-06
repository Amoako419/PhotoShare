import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import Toast from '../components/Toast';
import LoadingSpinner from '../components/LoadingSpinner';
import { buttonStyles, alertStyles, sectionStyles } from '../utils/buttonStyles';

const UploadPage = () => {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [albumTitle, setAlbumTitle] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [toast, setToast] = useState(null);
  
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    validateAndSetFiles(files);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    validateAndSetFiles(files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const validateAndSetFiles = (files) => {
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    const maxSize = 10 * 1024 * 1024; // 10MB
    
    const validFiles = files.filter(file => {
      if (!validTypes.includes(file.type)) {
        setToast({ message: `${file.name} is not a valid image type. Only JPEG, PNG, GIF, and WebP are allowed.`, type: 'error' });
        return false;
      }
      if (file.size > maxSize) {
        setToast({ message: `${file.name} is too large. Maximum file size is 10MB.`, type: 'error' });
        return false;
      }
      return true;
    });

    if (validFiles.length > 0) {
      setSelectedFiles(prev => [...prev, ...validFiles]);
      setError('');
    }
  };

  const removeFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    
    if (selectedFiles.length === 0) {
      setError('Please select at least one file to upload.');
      return;
    }

    if (!albumTitle.trim()) {
      setError('Please enter an album title.');
      return;
    }

    try {
      setUploading(true);
      setError('');
      setSuccess('');
      setUploadProgress(0);

      const formData = new FormData();
      formData.append('album_title', albumTitle.trim());
      if (eventDate) {
        formData.append('event_date', eventDate);
      }
      
      // Append all files
      selectedFiles.forEach((file, index) => {
        formData.append('photos', file);
      });

      const response = await api.post('/api/v1/core/photos/upload/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        },
      });

      setToast({ 
        message: `Successfully uploaded ${selectedFiles.length} photo(s) to album "${albumTitle}"`, 
        type: 'success' 
      });
      setSelectedFiles([]);
      setAlbumTitle('');
      setEventDate('');
      
      // Redirect to dashboard after 2 seconds
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
      
    } catch (err) {
      setToast({
        message: err.response?.data?.message || 
                 err.response?.data?.error || 
                 err.response?.data?.detail ||
                 'Failed to upload photos. Please try again.',
        type: 'error'
      });
      setUploadProgress(0);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
      
      <div className="container mx-auto px-4 py-8">
        <div className="mb-4">
          <button
            onClick={() => navigate('/dashboard')}
            className={buttonStyles.link}
            aria-label="Back to Dashboard"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Dashboard
          </button>
        </div>

        <h1 className={sectionStyles.pageHeader}>
          Upload Photos
        </h1>

        <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-md p-8">
          {error && (
            <div className={`${alertStyles.error} ${sectionStyles.spacing.element}`}>
              {error}
            </div>
          )}

          <form onSubmit={handleUpload}>
            <div className="mb-6">
              <label htmlFor="albumTitle" className="block text-sm font-medium text-gray-700 mb-2">
                Album Title *
              </label>
              <input
                type="text"
                id="albumTitle"
                value={albumTitle}
                onChange={(e) => setAlbumTitle(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., Sunday Service - January 5, 2026"
                required
                disabled={uploading}
              />
            </div>

            <div className="mb-6">
              <label htmlFor="eventDate" className="block text-sm font-medium text-gray-700 mb-2">
                Event Date (Optional)
              </label>
              <input
                type="date"
                id="eventDate"
                value={eventDate}
                onChange={(e) => setEventDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={uploading}
              />
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Photos *
              </label>
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center cursor-pointer hover:border-blue-500 transition-colors"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
                  onChange={handleFileSelect}
                  className="hidden"
                  disabled={uploading}
                />
                <div className="text-gray-400 mb-4">
                  <svg className="mx-auto h-12 w-12" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                    <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <p className="text-gray-600 mb-2">
                  Drag and drop photos here, or click to select
                </p>
                <p className="text-sm text-gray-500">
                  Supported formats: JPEG, PNG, GIF, WebP (Max 10MB per file)
                </p>
              </div>
            </div>

            {selectedFiles.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-medium text-gray-700 mb-2">
                  Selected Files ({selectedFiles.length})
                </h3>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {selectedFiles.map((file, index) => (
                    <div key={index} className="flex items-center justify-between bg-gray-50 p-3 rounded-md">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <svg className="w-5 h-5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-900 truncate">{file.name}</p>
                          <p className="text-xs text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                        </div>
                      </div>
                      {!uploading && (
                        <button
                          type="button"
                          onClick={() => removeFile(index)}
                          className="text-red-600 hover:text-red-700 p-1"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {uploading && (
              <div className="mb-6">
                <div className="flex justify-between text-sm text-gray-600 mb-2">
                  <span>Uploading...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={uploading || selectedFiles.length === 0}
              className={`${buttonStyles.primary} w-full`}
            >
              {uploading ? 'Uploading...' : `Upload ${selectedFiles.length} Photo${selectedFiles.length !== 1 ? 's' : ''}`}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default UploadPage;