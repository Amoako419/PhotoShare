import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTenant } from '../contexts/TenantContext';
import api, { logout } from '../lib/api';
import LoadingSpinner from '../components/LoadingSpinner';
import { buttonStyles, alertStyles, sectionStyles } from '../utils/buttonStyles';

const HomePage = () => {
  const [albums, setAlbums] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { branding, fetchBranding } = useTenant();

  useEffect(() => {
    fetchAlbums();
    // Fetch branding if not already loaded
    if (!branding.church_name) {
      fetchBranding().catch(err => {
        console.error('Failed to fetch branding:', err);
      });
    }
  }, []);

  const fetchAlbums = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await api.get('/api/v1/core/albums/');
      const albumsData = response.data.albums || response.data;
      setAlbums(albumsData);
    } catch (err) {
      if (err.response?.status === 401 || err.response?.status === 403) {
        // Not authenticated - redirect handled by interceptor
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

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className={`flex items-center gap-4 ${sectionStyles.spacing.section}`}>
          {branding.logo_url && (
            <img 
              src={branding.logo_url} 
              alt={`${branding.church_name} Logo`}
              className="h-12 w-12 object-contain rounded-md"
            />
          )}
          <div>
            <h1 className={sectionStyles.pageHeader}>
              {branding.church_name || 'Church'} Photos
            </h1>
            {branding.church_name && (
              <p className="text-sm text-gray-600 mt-1">
                Welcome to {branding.church_name}
              </p>
            )}
          </div>
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
            <p className="text-gray-600">
              No albums available yet. Check back later!
            </p>
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
                  <h3 className="text-lg font-semibold text-gray-900 mb-1 truncate">
                    {album.title}
                  </h3>
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

export default HomePage;
