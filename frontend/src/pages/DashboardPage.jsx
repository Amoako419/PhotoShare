import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTenant } from '../contexts/TenantContext';
import api, { logout } from '../lib/api';
import Toast from '../components/Toast';import LoadingSpinner from '../components/LoadingSpinner';import { buttonStyles, alertStyles, sectionStyles } from '../utils/buttonStyles';

const DashboardPage = () => {
  const [albums, setAlbums] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [userRole, setUserRole] = useState(null);
  const [deletingAlbum, setDeletingAlbum] = useState(null);
  const [toast, setToast] = useState(null);
  const navigate = useNavigate();
  const { branding, fetchBranding } = useTenant();

  useEffect(() => {
    fetchUserRole();
    fetchAlbums();
    // Fetch branding if not already loaded
    if (!branding.church_name) {
      fetchBranding().catch(err => {
        console.error('Failed to fetch branding:', err);
      });
    }
  }, []);

  const fetchUserRole = async () => {
    try {
      const response = await api.get('/api/v1/core/auth/user/');
      setUserRole(response.data.user?.role);
    } catch (err) {
      console.error('Failed to fetch user role:', err);
    }
  };

  const fetchAlbums = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await api.get('/api/v1/core/albums/');
      // Handle both array and object response formats
      const albumsData = response.data.albums || response.data;
      setAlbums(albumsData);
    } catch (err) {
      if (err.response?.status === 401 || err.response?.status === 403) {
        // Not authenticated - redirect to login (handled by interceptor)
        // navigate('/login'); // Interceptor will handle this
      } else {
        const errorMsg = err.response?.data?.message || 
          err.response?.data?.error || 
          'Failed to load albums. Please try again.';
        setError(errorMsg);
        setToast({ message: errorMsg, type: 'error' });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAlbumClick = (albumId) => {
    navigate(`/album/${albumId}`);
  };

  const handleLogout = async () => {
    await logout();
  };

  const handleDeleteAlbum = async (albumId, albumTitle, e) => {
    e.stopPropagation(); // Prevent navigation to album
    
    if (!window.confirm(`Are you sure you want to delete "${albumTitle}"? This will permanently delete all photos in this album from storage.`)) {
      return;
    }

    setDeletingAlbum(albumId);
    setError('');

    try {
      const response = await api.delete(`/api/v1/core/albums/${albumId}/`);
      
      // Remove deleted album from state
      setAlbums(albums.filter(album => album.id !== albumId));
      
      // Show success toast
      setToast({
        message: `Album "${albumTitle}" deleted successfully`,
        type: 'success'
      });
      
    } catch (err) {
      console.error('Failed to delete album:', err);
      const errorMsg = err.response?.data?.error ||
        err.response?.data?.detail ||
        'Failed to delete album. Please try again.';
      setError(errorMsg);
      setToast({ message: errorMsg, type: 'error' });
    } finally {
      setDeletingAlbum(null);
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
      
      <div className="container mx-auto px-4 py-6 sm:py-8">
        {/* Header Section */}
        <div className={sectionStyles.spacing.section}>
          <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-6">
            <div className="flex items-center gap-3">
              {branding.logo_url && (
                <img 
                  src={branding.logo_url} 
                  alt={`${branding.church_name} Logo`}
                  className="h-10 w-10 sm:h-12 sm:w-12 object-contain rounded-md"
                />
              )}
              <div>
                <h1 className={sectionStyles.pageHeader}>
                  {branding.church_name || 'Church'} Albums
                </h1>
                {branding.church_name && (
                  <p className="text-xs sm:text-sm text-gray-600 mt-1">
                    Welcome to {branding.church_name}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Action Cards - Admin Only */}
          {userRole === 'admin' && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
              <button
                onClick={() => navigate('/upload')}
                className={`${buttonStyles.primary} rounded-xl p-4`}
                aria-label="Upload photos to create new album"
              >
                <div className="flex flex-col items-center gap-2 text-center">
                  <div className="w-10 h-10 sm:w-12 sm:h-12 bg-white bg-opacity-20 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <span className="font-semibold text-sm sm:text-base">Upload Photos</span>
                </div>
              </button>

              <button
                onClick={() => navigate('/settings')}
                className={`${buttonStyles.secondary} rounded-xl p-4`}
                aria-label="Church settings and branding"
              >
                <div className="flex flex-col items-center gap-2 text-center">
                  <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gray-200 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </div>
                  <span className="font-semibold text-sm sm:text-base">Settings</span>
                </div>
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className={`${alertStyles.error} ${sectionStyles.spacing.element}`}>
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <LoadingSpinner message="Loading albums..." />
          </div>
        ) : albums.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md p-8 sm:p-12 text-center">
            <div className="text-gray-400 mb-4">
              <svg 
                className="mx-auto h-16 w-16 sm:h-20 sm:w-20" 
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
            <h3 className="text-xl sm:text-2xl font-semibold text-gray-800 mb-2">
              No Albums Yet
            </h3>
            <p className="text-gray-600 mb-6 text-sm sm:text-base">
              {userRole === 'admin' 
                ? 'Start by uploading photos to create your first album'
                : 'No albums available yet. Check back later!'}
            </p>
            {userRole === 'admin' && (
              <button
                onClick={() => navigate('/upload')}
                className={buttonStyles.primary}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                Upload Photos
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-600">
                {albums.length} {albums.length === 1 ? 'album' : 'albums'}
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6">
              {albums.map((album) => (
              <div
                key={album.id}
                onClick={() => handleAlbumClick(album.id)}
                className="bg-white rounded-xl shadow-md overflow-hidden cursor-pointer hover:shadow-xl transition-all duration-200 active:scale-98"
              >
                <div className="relative bg-gray-200 flex items-center justify-center">
                  {album.thumbnail_url ? (
                    <img 
                      src={album.thumbnail_url} 
                      alt={album.title}
                      className="w-full h-48 sm:h-52 object-cover"
                    />
                  ) : (
                    <div className="w-full h-48 sm:h-52 bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center">
                      <svg 
                        className="h-16 w-16 sm:h-20 sm:w-20 text-indigo-300" 
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
                  )}
                  {userRole === 'admin' && (
                    <button
                      onClick={(e) => handleDeleteAlbum(album.id, album.title, e)}
                      disabled={deletingAlbum === album.id}
                      className={`${buttonStyles.icon} absolute top-2 right-2 bg-white text-red-600 hover:bg-red-50 shadow-lg z-10 disabled:opacity-50 disabled:cursor-not-allowed`}
                      title="Delete album"
                      aria-label={`Delete album ${album.title}`}
                    >
                      {deletingAlbum === album.id ? (
                        <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                      ) : (
                        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      )}
                    </button>
                  )}
                </div>
                <div className="p-4 sm:p-5">
                  <h3 className="text-base sm:text-lg font-semibold text-gray-900 truncate mb-2">
                    {album.title}
                  </h3>
                  <div className="flex items-center justify-between text-sm text-gray-600">
                    {album.event_date && (
                      <span className="flex items-center gap-1.5">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        {new Date(album.event_date).toLocaleDateString('en-US', { 
                          month: 'short', 
                          day: 'numeric', 
                          year: 'numeric' 
                        })}
                      </span>
                    )}
                    {album.photo_count !== undefined && (
                      <span className="flex items-center gap-1.5 font-medium">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        {album.photo_count}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          </>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;