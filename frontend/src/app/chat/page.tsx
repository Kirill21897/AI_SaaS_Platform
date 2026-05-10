'use client';

import { useState, useRef, useEffect } from 'react';
import { AppHeader } from '@/components/app-header';

export default function ChatPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';
  const [messages, setMessages] = useState<{role: 'user' | 'assistant', content: string}[]>([
    { role: 'assistant', content: 'Привет! Я твой AI-ассистент. Чем могу помочь с выбором образовательного трека или карьеры?' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsLoading(true);

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${apiUrl}/chat/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message: userMsg })
      });

      if (response.status === 401 || response.status === 403) {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Пожалуйста, войдите в систему, чтобы использовать чат.' }]);
        setIsLoading(false);
        return;
      }

      if (!response.ok) throw new Error('Network response was not ok');

      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        let accumulatedMessage = '';
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value);
          accumulatedMessage += chunk;
          
          setMessages(prev => {
            const newMessages = [...prev];
            // Update the last message completely instead of appending to avoid React strict mode / render double appending
            newMessages[newMessages.length - 1].content = accumulatedMessage;
            return newMessages;
          });
        }
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Ой, произошла ошибка подключения к серверу.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Simple parser to extract and render <TRACK_CARD id="X" /> tags
  const renderMessageContent = (content: string) => {
    const parts = content.split(/(<TRACK_CARD id="\d+" \/>)/);
    
    return parts.map((part, index) => {
      const match = part.match(/<TRACK_CARD id="(\d+)" \/>/);
      if (match) {
        const trackId = match[1];
        // В реальном проекте здесь будет компонент карточки, который запрашивает данные по id
        return (
          <div key={index} className="my-3 p-4 bg-gray-50 border border-gray-200 rounded-lg shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-blue-600 bg-blue-100 px-2 py-1 rounded uppercase tracking-wider">Рекомендация</span>
              <span className="text-xs text-gray-500">ID: {trackId}</span>
            </div>
            <h3 className="font-semibold text-lg text-gray-800">Посмотреть трек #{trackId}</h3>
            <button className="mt-2 text-sm bg-white border border-gray-300 px-4 py-1.5 rounded hover:bg-gray-50 transition-colors">
              Открыть подробности
            </button>
          </div>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="flex h-screen flex-col">
      <AppHeader />
      
      <main className="mx-auto w-full max-w-6xl flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[70%] rounded-lg p-4 whitespace-pre-wrap ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white shadow text-gray-800 border'}`}>
              {msg.role === 'assistant' ? renderMessageContent(msg.content) : msg.content}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </main>

      <footer className="border-t bg-white p-4">
        <form onSubmit={sendMessage} className="mx-auto flex max-w-6xl gap-4">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Напишите сообщение..."
            className="flex-1 rounded-full border border-gray-300 shadow-sm px-6 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-blue-600 text-white px-8 py-3 rounded-full hover:bg-blue-700 disabled:opacity-50 transition"
          >
            Отправить
          </button>
        </form>
      </footer>
    </div>
  );
}
