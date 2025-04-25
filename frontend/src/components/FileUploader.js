import React, { useState } from 'react';
import { uploadFile } from '../api';

const FileUploader = ({ conversationHistory, onUploadComplete }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    try {
      const { extracted_text, ai_response } = await uploadFile(file, conversationHistory);
      onUploadComplete(extracted_text, ai_response);
      setFile(null);
    } catch (error) {
      console.error('Error uploading file:', error);
      alert('Failed to upload file. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="file-uploader">
      <h3>Upload a Legal Document</h3>
      <form onSubmit={handleSubmit}>
        <input
          type="file"
          onChange={handleFileChange}
          accept=".txt,.pdf,.docx"
          disabled={uploading}
        />
        <button type="submit" disabled={!file || uploading}>
          {uploading ? 'Analyzing...' : 'Send to Chatbot'}
        </button>
      </form>
    </div>
  );
};

export default FileUploader;