
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
        <div className="glass-panel p-6 rounded-3xl flex flex-col h-[520px] gradient-ring">
            <h2 className="section-title text-xl font-bold text-slate-800 mb-4 flex items-center">
                <Icon name="chat" className="h-6 w-6 mr-2 text-cyan-700" />
                Ask a Question
            </h2>
            <div className="flex-grow overflow-y-auto mb-4 pr-2 space-y-4 rounded-2xl bg-slate-50/65 border border-slate-200 p-3">
                {messages.map((msg, index) => (
                    <div key={index} className={`flex items-start gap-2.5 ${msg.sender === 'user' ? 'justify-end' : ''}`}>
                        {msg.sender === 'ai' && <div className="flex-shrink-0 h-8 w-8 rounded-full bg-cyan-100 flex items-center justify-center"><Icon name="sparkles" className="h-5 w-5 text-cyan-700"/></div>}
                        <div className={`flex flex-col w-full max-w-[340px] leading-1.5 p-4 border border-slate-200 ${msg.sender === 'user' ? 'bg-gradient-to-r from-cyan-700 via-teal-700 to-emerald-700 rounded-2xl text-white border-cyan-700' : 'bg-white rounded-2xl text-slate-800'}`}>
                            <p className="text-sm font-normal">{msg.text}</p>
                        </div>
                    </div>
                ))}
                {isLoading && (
                     <div className="flex items-start gap-2.5">
                        <div className="flex-shrink-0 h-8 w-8 rounded-full bg-cyan-100 flex items-center justify-center"><Icon name="sparkles" className="h-5 w-5 text-cyan-700"/></div>
                        <div className="flex flex-col w-full max-w-[340px] leading-1.5 p-4 border border-slate-200 bg-white rounded-2xl">
                            <div className="flex items-center space-x-2">
                                <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse"></div>
                                <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse [animation-delay:0.2s]"></div>
                                <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse [animation-delay:0.4s]"></div>
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
                    className="flex-grow p-3 border border-slate-300 rounded-l-xl bg-white focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition duration-150"
                    disabled={isLoading}
                />
                <button
                    onClick={handleSend}
                    disabled={isLoading || !input.trim()}
                    className="bg-gradient-to-r from-cyan-700 via-teal-700 to-emerald-700 text-white font-semibold p-3 rounded-r-xl hover:from-cyan-800 hover:via-teal-800 hover:to-emerald-800 disabled:from-cyan-300 disabled:to-teal-300 disabled:cursor-not-allowed transition duration-150"
                >
                    <Icon name="send" className="h-6 w-6"/>
                </button>
            </div>
        </div>
    );
};
