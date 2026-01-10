import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, FileText, Activity, RefreshCw, Clock, CheckCircle, AlertTriangle } from 'lucide-react';
import ClaimUpload from '../components/Upload/ClaimUpload';
import { signOut, getCurrentUser } from '../services/auth';
import { getClaim } from '../services/api';

const Dashboard = () => {
  const [user, setUser] = useState(null);
  const [uploadedClaims, setUploadedClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    try {
      const userData = await getCurrentUser();
      setUser(userData);
    } catch (err) {
      console.error('Failed to load user:', err);
      navigate('/login');
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = () => {
    signOut();
    navigate('/login');
  };

  const handleUploadSuccess = (claimId) => {
    const newClaim = {
      id: claimId,
      timestamp: new Date().toISOString(),
      status: 'Processing',
      statusColor: 'yellow'
    };
    
    setUploadedClaims(prev => [newClaim, ...prev]);
    
    // Start polling for claim status
    pollClaimStatus(claimId);
  };

  const pollClaimStatus = async (claimId) => {
    let attempts = 0;
    const maxAttempts = 30; // 60 seconds total
    
    const checkStatus = async () => {
      try {
        const claim = await getClaim(claimId);
        
        // Update claim in list
        setUploadedClaims(prev => prev.map(c => 
          c.id === claimId 
            ? {
                ...c,
                status: claim.status || 'Processing',
                statusColor: claim.processing_complete ? 'green' : 'yellow',
                data: claim
              }
            : c
        ));
        
        // If processing complete, stop polling
        if (claim.processing_complete || claim.status === 'SCORING_COMPLETE') {
          return;
        }
        
        // Continue polling
        if (attempts < maxAttempts) {
          attempts++;
          setTimeout(checkStatus, 2000);
        }
      } catch (error) {
        console.error('Error polling claim:', error);
        if (attempts < maxAttempts) {
          attempts++;
          setTimeout(checkStatus, 2000);
        }
      }
    };
    
    // Start polling after 3 seconds
    setTimeout(checkStatus, 3000);
  };

  const viewClaimDetails = (claim) => {
    navigate(`/claim/${encodeURIComponent(claim.id)}`, { state: { claim } });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center">
              <Activity className="w-8 h-8 text-blue-600 mr-3" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Healthcare Claim Intelligence
                </h1>
                <p className="text-sm text-gray-500">AI-Powered Claim Analysis System</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium text-gray-700">{user?.name}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
              </div>
              <button
                onClick={handleSignOut}
                className="flex items-center px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Upload Section - Left 2/3 */}
          <div className="lg:col-span-2">
            <ClaimUpload onUploadSuccess={handleUploadSuccess} />

            {/* Instructions */}
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h3 className="font-bold text-blue-900 mb-3 flex items-center">
                <Activity className="w-5 h-5 mr-2" />
                How It Works
              </h3>
              <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800">
                <li>Upload your medical claim PDF document</li>
                <li>AI extracts text and identifies medical entities (ICD-10, CPT codes)</li>
                <li>Risk scoring algorithm analyzes claim completeness and patterns</li>
                <li>Get instant results with recommended actions</li>
              </ol>
            </div>
          </div>

          {/* Recent Claims Sidebar - Right 1/3 */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-lg p-6 sticky top-24">
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center justify-between">
                <span className="flex items-center">
                  <FileText className="w-5 h-5 mr-2" />
                  Recent Claims
                </span>
                {uploadedClaims.length > 0 && (
                  <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                    {uploadedClaims.length}
                  </span>
                )}
              </h3>

              {uploadedClaims.length === 0 ? (
                <div className="text-center py-8">
                  <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500 text-sm">No claims uploaded yet</p>
                  <p className="text-gray-400 text-xs mt-1">Upload your first claim to get started</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {uploadedClaims.map((claim, idx) => (
                    <div
                      key={idx}
                      onClick={() => claim.data && viewClaimDetails(claim)}
                      className={`p-4 bg-gray-50 rounded-lg border transition-all ${
                        claim.data 
                          ? 'border-gray-200 hover:border-blue-300 hover:shadow-md cursor-pointer' 
                          : 'border-gray-200'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <p className="text-xs text-gray-600 font-mono truncate flex-1 mr-2">
                          {claim.id.split('/').pop()}
                        </p>
                        {claim.statusColor === 'green' && (
                          <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                        )}
                        {claim.statusColor === 'yellow' && (
                          <RefreshCw className="w-4 h-4 text-yellow-500 animate-spin flex-shrink-0" />
                        )}
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <div className="flex items-center text-xs text-gray-500">
                          <Clock className="w-3 h-3 mr-1" />
                          {new Date(claim.timestamp).toLocaleTimeString()}
                        </div>
                        <span className={`px-2 py-1 text-xs rounded font-medium ${
                          claim.statusColor === 'green' 
                            ? 'bg-green-100 text-green-800' 
                            : claim.statusColor === 'yellow'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {claim.status}
                        </span>
                      </div>

                      {claim.data?.risk_analysis && (
                        <div className="mt-2 pt-2 border-t border-gray-200">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-gray-600">Risk Score:</span>
                            <span className={`font-bold ${
                              claim.data.risk_analysis.risk_level === 'LOW'
                                ? 'text-green-600'
                                : claim.data.risk_analysis.risk_level === 'MEDIUM'
                                ? 'text-yellow-600'
                                : 'text-red-600'
                            }`}>
                              {claim.data.risk_analysis.risk_score}/100
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
