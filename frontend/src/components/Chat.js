import React, { useState, useEffect, useRef } from 'react';
import { sendMessage } from '../api';
import FileUploader from './FileUploader';

const Chat = () => {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your AI Assistant. How can I help you today?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatContainerRef = useRef(null);

  useEffect(() => {
    // Scroll to bottom when messages change
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Function to detect if content should be formatted as an email
  const detectEmailFormat = (content) => {
    // Simple detection: looks for common email headers
    const emailPatterns = [
      /from:.*\n.*to:/i,
      /subject:.*\n/i,
      /^(to|from|cc|subject|date):.*\n/i
    ];
    
    return emailPatterns.some(pattern => pattern.test(content));
  };

  // Function to format emails
  const formatEmailContent = (content) => {
    // First, identify the header section and the body
    const lines = content.split('\n');
    const headerLines = [];
    const bodyLines = [];
    let isInHeader = true;
    
    // Process each line
    for (const line of lines) {
      // Check if we're still in the header section
      if (isInHeader) {
        // Empty line marks the end of headers
        if (line.trim() === '') {
          isInHeader = false;
          continue;
        }
        
        // Check if this looks like a header field
        if (/^(to|from|cc|bcc|subject|date):/i.test(line)) {
          headerLines.push(line);
        } else {
          // If not a header field, we're in the body
          isInHeader = false;
          bodyLines.push(line);
        }
      } else {
        bodyLines.push(line);
      }
    }
    
    // Format the headers nicely
    const formattedHeaders = headerLines.map(header => {
      const [field, value] = header.split(/:\s*/, 2);
      return (
        <div className="email-field" key={field}>
          <strong>{field.charAt(0).toUpperCase() + field.slice(1)}:</strong> {value}
        </div>
      );
    });
    
    // Join the body lines back together
    const body = bodyLines.join('\n');
    
    return (
      <div className="email-format">
        <div className="email-header">
          {formattedHeaders}
        </div>
        <div className="email-body">{body}</div>
      </div>
    );
  };

  // Function to render message content with appropriate formatting
  const renderMessageContent = (content) => {
    if (detectEmailFormat(content)) {
      return formatEmailContent(content);
    }
    
    // For other structured text that should preserve whitespace
    return <div className="formatted-content">{content}</div>;
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages([...messages, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const updatedHistory = [...messages, userMessage];
      const { response } = await sendMessage(updatedHistory);
      
      setMessages([
        ...updatedHistory,
        { role: 'assistant', content: response }
      ]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages([
        ...messages,
        userMessage,
        { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUploadResponse = (extractedText, aiResponse) => {
    setMessages([
      ...messages,
      { role: 'user', content: extractedText },
      { role: 'assistant', content: aiResponse }
    ]);
  };

  return (
    <div className="chat-container">
      <div className="chat-messages" ref={chatContainerRef}>
        {messages.map((message, index) => (
          <div
            key={index}
            className={`message ${message.role === 'user' ? 'user-message' : 'ai-message'}`}
          >
            <div className="message-content">
              <span className="message-role">{message.role === 'user' ? 'You' : 'AI Assistant'}</span>
              {message.role === 'assistant' 
                ? renderMessageContent(message.content)
                : <div>{message.content}</div>
              }
            </div>
          </div>
        ))}
        {loading && (
          <div className="message ai-message thinking-message">
            <div className="message-content">
              <span className="message-role">AI Assistant</span>
              <div className="thinking-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <form className="chat-input-form" onSubmit={handleSendMessage}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message and press Enter..."
          disabled={loading}
        />
        <button type="submit" disabled={loading}>Send</button>
      </form>
      
      <FileUploader 
        conversationHistory={messages}
        onUploadComplete={handleFileUploadResponse}
      />
    </div>
  );
};

export default Chat;