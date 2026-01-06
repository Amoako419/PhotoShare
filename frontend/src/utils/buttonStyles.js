// Standardized button styles for consistent UI across the app

export const buttonStyles = {
  // Primary action buttons
  primary: 'bg-indigo-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg',
  
  // Secondary/neutral buttons
  secondary: 'bg-gray-100 text-gray-700 px-6 py-3 rounded-lg font-semibold hover:bg-gray-200 focus:outline-none focus:ring-4 focus:ring-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all',
  
  // Danger/destructive buttons
  danger: 'bg-red-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-red-700 focus:outline-none focus:ring-4 focus:ring-red-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg',
  
  // Outline buttons
  outline: 'bg-transparent border-2 border-gray-300 text-gray-700 px-6 py-3 rounded-lg font-semibold hover:bg-gray-50 hover:border-gray-400 focus:outline-none focus:ring-4 focus:ring-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all',
  
  // Link-style buttons
  link: 'text-indigo-600 hover:text-indigo-700 font-medium underline-offset-2 hover:underline transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
  
  // Icon buttons
  icon: 'p-2 rounded-lg text-gray-600 hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors',
  
  // Small variants
  primarySm: 'bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all',
  
  secondarySm: 'bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-semibold hover:bg-gray-200 focus:outline-none focus:ring-4 focus:ring-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all',
  
  dangerSm: 'bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-red-700 focus:outline-none focus:ring-4 focus:ring-red-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all',
};

export const alertStyles = {
  error: 'bg-red-50 border-2 border-red-200 text-red-800 px-4 py-3 rounded-lg',
  success: 'bg-green-50 border-2 border-green-200 text-green-800 px-4 py-3 rounded-lg',
  warning: 'bg-yellow-50 border-2 border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg',
  info: 'bg-blue-50 border-2 border-blue-200 text-blue-800 px-4 py-3 rounded-lg',
};

export const sectionStyles = {
  // Page headers
  pageHeader: 'text-3xl font-bold text-gray-900 mb-2',
  pageSubheader: 'text-gray-600 mb-8',
  
  // Section headers
  sectionHeader: 'text-xl font-semibold text-gray-900 mb-4',
  sectionSubheader: 'text-sm text-gray-600 mb-6',
  
  // Card headers
  cardHeader: 'text-lg font-semibold text-gray-900 mb-3',
  
  // Spacing utilities
  section: 'mb-12',
  subsection: 'mb-8',
  content: 'mb-6',
};
