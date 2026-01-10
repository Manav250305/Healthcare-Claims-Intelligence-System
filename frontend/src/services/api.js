import axios from 'axios';
import { getIdToken } from './auth';

const API_BASE = import.meta.env.VITE_API_ENDPOINT;

// Helper to get auth headers
const getAuthHeaders = async () => {
  try {
    const token = await getIdToken();
    return {
      'Authorization': token,
      'Content-Type': 'application/json'
    };
  } catch (err) {
    throw new Error('Not authenticated');
  }
};

// Get pre-signed upload URL
export const getUploadUrl = async (filename) => {
  try {
    const headers = await getAuthHeaders();
    const response = await axios.get(`${API_BASE}/upload-url`, {
      params: { filename },
      headers
    });
    return response.data;
  } catch (error) {
    console.error('Error getting upload URL:', error);
    throw error;
  }
};

// Upload file to S3
export const uploadToS3 = async (uploadUrl, file) => {
  try {
    await axios.put(uploadUrl, file, {
      headers: {
        'Content-Type': file.type
      }
    });
  } catch (error) {
    console.error('Error uploading to S3:', error);
    throw error;
  }
};

// Get claim results - single encode the claim ID
export const getClaim = async (claimId) => {
  try {
    const headers = await getAuthHeaders();
    
    // Use single encoding - let axios handle URL encoding
    const encodedClaimId = encodeURIComponent(claimId);
    
    console.log('Fetching claim:', claimId);
    console.log('Encoded as:', encodedClaimId);
    
    const response = await axios.get(
      `${API_BASE}/claim/${encodedClaimId}`,
      { headers }
    );
    return response.data;
  } catch (error) {
    console.error('Error fetching claim:', error);
    throw error;
  }
};

// Poll claim status (keep checking until processing complete)
export const pollClaimStatus = async (claimId, maxAttempts = 30, interval = 2000) => {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const claim = await getClaim(claimId);
      
      if (claim.processing_complete || claim.status === 'SCORING_COMPLETE') {
        return claim;
      }
      
      // Wait before next attempt
      await new Promise(resolve => setTimeout(resolve, interval));
    } catch (error) {
      if (error.response?.status === 404 && i < maxAttempts - 1) {
        // Claim not yet created in DB, keep polling
        await new Promise(resolve => setTimeout(resolve, interval));
        continue;
      }
      throw error;
    }
  }
  
  throw new Error('Claim processing timeout');
};
