"use client"

import * as React from 'react'
import { useState, useCallback, useRef, useEffect } from 'react'
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import { ScrollArea } from "./ui/scroll-area"
import { SendIcon, Loader2Icon, SunIcon, MoonIcon } from 'lucide-react'
import MessageComponent from './MessageComponent'


interface Message {
  role: 'user' | 'bot';
  content: string;
  id?: number;
}

interface ChatSession {
  sessionId: string | null;
}

const staticSuggestedQuestions = [
  "What is DAO PropTech?",
  "How does real estate tokenization work?",
  "What are the benefits of investing through DAO PropTech?",
  "Give me an overview of the projects undertaken by DAO PropTech"
];

const useTheme = () => {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('theme') === 'dark'
    }
    return false
  })

  const toggleTheme = useCallback(() => {
    const newTheme = !isDarkMode
    setIsDarkMode(newTheme)
    localStorage.setItem('theme', newTheme ? 'dark' : 'light')
    if (newTheme) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDarkMode])

  React.useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDarkMode])

  return { isDarkMode, toggleTheme }
}

const useChatbot = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [botState, setBotState] = useState<'idle' | 'thinking' | 'streaming' | 'rate-limited' | 'error'>('idle');
  const [streamingMessage, setStreamingMessage] = useState('');
  const [session, setSession] = useState<ChatSession>({ sessionId: null });
  const [showFeedback, setShowFeedback] = useState(false);
  const [errorDetails, setErrorDetails] = useState<{
    type: 'rate_limit' | 'server_error' | 'quota_exceeded' | 'timeout' | 'unknown';
    message: string;
    retryAfter?: number;
  } | null>(null);

  useEffect(() => {
    if (messages.length === 10) {
      setShowFeedback(true);
    }
  }, [messages]);

  const initializeSession = useCallback(async () => {
    try {
      const response = await fetch('/api/session', {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error('Failed to create session');
      }
      
      const data = await response.json();
      setSession({ sessionId: data.session_id });
    } catch (error) {
      console.error('Error creating session:', error);
      // Retry after 2 seconds
      setTimeout(initializeSession, 2000);
    }
  }, []);

  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  const handleSendMessage = useCallback(async (message: string) => {
    if (message.trim() === '' || botState !== 'idle' || !session.sessionId) return;

    const newUserMessage: Message = { role: 'user', content: message.trim() };
    setMessages(prev => [...prev, newUserMessage]);
    setInput('');
    setBotState('thinking');
    setStreamingMessage('');
    setErrorDetails(null);

    try {
      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': session.sessionId
        },
        body: JSON.stringify({ text: message }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          await initializeSession();
          throw new Error('Session expired. Please try again.');
        }
        
        const errorData = await response.json();
        
        if (response.status === 429) {
          const retryAfter = parseInt(response.headers.get('Retry-After') || '300');
          setErrorDetails({
            type: 'rate_limit',
            message: errorData.error?.message || 'Rate limit exceeded. Please try again later.',
            retryAfter
          });
          setBotState('rate-limited');
          setTimeout(() => {
            setBotState('idle');
            setErrorDetails(null);
          }, retryAfter * 1000);
          return;
        }
        
        if (response.status === 503) {
          setErrorDetails({
            type: 'server_error',
            message: 'Server is currently overloaded. Please try again in a few minutes.'
          });
          setBotState('error');
          return;
        }
        
        throw new Error(errorData.error?.message || 'An error occurred');
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader available');

      const decoder = new TextDecoder();
      let accumulatedMessage = '';
      let messageId: number | undefined;

      setBotState('streaming');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.token) {
                accumulatedMessage += data.token;
                setStreamingMessage(accumulatedMessage);
              } else if (data.message_id) {
                messageId = data.message_id;
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }

      const botMessage: Message = { 
        role: 'bot', 
        content: accumulatedMessage,
        id: messageId
      };
      setMessages(prev => [...prev, botMessage]);
      setBotState('idle');
      setStreamingMessage('');
      
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = error instanceof Error ? error.message : 'An error occurred';
      const errorBotMessage: Message = { 
        role: 'bot', 
        content: `I apologize, but I encountered an issue: ${errorMessage}`
      };
      setMessages(prev => [...prev, errorBotMessage]);
      setBotState('idle');
    }
  }, [botState, session.sessionId, initializeSession]);

  const cleanup = useCallback(async () => {
    if (session.sessionId) {
      try {
        await fetch(`/api/session/${session.sessionId}`, {
          method: 'DELETE',
        });
      } catch (error) {
        console.error('Error cleaning up session:', error);
      }
    }
  }, [session.sessionId]);

  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  const handleFeedbackSubmit = async (rating: number, feedbackText: string, email: string) => {
    if (!session.sessionId) return;
    
    try {
      await fetch(`/api/session/${session.sessionId}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          rating,
          feedback_text: feedbackText,
          email,
        }),
      });
      setShowFeedback(false);
    } catch (error) {
      console.error('Error submitting feedback:', error);
    }
  };

  return {
    messages,
    input,
    setInput,
    botState,
    streamingMessage,
    handleSendMessage,
    sessionReady: !!session.sessionId,
    errorDetails,
    handleFeedbackSubmit,
    showFeedback,
    setShowFeedback
  };
}

const GeometricShapes = () => (
  <div className="absolute inset-0 overflow-hidden pointer-events-none">
    <div className="absolute top-10 left-10 w-20 h-20 bg-blue-500 opacity-20 transform rotate-45"></div>
    <div className="absolute bottom-20 right-20 w-32 h-32 bg-teal-500 opacity-20 rounded-lg transform -rotate-12"></div>
    <div className="absolute top-1/3 right-1/4 w-16 h-16 bg-indigo-500 opacity-20 transform rotate-12"></div>
    <div className="absolute bottom-1/4 left-1/3 w-24 h-24 bg-purple-500 opacity-20 rounded-full"></div>
  </div>
)

const ThinkingIndicator = ({ 
  state, 
  isDarkMode 
}: { 
  state: 'thinking' | 'streaming' | 'idle' | 'error' | 'rate-limited', 
  isDarkMode: boolean 
}) => {
  if (state === 'idle' || state === 'error' || state === 'rate-limited' || state === 'streaming') return null;

  return (
    <div className="flex items-center space-x-2 mb-4">
      <div className="w-6 h-6 mr-2">
        <img 
          src="/emblem.svg" 
          alt="DAO PropTech Emblem" 
          className={`w-full h-full ${isDarkMode ? 'invert' : ''}`}
        />
      </div>
      <div className="flex items-center space-x-2 text-gray-400">
        <span className="text-sm">Thinking</span>
        <span className="flex space-x-1">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
        </span>
      </div>
    </div>
  );
};

// Add custom scrollbar styles at the top of the file
const scrollbarStyles = `
  .custom-scrollbar::-webkit-scrollbar {
    width: 8px;
  }

  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }

  .custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: rgba(155, 155, 155, 0.5);
    border-radius: 20px;
    border: transparent;
  }
`;

const ErrorMessage = ({ error, isDarkMode }: { 
  error: { type: string; message: string; retryAfter?: number; } | null;
  isDarkMode: boolean;
}) => {
  if (!error) return null;

  const getErrorStyle = () => {
    switch (error.type) {
      case 'rate_limit':
        return isDarkMode ? 'bg-red-900/90' : 'bg-red-50';
      case 'server_error':
        return isDarkMode ? 'bg-orange-900/90' : 'bg-orange-50';
      default:
        return isDarkMode ? 'bg-gray-800/90' : 'bg-gray-50';
    }
  };

  return (
    <div className={`fixed inset-x-0 top-16 z-50 p-4 ${getErrorStyle()}`}>
      <div className="max-w-3xl mx-auto flex items-center justify-between">
        <div className={isDarkMode ? 'text-white' : 'text-gray-800'}>
          <p className="font-semibold">{error.message}</p>
          {error.retryAfter && (
            <p className="text-sm">Available again in {Math.ceil(error.retryAfter / 60)} minutes</p>
          )}
        </div>
      </div>
    </div>
  );
};

interface FeedbackModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (rating: number, feedback: string, email: string) => void;
}

const FeedbackModal: React.FC<FeedbackModalProps> = ({ isOpen, onClose, onSubmit }) => {
    const [rating, setRating] = useState<number>(0);
    const [feedback, setFeedback] = useState('');
    const [email, setEmail] = useState('');

    if (!isOpen) return null;

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <h2>How was your experience?</h2>
                <div className="rating-container">
                    {[1, 2, 3, 4, 5].map((value) => (
                        <button
                            key={value}
                            onClick={() => setRating(value)}
                            className={`rating-btn ${rating === value ? 'active' : ''}`}
                        >
                            {/* You can use emoji or custom smiley icons here */}
                            {value <= rating ? '😊' : '😐'}
                        </button>
                    ))}
                </div>
                <textarea
                    placeholder="Your feedback (optional)"
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                />
                <input
                    type="email"
                    placeholder="Your email (optional)"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                />
                <div className="modal-buttons">
                    <button onClick={() => onSubmit(rating, feedback, email)}>Submit</button>
                    <button onClick={onClose}>Skip</button>
                </div>
            </div>
        </div>
    );
};

export default function ChatbotPage() {
  const { isDarkMode, toggleTheme } = useTheme()
  const { 
    messages, 
    input, 
    setInput, 
    botState, 
    streamingMessage, 
    handleSendMessage,
    sessionReady,
    errorDetails,
    handleFeedbackSubmit,
    showFeedback,
    setShowFeedback
  } = useChatbot()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollArea = scrollAreaRef.current
      scrollArea.scrollTop = scrollArea.scrollHeight
    }
  }, [messages, streamingMessage, botState])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value)
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && botState !== 'thinking' && input.trim()) {
      handleSendMessage(input)
    }
  }

  return (
    <div className={`flex flex-col min-h-[100dvh] ${isDarkMode ? 'bg-gray-900 text-white' : 'bg-white text-black'}`}>
      {/* Add style tag for scrollbar */}
      <style>{scrollbarStyles}</style>
      
      <header className={`${isDarkMode ? 'bg-gray-900' : 'bg-white'} backdrop-blur-sm p-4 font-bold flex items-center justify-between sticky top-0 z-50`}>
        <div className="flex items-center">
          <img 
            src="/emblem.svg" 
            alt="DAO PropTech Emblem" 
            className={`w-6 h-6 mr-2 ${isDarkMode ? 'invert' : ''}`}
          />
          <span className="text-xl">DAO Chat</span> <span className="text-xs">(Beta)</span>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={toggleTheme} 
          className={`transition-colors ${isDarkMode ? 'bg-gray-800/10 hover:bg-gray-700/20 border-gray-700/40 hover:border-gray-600 text-white' : 'bg-white/10 hover:bg-white/20 border-gray-200/40 hover:border-gray-300 text-black'}`}
        >
          {isDarkMode ? <SunIcon className="h-4 w-4 text-white" /> : <MoonIcon className="h-4 w-4 text-black" />}
        </Button>
      </header>
      <ErrorMessage error={errorDetails} isDarkMode={isDarkMode} />

      <main className="flex-1 flex flex-col overflow-hidden relative pb-[env(safe-area-inset-bottom)]">
        {messages.length === 0 && <GeometricShapes />}
        
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center px-4 py-8">
            <img 
              src="/emblem.svg" 
              alt="DAO PropTech Emblem" 
              className={`w-24 h-24 mb-8 ${
                isDarkMode ? 'invert' : ''
              }`}
            />
            <h2 className={`text-2xl font-semibold text-center mb-8 ${
              isDarkMode ? 'text-white' : 'text-gray-800'
            }`}>
              How can I assist you with real estate investments today?
            </h2>
            <div className="w-full max-w-md space-y-4">
              {staticSuggestedQuestions.map((question, index) => (
                <Button
                  key={index}
                  variant="outline"
                  onClick={() => handleSendMessage(question)}
                  className={`w-full text-left justify-start h-auto whitespace-normal ${
                    isDarkMode ? 'bg-gray-800 hover:bg-gray-700 text-white' : 'bg-white hover:bg-gray-100 text-gray-800'
                  }`}
                >
                  {question}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <ScrollArea 
            className="flex-1 custom-scrollbar overflow-y-auto" 
            ref={scrollAreaRef}
            scrollHideDelay={0}
          >
            <div className="px-4 py-1 max-w-3xl mx-auto">
              {messages.map((message, index) => (
                <MessageComponent
                  key={index}
                  message={message}
                  isDarkMode={isDarkMode}
                  isStreaming={false}
                />
              ))}
              <div className={`transition-opacity duration-300 ${botState !== 'idle' ? 'opacity-100' : 'opacity-0'}`}>
                <ThinkingIndicator state={botState} isDarkMode={isDarkMode} />
              </div>
              {botState === 'streaming' && (
                <MessageComponent
                  message={{ role: 'bot', content: streamingMessage }}
                  isDarkMode={isDarkMode}
                  isStreaming={true}
                />
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
        )}

        <div className="sticky bottom-0 z-50">
          <div className="p-4 bg-gradient-to-t from-inherit via-inherit to-transparent">
            <div className={`flex space-x-2 w-full max-w-2xl mx-auto rounded-full shadow-lg ${
              isDarkMode ? 'bg-gray-800' : 'bg-white'
            }`}>
              <Input
                value={input}
                onChange={handleInputChange}
                onKeyPress={handleKeyPress}
                placeholder={!sessionReady ? "Initializing chat..." : messages.length === 0 ? "Ask me anything about real estate investments..." : "Type your message..."}
                className={`flex-grow rounded-l-full border-0 focus:ring-0 ${
                  isDarkMode ? 'bg-gray-800 text-white placeholder-gray-400' : 'bg-white text-gray-800 placeholder-gray-500'
                }`}
                disabled={botState !== 'idle' || !sessionReady}
              />
              <Button
                onClick={() => handleSendMessage(input)}
                className={`rounded-r-full ${
                  botState !== 'idle' || !sessionReady ? 'bg-gray-500' : 'bg-[#ADFF2F] hover:bg-[#9ACD32]'
                } text-black`}
                disabled={botState !== 'idle' || !input.trim() || !sessionReady}
              >
                {botState !== 'idle' ? <Loader2Icon className="w-4 h-4 animate-spin" /> : <SendIcon className="w-4 h-4" />}
              </Button>
            </div>
          </div>
          <div className={`text-center text-xs pb-1 ${
            isDarkMode ? 'text-gray-400' : 'text-gray-500'
          }`}>
            DAO Chat may make mistakes. Use with discretion.
          </div>
        </div>
      </main>
      <FeedbackModal
        isOpen={showFeedback}
        onClose={() => setShowFeedback(false)}
        onSubmit={handleFeedbackSubmit}
      />
    </div>
  )
}
