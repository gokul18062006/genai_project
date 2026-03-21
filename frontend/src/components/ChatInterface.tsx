
import React, { useState, useRef, useEffect } from 'react';
import type { ChatMessage } from '../types';
import { Icon } from './Icon';

interface ChatInterfaceProps {
    messages: ChatMessage[];
    onSendMessage: (message: string) => void;
    isLoading: boolean;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ messages, onSendMessage, isLoading }) => {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<null | HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    const handleSend = () => {
        if (input.trim()) {
            onSendMessage(input);
            setInput('');
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' && !isLoading) {
            handleSend();
        }
    }

    return (
        <div className="bg-white p-6 rounded-lg shadow-md border border-slate-200 flex flex-col h-[500px]">
            <h2 className="text-xl font-bold text-slate-700 mb-4 flex items-center">
                <Icon name="chat" className="h-6 w-6 mr-2 text-indigo-500" />
                Ask a Question
            </h2>
            <div className="flex-grow overflow-y-auto mb-4 pr-2 space-y-4">
                {messages.map((msg, index) => (
                    <div key={index} className={`flex items-start gap-2.5 ${msg.sender === 'user' ? 'justify-end' : ''}`}>
                        {msg.sender === 'ai' && <div className="flex-shrink-0 h-8 w-8 rounded-full bg-indigo-100 flex items-center justify-center"><Icon name="sparkles" className="h-5 w-5 text-indigo-600"/></div>}
                        <div className={`flex flex-col w-full max-w-[320px] leading-1.5 p-4 border-slate-200 ${msg.sender === 'user' ? 'bg-indigo-500 rounded-s-xl rounded-se-xl text-white' : 'bg-slate-100 rounded-e-xl rounded-es-xl text-slate-800'}`}>
                            <p className="text-sm font-normal">{msg.text}</p>
                        </div>
                    </div>
                ))}
                {isLoading && (
                     <div className="flex items-start gap-2.5">
                        <div className="flex-shrink-0 h-8 w-8 rounded-full bg-indigo-100 flex items-center justify-center"><Icon name="sparkles" className="h-5 w-5 text-indigo-600"/></div>
                        <div className="flex flex-col w-full max-w-[320px] leading-1.5 p-4 border-slate-200 bg-slate-100 rounded-e-xl rounded-es-xl">
                            <div className="flex items-center space-x-2">
                                <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></div>
                                <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse [animation-delay:0.2s]"></div>
                                <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse [animation-delay:0.4s]"></div>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>
            <div className="flex items-center">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="e.g., What is the penalty clause?"
                    className="flex-grow p-3 border border-slate-300 rounded-l-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition duration-150"
                    disabled={isLoading}
                />
                <button
                    onClick={handleSend}
                    disabled={isLoading || !input.trim()}
                    className="bg-indigo-600 text-white font-semibold p-3 rounded-r-md hover:bg-indigo-700 disabled:bg-indigo-300 disabled:cursor-not-allowed transition duration-150"
                >
                    <Icon name="send" className="h-6 w-6"/>
                </button>
            </div>
        </div>
    );
};
