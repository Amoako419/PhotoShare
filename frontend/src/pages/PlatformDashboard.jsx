import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { logout } from '../lib/api';
import api from '../lib/api';

const PlatformDashboard = () => {
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState({
    total_churches: 0,
    active_churches: 0,
    total_users: 0,
    total_albums: 0,
    total_photos: 0
  });
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [churchName, setChurchName] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [createdChurch, setCreatedChurch] = useState(null);
  const [churches, setChurches] = useState([]);
  const [filteredChurches, setFilteredChurches] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedChurch, setSelectedChurch] = useState(null);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [churchToToggle, setChurchToToggle] = useState(null);
  const [toggling, setToggling] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchUserData();
    fetchChurches();
  }, []);

  const fetchUserData = async () => {
    try {
      const response = await api.get('/api/v1/core/auth/user/');
      setUser(response.data.user);
    } catch (err) {
      console.error('Failed to fetch user:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchChurches = async () => {
    try {
      const response = await api.get('/api/v1/platform/churches/');
      const churchesData = response.data.churches || [];
      const summary = response.data.summary || {};
      
      setChurches(churchesData);
      setFilteredChurches(churchesData);
      setStats(prev => ({
        ...prev,
        total_churches: summary.total_churches || 0,
        active_churches: summary.active_churches || 0,
        total_users: summary.total_users || 0
      }));
    } catch (err) {
      console.error('Failed to fetch churches:', err);
    }
  };

  useEffect(() => {
    // Apply status filter
    if (statusFilter === 'all') {
      setFilteredChurches(churches);
    } else if (statusFilter === 'active') {
      setFilteredChurches(churches.filter(c => c.is_active));
    } else if (statusFilter === 'inactive') {
      setFilteredChurches(churches.filter(c => !c.is_active));
    }
  }, [statusFilter, churches]);

  const handleCreateChurch = async (e) => {
    e.preventDefault();
    setCreating(true);
    setError('');

    try {
      const response = await api.post('/api/v1/platform/churches/', {
        name: churchName.trim()
      });

      setCreatedChurch(response.data);
      setChurchName('');
      
      // Refresh churches list
      await fetchChurches();
    } catch (err) {
      setError(
        err.response?.data?.error || 
        'Failed to create church. Please try again.'
      );
    } finally {
      setCreating(false);
    }
  };

  const handleCopyCode = () => {
    if (createdChurch?.church_code) {
      navigator.clipboard.writeText(createdChurch.church_code);
    }
  };

  const handleCloseModal = () => {
    setShowCreateModal(false);
    setCreatedChurch(null);
    setChurchName('');
    setError('');
  };

  const handleToggleStatus = (church) => {
    setChurchToToggle(church);
    setShowStatusModal(true);
  };

  const confirmToggleStatus = async () => {
    if (!churchToToggle) return;

    setToggling(true);
    setError('');

    try {
      const newStatus = !churchToToggle.is_active;
      const response = await api.patch(
        `/api/v1/platform/churches/${churchToToggle.church_id}/status/`,
        { is_active: newStatus }
      );

      // Update churches list with new status
      setChurches(prev =>
        prev.map(church =>
          church.church_id === churchToToggle.church_id
            ? { ...church, is_active: response.data.is_active }
            : church
        )
      );

      // Close modal
      setShowStatusModal(false);
      setChurchToToggle(null);
    } catch (err) {
      console.error('Failed to toggle church status:', err);
      setError(
        err.response?.data?.error ||
        'Failed to update church status. Please try again.'
      );
    } finally {
      setToggling(false);
    }
  };

  const cancelToggleStatus = () => {
    setShowStatusModal(false);
    setChurchToToggle(null);
    setError('');
  };

  const handleLogout = async () => {
    await logout();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className="bg-indigo-600 text-white p-2 rounded-lg">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Platform Dashboard</h1>
                <p className="text-sm text-gray-600">Super Admin Control Panel</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900">{user?.email}</p>
                <p className="text-xs text-indigo-600 font-semibold uppercase">{user?.role}</p>
              </div>
              <button
                onClick={handleLogout}
                className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Churches</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{stats.total_churches}</p>
              </div>
              <div className="bg-blue-100 p-3 rounded-lg">
                <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Active Churches</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{stats.active_churches}</p>
              </div>
              <div className="bg-green-100 p-3 rounded-lg">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Users</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{stats.total_users}</p>
              </div>
              <div className="bg-purple-100 p-3 rounded-lg">
                <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Churches Management Section */}
        <div className="bg-white rounded-lg shadow-md mb-8">
          <div className="p-6 border-b border-gray-200">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Church Tenants</h2>
                <p className="text-sm text-gray-600 mt-1">Monitor and manage all church tenants</p>
              </div>
              <div className="flex gap-3">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="all">All Churches</option>
                  <option value="active">Active Only</option>
                  <option value="inactive">Inactive Only</option>
                </select>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 flex items-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  Add Church
                </button>
              </div>
            </div>
          </div>

          {/* Churches Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Church Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Church Code
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Users
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Admins
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Members
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredChurches.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="px-6 py-8 text-center text-gray-500">
                      <div className="flex flex-col items-center">
                        <svg className="w-12 h-12 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                        <p className="text-lg font-medium">No churches found</p>
                        <p className="text-sm mt-1">Create your first church tenant to get started</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredChurches.map((church) => (
                    <tr 
                      key={church.church_id}
                      className="hover:bg-gray-50 cursor-pointer transition-colors"
                      onClick={() => setSelectedChurch(selectedChurch?.church_id === church.church_id ? null : church)}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                            <svg className="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                            </svg>
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900">{church.name}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {church.is_active ? (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                            Active
                          </span>
                        ) : (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                            Inactive
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-mono text-gray-900">{church.church_code}</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm text-gray-900 font-medium">{church.total_users}</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm text-gray-600">{church.admin_count}</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm text-gray-600">{church.member_count}</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(church.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleToggleStatus(church);
                            }}
                            className={`px-3 py-1 rounded-md text-xs font-semibold ${
                              church.is_active
                                ? 'bg-red-100 text-red-700 hover:bg-red-200'
                                : 'bg-green-100 text-green-700 hover:bg-green-200'
                            }`}
                          >
                            {church.is_active ? 'Disable' : 'Enable'}
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/platform/churches/${church.church_id}/stats`);
                            }}
                            className="text-indigo-600 hover:text-indigo-900 font-medium"
                          >
                            Stats
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedChurch(selectedChurch?.church_id === church.church_id ? null : church);
                            }}
                            className="text-gray-600 hover:text-gray-900"
                          >
                            {selectedChurch?.church_id === church.church_id ? 'Hide' : 'Details'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Selected Church Details */}
          {selectedChurch && (
            <div className="border-t border-gray-200 bg-gray-50 p-6">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-semibold text-gray-900">{selectedChurch.name} - Details</h3>
                <button
                  onClick={() => setSelectedChurch(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <p className="text-sm font-medium text-gray-600">Church ID</p>
                  <p className="text-xs font-mono text-gray-900 mt-1 break-all">{selectedChurch.church_id}</p>
                </div>
                
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <p className="text-sm font-medium text-gray-600">Church Code</p>
                  <p className="text-lg font-mono font-bold text-indigo-600 mt-1">{selectedChurch.church_code}</p>
                </div>
                
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <p className="text-sm font-medium text-gray-600">Status</p>
                  <p className="text-sm mt-1">
                    {selectedChurch.is_active ? (
                      <span className="text-green-600 font-semibold">✓ Active</span>
                    ) : (
                      <span className="text-red-600 font-semibold">✗ Inactive</span>
                    )}
                  </p>
                </div>
                
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <p className="text-sm font-medium text-gray-600">Total Users</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{selectedChurch.total_users}</p>
                </div>
                
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <p className="text-sm font-medium text-gray-600">Admins</p>
                  <p className="text-2xl font-bold text-blue-600 mt-1">{selectedChurch.admin_count}</p>
                </div>
                
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <p className="text-sm font-medium text-gray-600">Members</p>
                  <p className="text-2xl font-bold text-purple-600 mt-1">{selectedChurch.member_count}</p>
                </div>
                
                <div className="bg-white rounded-lg p-4 border border-gray-200 md:col-span-3">
                  <p className="text-sm font-medium text-gray-600">Created On</p>
                  <p className="text-sm text-gray-900 mt-1">
                    {new Date(selectedChurch.created_at).toLocaleString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Info Card */}
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-6">
          <div className="flex items-start gap-3">
            <div className="bg-indigo-100 p-2 rounded-lg">
              <svg className="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h3 className="font-semibold text-indigo-900 mb-1">Super Admin Access</h3>
              <p className="text-sm text-indigo-700">
                You have full platform access with no tenant restrictions. This dashboard provides oversight of all churches, users, and content across the platform.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Create Church Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="p-6">
              {!createdChurch ? (
                <>
                  <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold text-gray-900">Create Church Tenant</h2>
                    <button
                      onClick={handleCloseModal}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>

                  {error && (
                    <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                      {error}
                    </div>
                  )}

                  <form onSubmit={handleCreateChurch}>
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Church Name <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={churchName}
                        onChange={(e) => setChurchName(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="e.g., First Baptist Church"
                        required
                        maxLength={255}
                        disabled={creating}
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        This will be the display name for the church tenant
                      </p>
                    </div>

                    <div className="flex gap-3">
                      <button
                        type="submit"
                        disabled={creating || !churchName.trim()}
                        className="flex-1 bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {creating ? 'Creating...' : 'Create Church'}
                      </button>
                      <button
                        type="button"
                        onClick={handleCloseModal}
                        disabled={creating}
                        className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                </>
              ) : (
                <>
                  <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold text-green-600">Church Created!</h2>
                    <button
                      onClick={handleCloseModal}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>

                  <div className="mb-6">
                    <div className="flex items-center justify-center mb-4">
                      <div className="bg-green-100 p-3 rounded-full">
                        <svg className="w-12 h-12 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    </div>

                    <div className="text-center mb-4">
                      <p className="text-lg font-semibold text-gray-900 mb-1">
                        {createdChurch.name}
                      </p>
                      <p className="text-sm text-gray-600">
                        has been created successfully
                      </p>
                    </div>

                    <div className="bg-indigo-50 border-2 border-indigo-200 rounded-lg p-4 mb-4">
                      <label className="block text-sm font-medium text-indigo-900 mb-2">
                        Church Code (Share with Admin)
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={createdChurch.church_code}
                          readOnly
                          className="flex-1 px-3 py-2 bg-white border border-indigo-300 rounded-md font-mono text-lg font-bold text-indigo-900 text-center"
                        />
                        <button
                          onClick={handleCopyCode}
                          className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          title="Copy code"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        </button>
                      </div>
                      <p className="text-xs text-indigo-700 mt-2">
                        ⚠️ Save this code securely. Admins will need it to sign up.
                      </p>
                    </div>

                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                      <p className="text-xs text-yellow-800">
                        <strong>Note:</strong> The first user to sign up with this church code will automatically become the admin.
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={handleCloseModal}
                    className="w-full bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
                  >
                    Done
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Status Toggle Confirmation Modal */}
      {showStatusModal && churchToToggle && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center mb-4">
              <div className={`p-3 rounded-full ${
                churchToToggle.is_active ? 'bg-red-100' : 'bg-green-100'
              }`}>
                <svg className={`w-6 h-6 ${
                  churchToToggle.is_active ? 'text-red-600' : 'text-green-600'
                }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {churchToToggle.is_active ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  )}
                </svg>
              </div>
              <h3 className="text-lg font-bold text-gray-900 ml-3">
                {churchToToggle.is_active ? 'Disable Church' : 'Enable Church'}
              </h3>
            </div>

            <div className="mb-6">
              <p className="text-gray-700 mb-3">
                Are you sure you want to {churchToToggle.is_active ? 'disable' : 'enable'}{' '}
                <strong>{churchToToggle.name}</strong>?
              </p>

              {churchToToggle.is_active ? (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <p className="text-sm text-yellow-800">
                    <strong>Warning:</strong> Users from this church will not be able to log in or sign up until the church is re-enabled.
                  </p>
                </div>
              ) : (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <p className="text-sm text-green-800">
                    <strong>Note:</strong> Users will be able to log in and sign up again after enabling.
                  </p>
                </div>
              )}

              {error && (
                <div className="mt-3 bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">
                  {error}
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={cancelToggleStatus}
                disabled={toggling}
                className="flex-1 bg-gray-200 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmToggleStatus}
                disabled={toggling}
                className={`flex-1 px-4 py-2 rounded-md focus:outline-none focus:ring-2 disabled:opacity-50 ${
                  churchToToggle.is_active
                    ? 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500'
                    : 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500'
                }`}
              >
                {toggling ? 'Processing...' : churchToToggle.is_active ? 'Disable' : 'Enable'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PlatformDashboard;
