import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTenant } from '../contexts/TenantContext';
import api, { logout } from '../lib/api';

const DashboardPage = () => {
  const [albums, setAlbums] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [userRole, setUserRole] = useState(null);
  const [deletingAlbum, setDeletingAlbum] = useState(null);
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
        setError(
          err.response?.data?.message || 
          err.response?.data?.error || 
          'Failed to load albums. Please try again.'
        );
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
      
      // Show success message briefly
      const message = response.data.message || 'Album deleted successfully';
      console.log(message, response.data);
      
    } catch (err) {
      console.error('Failed to delete album:', err);
      setError(
        err.response?.data?.error ||
        err.response?.data?.detail ||
        'Failed to delete album. Please try again.'
      );
    } finally {
      setDeletingAlbum(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-4">
            {branding.logo_url && (
              <img 
                src={branding.logo_url} 
                alt={`${branding.church_name} Logo`}
                className="h-12 w-12 object-contain rounded-md"
              />
            )}
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {branding.church_name || 'Church'} Albums
              </h1>
              {branding.church_name && (
                <p className="text-sm text-gray-600 mt-1">
                  Welcome to {branding.church_name}
                </p>
              )}
            </div>
          </div>
          <div className="flex gap-3">
            {userRole === 'admin' && (
              <button
                onClick={() => navigate('/upload')}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Upload Photos
              </button>
            )}
            <button
              onClick={handleLogout}
              className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              Logout
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="text-gray-600">Loading albums...</div>
          </div>
        ) : albums.length === 0 ? (
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
              No Albums Yet
            </h3>
            <p className="text-gray-600 mb-6">
              {userRole === 'admin' 
                ? 'Start by uploading photos to create your first album'
                : 'No albums available yet. Check back later!'}
            </p>
            {userRole === 'admin' && (
              <button
                onClick={() => navigate('/upload')}
                className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Upload Photos
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {albums.map((album) => (
              <div
                key={album.id}
                onClick={() => handleAlbumClick(album.id)}
                className="bg-white rounded-lg shadow-md overflow-hidden cursor-pointer hover:shadow-lg transition-shadow duration-200"
              >
                <div className="aspect-w-16 aspect-h-9 bg-gray-200 flex items-center justify-center">
                  {album.thumbnail_url ? (
                    <img 
                      src={album.thumbnail_url} 
                      alt={album.title}
                      className="w-full h-48 object-cover"
                    />
                  ) : (
                    <div className="w-full h-48 bg-gradient-to-br from-blue-100 to-blue-200 flex items-center justify-center">
                      <svg 
                        className="h-16 w-16 text-blue-300" 
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
                </div>
                <div className="p-4">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="text-lg font-semibold text-gray-900 truncate flex-1">
                      {album.title}
                    </h3>
                    {userRole === 'admin' && (
                      <button
                        onClick={(e) => handleDeleteAlbum(album.id, album.title, e)}
                        disabled={deletingAlbum === album.id}
                        className="ml-2 text-red-600 hover:text-red-800 hover:bg-red-50 p-1.5 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Delete album"
                      >
                        {deletingAlbum === album.id ? (
                          <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                        ) : (
                          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        )}
                      </button>
                    )}
                  </div>
                  {album.event_date && (
                    <p className="text-sm text-gray-500 mb-2">
                      {new Date(album.event_date).toLocaleDateString()}
                    </p>
                  )}
                  {album.photo_count !== undefined && (
                    <p className="text-sm text-gray-600">
                      {album.photo_count} {album.photo_count === 1 ? 'photo' : 'photos'}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;