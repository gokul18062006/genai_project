import React from 'react';
import { Icon } from './Icon';

export const Header: React.FC = () => {
    return (
        <header className="bg-white/95 backdrop-blur border-b border-slate-200 sticky top-0 z-20">
            <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between min-h-16 py-3">
                    <div className="flex items-center space-x-3">
                        <div className="h-10 w-10 rounded-xl bg-indigo-100 flex items-center justify-center border border-indigo-200">
                            <Icon name="logo" className="h-6 w-6 text-indigo-600" />
                        </div>
                        <div>
                            <h1 className="text-xl sm:text-2xl font-bold text-slate-800 leading-tight">
                                <span className="bg-gradient-to-r from-indigo-600 to-blue-500 bg-clip-text text-transparent">
                                    LegalEase AI
                                </span>
                            </h1>
                            <p className="text-xs sm:text-sm text-slate-500">Analyze, simplify, and ask questions about legal documents</p>
                        </div>
                    </div>
                    <div className="hidden md:flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-emerald-700 text-sm font-medium">
                        <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                        AI ready
                    </div>
                </div>
            </div>
        </header>
    );
};