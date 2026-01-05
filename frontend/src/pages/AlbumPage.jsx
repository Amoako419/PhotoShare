import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api, { logout } from '../lib/api';

const AlbumPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [album, setAlbum] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [signedUrls, setSignedUrls] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [urlsLoading, setUrlsLoading] = useState({});
  const [downloadingPhotos, setDownloadingPhotos] = useState({});
  
  const observerRef = useRef(null);

  useEffect(() => {
    fetchAlbumPhotos();
  }, [id]);

  const fetchAlbumPhotos = async () => {
    try {
      setLoading(true);
      setError('');
      
      // Fetch photo metadata for this album
      const response = await api.get(`/api/v1/core/photos/?album_id=${id}`);
      
      // Handle different response formats
      if (response.data.photos) {
        setPhotos(response.data.photos);
      } else if (response.data.results) {
        setPhotos(response.data.results);
      } else if (Array.isArray(response.data)) {
        setPhotos(response.data);
      } else {
        setPhotos([]);
      }
    } catch (err) {
      if (err.response?.status === 401 || err.response?.status === 403) {
        // Not authenticated or unauthorized - redirect to login
        navigate('/login');
      } else if (err.response?.status === 404) {
        setError('Album not found or you do not have access to this album.');
      } else {
        setError(
          err.response?.data?.message || 
          err.response?.data?.error || 
          'Failed to load photos. Please try again.'
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchSignedUrl = async (photoId) => {
    // Don't fetch if already loading or loaded
    if (urlsLoading[photoId] || signedUrls[photoId]) {
      return;
    }

    try {
      setUrlsLoading(prev => ({ ...prev, [photoId]: true }));
      
      const response = await api.get(`/api/v1/core/photos/${photoId}/access/`);
      
      // Backend returns 'secure_url' not 'signed_url'
      const url = response.data.secure_url || response.data.signed_url;
      
      setSignedUrls(prev => ({
        ...prev,
        [photoId]: url
      }));
    } catch (err) {
      console.error(`Failed to fetch signed URL for photo ${photoId}:`, err);
      setSignedUrls(prev => ({
        ...prev,
        [photoId]: null // Mark as failed
      }));
    } finally {
      setUrlsLoading(prev => ({ ...prev, [photoId]: false }));
    }
  };

  // Intersection Observer callback for lazy loading
  const handleIntersection = (entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const photoId = entry.target.dataset.photoId;
        if (photoId && !signedUrls[photoId] && !urlsLoading[photoId]) {
          fetchSignedUrl(parseInt(photoId));
        }
      }
    });
  };

  // Set up Intersection Observer
  useEffect(() => {
    observerRef.current = new IntersectionObserver(handleIntersection, {
      rootMargin: '200px', // Start loading before image is visible
      threshold: 0.01
    });

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [signedUrls, urlsLoading]);

  // Observe photo elements
  useEffect(() => {
    const photoElements = document.querySelectorAll('[data-photo-id]');
    photoElements.forEach(el => {
      if (observerRef.current) {
        observerRef.current.observe(el);
      }
    });

    return () => {
      photoElements.forEach(el => {
        if (observerRef.current) {
          observerRef.current.unobserve(el);
        }
      });
    };
  }, [photos]);

  const handleLogout = async () => {
    await logout();
  };

  const handleDownload = async (photoId, photoTitle) => {
    try {
      setDownloadingPhotos(prev => ({ ...prev, [photoId]: true }));
      
      // Fetch fresh signed URL for download
      const response = await api.get(`/api/v1/core/photos/${photoId}/access/`);
      const signedUrl = response.data.secure_url || response.data.signed_url;
      
      if (!signedUrl) {
        throw new Error('No signed URL received from server');
      }
      
      // Create a temporary anchor element to trigger download
      const link = document.createElement('a');
      link.href = signedUrl;
      link.download = photoTitle || `photo-${photoId}`;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      
      // Append to body, click, and remove
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
    } catch (err) {
      console.error(`Failed to download photo ${photoId}:`, err);
      
      if (err.response?.status === 401 || err.response?.status === 403) {
        // Session expired or unauthorized
        setError('Session expired. Please log in again.');
        setTimeout(() => navigate('/login'), 2000);
      } else if (err.response?.status === 404) {
        setError('Photo not found or access denied.');
      } else {
        setError(
          err.response?.data?.error || 
          err.response?.data?.message ||
          'Failed to download photo. Please try again.'
        );
      }
      
      // Clear error after 5 seconds
      setTimeout(() => setError(''), 5000);
    } finally {
      setDownloadingPhotos(prev => ({ ...prev, [photoId]: false }));
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <div className="flex justify-between items-start mb-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="text-blue-600 hover:text-blue-700 flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Dashboard
            </button>
            <button
              onClick={handleLogout}
              className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 text-sm"
            >
              Logout
            </button>
          </div>
          <h1 className="text-3xl font-bold text-gray-900">
            {album?.title || `Album ${id}`}
          </h1>
          {album?.event_date && (
            <p className="text-gray-600 mt-2">
              {new Date(album.event_date).toLocaleDateString()}
            </p>
          )}
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="text-gray-600">Loading photos...</div>
          </div>
        ) : photos.length === 0 ? (
          <div className="bg-white rounded-lg shadow-md p-12 text-center">
            <div className="text-gray-400 mb-4">
              <svg 
                className="mx-auto h-12 w-12" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" 
                />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">
              No Photos in This Album
            </h3>
            <p className="text-gray-600">
              This album doesn't contain any photos yet.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {photos.map((photo) => (
              <div
                key={photo.id}
                className="bg-white rounded-lg shadow-md overflow-hidden group relative"
              >
                <div
                  data-photo-id={photo.id}
                  className="aspect-square"
                >
                  {signedUrls[photo.id] ? (
                    <img
                      src={signedUrls[photo.id]}
                      alt={photo.title || 'Photo'}
                      className="w-full h-full object-cover transition-opacity duration-300"
                      loading="lazy"
                      onLoad={(e) => {
                        e.target.style.opacity = '1';
                      }}
                      style={{ opacity: 0 }}
                      onError={(e) => {
                        // If image fails to load, show placeholder
                        e.target.style.display = 'none';
                        e.target.parentElement.innerHTML = `
                          <div class="w-full h-full flex items-center justify-center bg-red-50">
                            <div class="text-center">
                              <svg class="mx-auto h-12 w-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                              </svg>
                              <span class="text-red-500 text-sm mt-2">Failed to load</span>
                            </div>
                          </div>
                        `;
                      }}
                    />
                  ) : signedUrls[photo.id] === null ? (
                    <div className="w-full h-full flex items-center justify-center bg-red-50">
                      <div className="text-center">
                        <svg className="mx-auto h-12 w-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        <span className="text-red-500 text-sm mt-2">Failed to load</span>
                      </div>
                    </div>
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100">
                      <div className="relative">
                        {/* Animated spinner */}
                        <div className="animate-spin rounded-full h-12 w-12 border-4 border-gray-200 border-t-blue-500"></div>
                        {/* Pulsing photo icon */}
                        <div className="absolute inset-0 flex items-center justify-center">
                          <svg 
                            className="h-6 w-6 text-gray-400 animate-pulse" 
                            fill="none" 
                            stroke="currentColor" 
                            viewBox="0 0 24 24"
                          >
                            <path 
                              strokeLinecap="round" 
                              strokeLinejoin="round" 
                              strokeWidth={2} 
                              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" 
                            />
                          </svg>
                        </div>
                      </div>
                      <p className="text-xs text-gray-500 mt-3 animate-pulse">Loading...</p>
                    </div>
                  )}
                </div>
                
                {/* Download button overlay */}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-3 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleDownload(photo.id, photo.title || photo.filename)}
                    disabled={downloadingPhotos[photo.id]}
                    className="w-full bg-white text-gray-900 px-3 py-2 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm font-medium"
                    title="Download photo"
                  >
                    {downloadingPhotos[photo.id] ? (
                      <>
                        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Downloading...
                      </>
                    ) : (
                      <>
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Download
                      </>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {photos.length > 0 && (
          <div className="mt-6 text-center text-gray-600">
            {photos.length} {photos.length === 1 ? 'photo' : 'photos'} in this album
          </div>
        )}
      </div>
    </div>
  );
};

export default AlbumPage;