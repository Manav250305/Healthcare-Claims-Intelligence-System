import { useState } from 'react';
import { Upload, FileText, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import { getUploadUrl, uploadToS3 } from '../../services/api';

const ClaimUpload = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      // Validate file size (10MB max)
      if (selectedFile.size > 10 * 1024 * 1024) {
        setError('File size must be less than 10MB');
        setFile(null);
        return;
      }
      
      // Validate file type
      if (!selectedFile.type.includes('pdf') && !selectedFile.name.endsWith('.pdf')) {
        setError('Please upload a PDF file');
        setFile(null);
        return;
      }
      
      setFile(selectedFile);
      setError('');
      setStatus('');
      setProgress(0);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    setUploading(true);
    setError('');
    setProgress(10);
    setStatus('Requesting upload URL from API...');

    try {
      // Step 1: Get pre-signed URL from API Gateway
      const { uploadUrl, fileKey } = await getUploadUrl(file.name);
      
      setProgress(30);
      setStatus('Uploading document to S3...');
      
      // Step 2: Upload file to S3
      await uploadToS3(uploadUrl, file);
      
      setProgress(70);
      setStatus('Upload complete! Processing claim...');
      
      // Step 3: Notify parent and wait for processing
      if (onUploadSuccess) {
        onUploadSuccess(fileKey);
      }

      setProgress(100);
      setStatus('✅ Claim submitted successfully! Processing will begin shortly.');
      
      // Reset after 3 seconds
      setTimeout(() => {
        setFile(null);
        setStatus('');
        setProgress(0);
        setUploading(false);
        // Reset file input
        const fileInput = document.getElementById('file-upload');
        if (fileInput) fileInput.value = '';
      }, 3000);
      
    } catch (err) {
      console.error('Upload error:', err);
      setError(
        err.response?.data?.error || 
        err.message || 
        'Upload failed. Please try again.'
      );
      setUploading(false);
      setProgress(0);
      setStatus('');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Header */}
      <div className="flex items-center mb-6">
        <FileText className="w-8 h-8 text-blue-600 mr-3" />
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Upload Medical Claim</h2>
          <p className="text-sm text-gray-500">Upload PDF documents for AI-powered analysis</p>
        </div>
      </div>

      {/* File Input Area */}
      <div className="mb-6">
        <label className="block mb-2 text-sm font-medium text-gray-700">
          Select PDF Document
        </label>
        <div className="flex items-center justify-center w-full">
          <label className={`flex flex-col items-center justify-center w-full h-40 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
            file ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-gray-50 hover:bg-gray-100'
          }`}>
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
              {file ? (
                <>
                  <FileText className="w-12 h-12 mb-3 text-blue-500" />
                  <p className="mb-2 text-sm text-gray-700 font-semibold">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </>
              ) : (
                <>
                  <Upload className="w-12 h-12 mb-3 text-gray-400" />
                  <p className="mb-2 text-sm text-gray-500">
                    <span className="font-semibold">Click to upload</span> or drag and drop
                  </p>
                  <p className="text-xs text-gray-500">PDF files only (MAX. 10MB)</p>
                </>
              )}
            </div>
            <input
              id="file-upload"
              type="file"
              className="hidden"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              disabled={uploading}
            />
          </label>
        </div>
      </div>

      {/* Progress Bar */}
      {uploading && progress > 0 && (
        <div className="mb-4">
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* Status Messages */}
      {status && (
        <div className={`mb-4 p-4 rounded-lg flex items-center ${
          status.includes('✅') 
            ? 'bg-green-50 border border-green-200' 
            : 'bg-blue-50 border border-blue-200'
        }`}>
          {uploading ? (
            <Loader className="w-5 h-5 text-blue-600 mr-3 animate-spin" />
          ) : (
            <CheckCircle className="w-5 h-5 text-green-600 mr-3" />
          )}
          <p className={status.includes('✅') ? 'text-green-800' : 'text-blue-800'}>
            {status}
          </p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center">
          <AlertCircle className="w-5 h-5 text-red-600 mr-3 flex-shrink-0" />
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Upload Button */}
      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className={`w-full py-3 px-4 rounded-lg font-medium text-white transition-all ${
          !file || uploading
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700 hover:shadow-lg'
        }`}
      >
        {uploading ? (
          <span className="flex items-center justify-center">
            <Loader className="w-5 h-5 mr-2 animate-spin" />
            Uploading...
          </span>
        ) : (
          'Upload and Process Claim'
        )}
      </button>

      {/* Info Box */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">Processing includes:</h4>
        <ul className="text-xs text-gray-600 space-y-1">
          <li>• Text extraction from PDF</li>
          <li>• Medical entity recognition (ICD-10, CPT codes)</li>
          <li>• Patient information extraction</li>
          <li>• Risk score calculation</li>
          <li>• AI-powered fraud detection</li>
        </ul>
      </div>
    </div>
  );
};

export default ClaimUpload;
