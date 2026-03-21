
import React, { useState } from 'react';
import type { AnalysisResult, RiskItem } from '../types';
import { LanguageSelector } from './LanguageSelector';
import { Loader } from './Loader';
import { Icon } from './Icon';

interface AnalysisOutputProps {
    analysis: AnalysisResult;
    translation: string;
    targetLanguage: string;
    setTargetLanguage: (lang: string) => void;
    onTranslate: () => void;
    isTranslating: boolean;
}

type Tab = 'risk' | 'agreement' | 'simplified' | 'summary' | 'clauses' | 'translate';

const getClauseChipColor = (type: string) => {
    switch (type.toLowerCase()) {
        case 'obligation': return 'bg-blue-100 text-blue-800';
        case 'penalty': return 'bg-red-100 text-red-800';
        case 'date': return 'bg-green-100 text-green-800';
        case 'right': return 'bg-purple-100 text-purple-800';
        case 'condition': return 'bg-yellow-100 text-yellow-800';
        default: return 'bg-slate-100 text-slate-800';
    }
};

const getRiskPresentation = (severity: RiskItem['severity']) => {
    switch (severity) {
        case 'High':
            return {
                icon: 'risk',
                colorClasses: 'border-red-500 bg-red-50',
                textColor: 'text-red-800',
                iconColor: 'text-red-600'
            };
        case 'Medium':
            return {
                icon: 'shield-exclamation',
                colorClasses: 'border-yellow-500 bg-yellow-50',
                textColor: 'text-yellow-800',
                iconColor: 'text-yellow-600'
            };
        case 'Low':
        default:
            return {
                icon: 'shield-check',
                colorClasses: 'border-blue-500 bg-blue-50',
                textColor: 'text-blue-800',
                iconColor: 'text-blue-600'
            };
    }
};


export const AnalysisOutput: React.FC<AnalysisOutputProps> = ({ analysis, translation, targetLanguage, setTargetLanguage, onTranslate, isTranslating }) => {
    const [activeTab, setActiveTab] = useState<Tab>('risk');
    
    const tabs: { id: Tab, label: string, icon: string }[] = [
        { id: 'risk', label: 'Risk Analysis', icon: 'risk' },
        { id: 'agreement', label: 'Document Details', icon: 'signature' },
        { id: 'simplified', label: 'Simplified Text', icon: 'document' },
        { id: 'summary', label: 'Summary', icon: 'summary' },
        { id: 'clauses', label: 'Key Clauses', icon: 'key' },
        { id: 'translate', label: 'Translate', icon: 'language' }
    ];

    return (
        <div className="bg-white p-6 rounded-lg shadow-md border border-slate-200 min-h-[400px]">
            <div className="mb-4">
                <nav className="bg-slate-100 p-1 rounded-lg flex flex-wrap space-x-1" aria-label="Tabs">
                    {tabs.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`${
                                activeTab === tab.id
                                    ? 'bg-white shadow text-indigo-600'
                                    : 'text-slate-600 hover:bg-slate-200 hover:text-slate-800'
                            } flex-1 whitespace-nowrap py-2.5 px-2 rounded-md font-medium text-sm flex items-center justify-center transition-all duration-200 min-w-max`}
                        >
                            <Icon name={tab.icon} className="h-5 w-5 mr-2" />
                            {tab.label}
                        </button>
                    ))}
                </nav>
            </div>
            <div className="prose max-w-none prose-slate">
                 {activeTab === 'risk' && (
                    <div>
                        <h3 className="text-lg font-semibold mb-4 text-slate-800">Risk & Mitigation Analysis</h3>
                        {analysis.riskAnalysis && analysis.riskAnalysis.length > 0 ? (
                            <div className="space-y-4">
                                {analysis.riskAnalysis.map((item, index) => {
                                    const presentation = getRiskPresentation(item.severity);
                                    return (
                                    <div key={index} className={`p-4 rounded-lg border-l-4 ${presentation.colorClasses}`}>
                                        <div className="flex items-start">
                                            <Icon name={presentation.icon} className={`h-6 w-6 mr-3 flex-shrink-0 ${presentation.iconColor}`} />
                                            <div className="flex-grow">
                                                <h4 className={`font-bold ${presentation.textColor}`}>{item.severity} Risk Detected</h4>
                                                <p className="text-slate-700 mt-1">{item.risk}</p>
                                            </div>
                                        </div>
                                        
                                        <div className="mt-4 pl-9">
                                            <h5 className="font-semibold text-green-800 flex items-center text-sm">
                                                <Icon name="sparkles" className="h-4 w-4 mr-2 text-green-600" />
                                                Suggested Solution
                                            </h5>
                                            <p className="text-slate-600 text-sm mt-1">{item.mitigation}</p>
                                        </div>
                                        
                                        <details className="mt-3 pl-9 group">
                                            <summary className="text-sm font-semibold text-slate-500 cursor-pointer list-none flex items-center">
                                                Legal Context
                                                <Icon name="chevron-down" className="h-4 w-4 ml-1 transition-transform group-open:rotate-180" />
                                            </summary>
                                            <div className="mt-2 pt-3 border-t border-slate-200 text-sm space-y-2">
                                                 <p className="text-slate-600">
                                                    <strong className="font-semibold text-slate-700">Applicable Law:</strong> {item.applicableLaw}
                                                </p>
                                                <p className="text-slate-600">
                                                    <strong className="font-semibold text-slate-700">Punishment for Violation:</strong> {item.punishment}
                                                </p>
                                            </div>
                                        </details>
                                    </div>
                                    )
                                })}
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center p-8 text-center bg-green-50 rounded-lg border border-green-200">
                                <Icon name="shield-check" className="h-12 w-12 text-green-500" />
                                <h4 className="mt-4 font-semibold text-green-800">All Clear!</h4>
                                <p className="text-slate-600">Our analysis did not identify any major risks in this document.</p>
                            </div>
                        )}
                    </div>
                )}
                 {activeTab === 'agreement' && (
                    <div>
                        <h3 className="text-lg font-semibold mb-4 text-slate-800">Document Details</h3>
                        <ul className="space-y-3">
                            <li className="flex flex-col sm:flex-row items-start p-3 bg-slate-50 rounded-md">
                                <strong className="w-full sm:w-1/3 font-semibold text-slate-600 mb-1 sm:mb-0">Document Type:</strong>
                                <span className="w-full sm:w-2/3 text-slate-800">{analysis.documentDetails.documentType}</span>
                            </li>
                            <li className="flex flex-col sm:flex-row items-start p-3 bg-slate-50 rounded-md">
                                <strong className="w-full sm:w-1/3 font-semibold text-slate-600 mb-1 sm:mb-0">Parties / Entities:</strong>
                                <span className="w-full sm:w-2/3 text-slate-800">
                                    {analysis.documentDetails.partiesOrEntities.length > 0
                                        ? analysis.documentDetails.partiesOrEntities.join(', ')
                                        : 'Not specified'}
                                </span>
                            </li>
                            <li className="flex flex-col sm:flex-row items-start p-3 bg-slate-50 rounded-md">
                                <strong className="w-full sm:w-1/3 font-semibold text-slate-600 mb-1 sm:mb-0">Date:</strong>
                                <span className="w-full sm:w-2/3 text-slate-800">{analysis.documentDetails.date}</span>
                            </li>
                            <li className="flex flex-col sm:flex-row items-start p-3 bg-slate-50 rounded-md">
                                <strong className="w-full sm:w-1/3 font-semibold text-slate-600 mb-1 sm:mb-0">Duration / Term:</strong>
                                <span className="w-full sm:w-2/3 text-slate-800">{analysis.documentDetails.duration}</span>
                            </li>
                            <li className="flex flex-col sm:flex-row items-start p-3 bg-slate-50 rounded-md">
                                <strong className="w-full sm:w-1/3 font-semibold text-slate-600 mb-1 sm:mb-0">Jurisdiction:</strong>
                                <span className="w-full sm:w-2/3 text-slate-800">{analysis.documentDetails.jurisdiction}</span>
                            </li>
                            <li className="flex flex-col sm:flex-row items-start p-3 bg-slate-50 rounded-md">
                                <strong className="w-full sm:w-1/3 font-semibold text-slate-600 mb-1 sm:mb-0">Purpose:</strong>
                                <span className="w-full sm:w-2/3 text-slate-800">{analysis.documentDetails.purpose}</span>
                            </li>
                        </ul>
                    </div>
                )}
                {activeTab === 'simplified' && (
                    <div>
                        <h3 className="text-lg font-semibold mb-2 text-slate-800">Plain English Version</h3>
                        <p className="text-slate-600 whitespace-pre-wrap">{analysis.simplifiedText}</p>
                    </div>
                )}
                {activeTab === 'summary' && (
                     <div>
                        <h3 className="text-lg font-semibold mb-2 text-slate-800">Executive Summary</h3>
                        <p className="text-slate-600 whitespace-pre-wrap">{analysis.summary}</p>
                    </div>
                )}
                {activeTab === 'clauses' && (
                    <div>
                         <h3 className="text-lg font-semibold mb-2 text-slate-800">Highlighted Clauses</h3>
                        <ul className="space-y-4">
                            {analysis.keyClauses.map((item, index) => (
                                <li key={index} className="p-4 bg-slate-50 rounded-md border border-slate-200">
                                    <div className={`inline-block px-3 py-1 text-sm font-semibold rounded-full ${getClauseChipColor(item.type)}`}>
                                        {item.type}
                                    </div>
                                    <blockquote className="mt-2 pl-4 border-l-4 border-slate-300 text-slate-600 italic">
                                        "{item.clause}"
                                    </blockquote>
                                    <p className="mt-2 text-slate-700"><strong className="font-semibold">In simple terms:</strong> {item.explanation}</p>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
                {activeTab === 'translate' && (
                    <div>
                         <h3 className="text-lg font-semibold mb-2 text-slate-800">Translate Simplified Text</h3>
                         <div className="flex items-center space-x-2 mb-4">
                            <LanguageSelector selectedLanguage={targetLanguage} onSelectLanguage={setTargetLanguage} />
                            <button
                                onClick={onTranslate}
                                disabled={isTranslating}
                                className="bg-indigo-600 text-white font-semibold py-2 px-4 rounded-md hover:bg-indigo-700 disabled:bg-indigo-300 transition duration-150 flex items-center"
                            >
                                {isTranslating ? <Loader /> : <Icon name="language" className="h-5 w-5 mr-2"/>}
                                Translate
                            </button>
                         </div>
                         {isTranslating && <p className="text-slate-500">Translating...</p>}
                         {translation && !isTranslating && (
                            <div className="mt-4 p-4 bg-slate-50 rounded-md border border-slate-200">
                                 <h4 className="font-semibold text-slate-800">Translation:</h4>
                                 <p className="text-slate-600 whitespace-pre-wrap">{translation}</p>
                            </div>
                         )}
                    </div>
                )}
            </div>
        </div>
    );
};
