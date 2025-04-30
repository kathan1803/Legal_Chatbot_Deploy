// const API_URL = 'http://localhost:5000/api';

export const sendMessage = async (conversationHistory) => {
  const response = await fetch('https://legal-chatbot-deploy-knhy.onrender.com/api/chat', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ conversation_history: conversationHistory }),
  });
  
  if (!response.ok) {
    throw new Error('Failed to get response from API');
  }
  
  return response.json();
};

export const uploadFile = async (file, conversationHistory) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('conversation_history', JSON.stringify(conversationHistory));
  
  const response = await fetch('https://legal-chatbot-deploy-knhy.onrender.com/api/upload', {
    method: 'POST',
    credentials: 'include',
    body: formData,
  });
  
  if (!response.ok) {
    throw new Error('Failed to upload file');
  }
  
  return response.json();
};