import { createContext, useContext, useState, useEffect } from 'react';
import api from '../lib/api';

const TenantContext = createContext();

export const useTenant = () => {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error('useTenant must be used within a TenantProvider');
  }
  return context;
};

export const TenantProvider = ({ children }) => {
  const [branding, setBranding] = useState({
    church_name: null,
    church_id: null,
    logo_url: null,
    login_cover_image: null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchBranding = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get('/api/v1/tenants/branding/');
      setBranding(response.data);
      return response.data;
    } catch (err) {
      console.error('Failed to fetch tenant branding:', err);
      setError(err.response?.data?.error || 'Failed to load branding');
      // Reset branding on error
      setBranding({
        church_name: null,
        church_id: null,
        logo_url: null,
        login_cover_image: null,
      });
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const clearBranding = () => {
    setBranding({
      church_name: null,
      church_id: null,
      logo_url: null,
      login_cover_image: null,
    });
    setError(null);
  };

  const value = {
    branding,
    loading,
    error,
    fetchBranding,
    clearBranding,
  };

  return (
    <TenantContext.Provider value={value}>
      {children}
    </TenantContext.Provider>
  );
};
