import React from 'react';
import { Icon } from './Icon';

export const Header: React.FC = () => {
    return (
        <header className="bg-white/80 backdrop-blur-xl border-b border-slate-200 sticky top-0 z-20 shadow-[0_8px_30px_-20px_rgba(2,6,23,0.45)]">
            <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between min-h-16 py-3 gap-3">
                    <div className="flex items-center space-x-3">
                        <div className="h-11 w-11 rounded-2xl bg-gradient-to-br from-cyan-100 via-teal-50 to-amber-50 flex items-center justify-center border border-cyan-200 shadow-sm">
                            <Icon name="logo" className="h-6 w-6 text-cyan-700" />
                        </div>
                        <div>
                            <h1 className="section-title text-xl sm:text-2xl font-extrabold text-slate-900 leading-tight tracking-tight">
                                <span className="bg-gradient-to-r from-cyan-800 via-slate-800 to-amber-700 bg-clip-text text-transparent">
                                    LegalEase AI
                                </span>
                            </h1>
                            <p className="text-xs sm:text-sm text-slate-600">Analyze, simplify, and ask questions about legal documents</p>
                        </div>
                    </div>
                    <div className="hidden md:flex items-center gap-2">
                        <span className="rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-800">Risk Detection</span>
                        <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">Plain Language</span>
                    </div>
                </div>
            </div>
        </header>
    );
};