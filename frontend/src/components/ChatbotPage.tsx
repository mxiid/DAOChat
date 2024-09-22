import * as React from 'react'
import { useState, useEffect, useCallback } from 'react'
import { Button } from "./ui/button.tsx"
import { Input } from "./ui/input.tsx"
import { ScrollArea } from "./ui/scroll-area.tsx"
import { SendIcon, BotIcon, UserIcon, Loader2Icon } from 'lucide-react'

interface Message {
  role: 'user' | 'bot';
  content: string;
}

export default function ChatbotPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'bot', content: 'Hello! How can I assist you with real estate investments today?' }
  ])
  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([
    "How do I start investing?",
    "What are the benefits of digital real estate investment?",
    "How is my investment secured?",
    "Can you explain value-based pricing?"
  ])

  const handleSend = useCallback(async () => {
    if (input.trim() && !isThinking) {
      const newUserMessage: Message = { role: 'user', content: input.trim() };
      setMessages(prev => [...prev, newUserMessage]);
      setInput('');
      setIsThinking(true);

      try {
        const response = await fetch('http://localhost:8000/ask', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ text: input.trim() }),
        })
        const data = await response.json()
        const newBotMessage: Message = { role: 'bot', content: data.answer };
        setMessages(prev => [...prev, newBotMessage]);
        generateSuggestedQuestions(data.answer)
      } catch (error) {
        console.error('Error:', error)
        const errorMessage: Message = { role: 'bot', content: 'Sorry, an error occurred. Please try again.' };
        setMessages(prev => [...prev, errorMessage]);
      } finally {
        setIsThinking(false);
      }
    }
  }, [input, isThinking])

  const generateSuggestedQuestions = async (lastAnswer: string) => {
    try {
      const response = await fetch('http://localhost:8000/suggest_questions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ context: lastAnswer }),
      })
      const data = await response.json()
      setSuggestedQuestions(data.questions || [])
    } catch (error) {
      console.error('Error generating suggested questions:', error)
      setSuggestedQuestions([])
    }
  }

  const handleSuggestedQuestion = async (question: string) => {
    if (!isThinking) {
      setInput(question)
      await handleSend()
    }
  }

  useEffect(() => {
    console.log('Current messages:', messages); // Debug log
  }, [messages]);

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-[#0066FF] to-[#00FFFF] p-4 text-white font-bold flex items-center justify-between">
        <div className="flex items-center">
          <BotIcon className="mr-2" />
          DAO PropTech Assistant
        </div>
        <Button variant="outline" className="text-white border-white hover:bg-white/20">
          Sign Up
        </Button>
      </div>

      {/* Main Chat Area */}
      <ScrollArea className="flex-grow p-4">
        {messages.map((message, index) => (
          <div key={index} className={`flex items-start mb-4 ${message.role === 'user' ? 'justify-end' : ''}`}>
            {message.role === 'bot' && <BotIcon className="w-6 h-6 mr-2 text-[#0066FF]" />}
            <div className={`rounded-lg p-3 max-w-[70%] ${
              message.role === 'user' ? 'bg-[#ADFF2F] text-black' : 'bg-white border border-gray-200'
            }`}>
              {message.content}
            </div>
            {message.role === 'user' && <UserIcon className="w-6 h-6 ml-2 text-[#ADFF2F]" />}
          </div>
        ))}
        {isThinking && (
          <div className="flex items-center mb-4">
            <BotIcon className="w-6 h-6 mr-2 text-[#0066FF]" />
            <div className="bg-white border border-gray-200 rounded-lg p-3">
              <Loader2Icon className="w-4 h-4 animate-spin text-[#0066FF]" />
            </div>
          </div>
        )}
      </ScrollArea>

      {/* Input Area */}
      <div className="p-4 bg-white border-t border-gray-200">
        <div className="flex flex-wrap gap-2 mb-4">
          {suggestedQuestions.map((question, index) => (
            <Button
              key={index}
              variant="outline"
              size="sm"
              onClick={() => handleSuggestedQuestion(question)}
              className="text-xs bg-white hover:bg-[#ADFF2F] hover:text-black transition-colors"
              disabled={isThinking}
            >
              {question}
            </Button>
          ))}
        </div>
        <div className="flex space-x-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            className="flex-grow"
            disabled={isThinking}
          />
          <Button 
            onClick={handleSend} 
            className={`${isThinking ? 'bg-gray-300' : 'bg-[#ADFF2F] hover:bg-[#9ACD32]'} text-black`}
            disabled={isThinking}
          >
            {isThinking ? <Loader2Icon className="w-4 h-4 animate-spin" /> : <SendIcon className="w-4 h-4" />}
          </Button>
        </div>
      </div>
    </div>
  )
}
