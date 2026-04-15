import React from 'react';
import { Icon } from './Icon';

export const Header: React.FC = () => {
    return (
        <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
            <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between min-h-16 py-3 gap-3">
                    <div className="flex items-center space-x-3">
                        <div className="h-11 w-11 rounded-xl bg-slate-100 flex items-center justify-center border border-slate-200">
                            <Icon name="logo" className="h-6 w-6 text-slate-700" />
                        </div>
                        <div>
                            <h1 className="section-title text-xl sm:text-2xl font-extrabold text-slate-900 leading-tight tracking-tight">
                                LegalEase AI
                            </h1>
                            <p className="text-xs sm:text-sm text-slate-600">Analyze, simplify, and ask questions about legal documents</p>
                        </div>
                    </div>
                    <div className="hidden md:flex items-center gap-2">
                        <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">Risk Detection</span>
                        <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">Plain Language</span>
                    </div>
                </div>
            </div>
        </header>
    );
};