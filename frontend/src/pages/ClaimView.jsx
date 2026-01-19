import { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, FileText, User, Calendar, DollarSign, Activity, AlertTriangle, CheckCircle, Pill, Stethoscope } from 'lucide-react';
import { getClaim } from '../services/api';

const ClaimView = () => {
  const { claimId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [claim, setClaim] = useState(location.state?.claim?.data || null);
  const [loading, setLoading] = useState(!claim);
  const [error, setError] = useState('');

  // 🔧 Helper function to unmarshall DynamoDB data
  const unmarshallValue = (value) => {
    if (!value) return null;
    if (value.S !== undefined) return value.S;
    if (value.N !== undefined) return Number(value.N);
    if (value.BOOL !== undefined) return value.BOOL;
    if (value.M !== undefined) return unmarshallMap(value.M);
    if (value.L !== undefined) return unmarshallList(value.L);
    return value;
  };

  const unmarshallMap = (map) => {
    const result = {};
    for (const [key, value] of Object.entries(map)) {
      result[key] = unmarshallValue(value);
    }
    return result;
  };

  const unmarshallList = (list) => {
    return list.map(item => unmarshallValue(item));
  };

  const unmarshallClaim = (rawClaim) => {
    if (!rawClaim) return null;
    
    // If already unmarshalled (plain objects), return as-is
    if (!rawClaim.claim_id?.S && typeof rawClaim.claim_id === 'string') {
      return rawClaim;
    }

    // Unmarshall the entire claim object
    const unmarshalled = {};
    for (const [key, value] of Object.entries(rawClaim)) {
      unmarshalled[key] = unmarshallValue(value);
    }
    return unmarshalled;
  };

  useEffect(() => {
    if (!claim) {
      loadClaim();
    } else {
      // Unmarshall existing claim data
      setClaim(unmarshallClaim(claim));
    }
  }, []);

  const loadClaim = async () => {
    try {
      const rawData = await getClaim(decodeURIComponent(claimId));
      const data = unmarshallClaim(rawData);
      setClaim(data);
    } catch (err) {
      setError('Failed to load claim details');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !claim) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <p className="text-gray-700">{error || 'Claim not found'}</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const riskAnalysis = claim.risk_analysis || {};
  const medicalEntities = claim.medical_entities || {};
  const patient = medicalEntities.patient || {};

  const getRiskColor = (level) => {
    switch (level) {
      case 'LOW': return 'text-green-600 bg-green-50 border-green-200';
      case 'MEDIUM': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'HIGH': return 'text-red-600 bg-red-50 border-red-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center text-blue-600 hover:text-blue-700 mb-2"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </button>
          <div className="flex items-center">
            <FileText className="w-8 h-8 text-blue-600 mr-3" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Claim Details</h1>
              <p className="text-sm text-gray-500 font-mono break-all">{claimId}</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Risk Score Card */}
          <div className="lg:col-span-3">
            <div className={`bg-white rounded-lg shadow-lg p-6 border-2 ${getRiskColor(riskAnalysis.risk_level)}`}>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold mb-2">Risk Assessment</h2>
                  <p className="text-4xl font-bold">{riskAnalysis.risk_score || 0}/100</p>
                  <p className="text-sm mt-1">Risk Level: <span className="font-bold">{riskAnalysis.risk_level || 'N/A'}</span></p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium mb-1">Recommended Action:</p>
                  <span className="px-4 py-2 rounded-lg font-semibold inline-block">
                    {riskAnalysis.recommended_action || 'PENDING'}
                  </span>
                  <p className="text-xs mt-2">
                    Confidence: {riskAnalysis.confidence_score || 0}%
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Patient Information */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
              <User className="w-5 h-5 mr-2 text-blue-600" />
              Patient Information
            </h3>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-gray-500">Name</dt>
                <dd className="font-semibold text-gray-900">{patient.name || 'N/A'}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Patient ID</dt>
                <dd className="font-mono text-gray-900">{patient.id || 'N/A'}</dd>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <dt className="text-gray-500">Age</dt>
                  <dd className="font-semibold text-gray-900">{patient.age || 'N/A'}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Gender</dt>
                  <dd className="font-semibold text-gray-900">{patient.gender || 'N/A'}</dd>
                </div>
              </div>
            </dl>
          </div>

          {/* Medical Codes */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
              <Stethoscope className="w-5 h-5 mr-2 text-blue-600" />
              Medical Codes
            </h3>
            
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Diagnosis Codes (ICD-10)</h4>
              <div className="flex flex-wrap gap-2">
                {medicalEntities.diagnosis_codes?.length > 0 ? (
                  medicalEntities.diagnosis_codes.map((code, idx) => (
                    <span key={idx} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-mono">
                      {code}
                    </span>
                  ))
                ) : (
                  <span className="text-gray-400 text-xs">No diagnosis codes found</span>
                )}
              </div>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Procedure Codes (CPT)</h4>
              <div className="flex flex-wrap gap-2">
                {medicalEntities.procedure_codes?.length > 0 ? (
                  medicalEntities.procedure_codes.map((code, idx) => (
                    <span key={idx} className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-mono">
                      {code}
                    </span>
                  ))
                ) : (
                  <span className="text-gray-400 text-xs">No procedure codes found</span>
                )}
              </div>
            </div>
          </div>

          {/* Medications & Financial */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
              <Pill className="w-5 h-5 mr-2 text-blue-600" />
              Medications & Financial
            </h3>
            
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Medications</h4>
              <ul className="space-y-1">
                {medicalEntities.medications?.length > 0 ? (
                  medicalEntities.medications.map((med, idx) => (
                    <li key={idx} className="text-sm text-gray-700">• {med}</li>
                  ))
                ) : (
                  <li className="text-sm text-gray-400">No medications found</li>
                )}
              </ul>
            </div>

            <div className="pt-4 border-t border-gray-200">
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Total Claim Amount:</span>
                <span className="text-xl font-bold text-gray-900">
                  {medicalEntities.claim_amount || '$0.00'}
                </span>
              </div>
            </div>

            {medicalEntities.extraction_method && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <p className="text-xs text-gray-500">
                  Extraction method: <span className="font-mono">{medicalEntities.extraction_method}</span>
                </p>
                {medicalEntities.cost?.estimated_usd && (
                  <p className="text-xs text-gray-500">
                    Processing cost: ${medicalEntities.cost.estimated_usd.toFixed(6)}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Risk Breakdown */}
          {riskAnalysis.risk_breakdown && riskAnalysis.risk_breakdown.length > 0 && (
            <div className="lg:col-span-3 bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
                <Activity className="w-5 h-5 mr-2 text-blue-600" />
                Risk Factors Breakdown
              </h3>
              <div className="space-y-3">
                {riskAnalysis.risk_breakdown.map((factor, idx) => (
                  <div key={idx} className="flex items-start p-3 bg-gray-50 rounded-lg">
                    <AlertTriangle className={`w-5 h-5 mr-3 flex-shrink-0 mt-0.5 ${
                      factor.severity === 'HIGH' ? 'text-red-500' :
                      factor.severity === 'MEDIUM' ? 'text-yellow-500' :
                      'text-blue-500'
                    }`} />
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <h4 className="font-semibold text-gray-900">{factor.category}</h4>
                        <span className="text-sm font-bold text-gray-700">+{factor.points} points</span>
                      </div>
                      <p className="text-sm text-gray-600">{factor.details}</p>
                      <span className={`inline-block mt-2 px-2 py-0.5 text-xs rounded ${
                        factor.severity === 'HIGH' ? 'bg-red-100 text-red-700' :
                        factor.severity === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-blue-100 text-blue-700'
                      }`}>
                        {factor.severity}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default ClaimView;
