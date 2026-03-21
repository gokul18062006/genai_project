
import React from 'react';
import { LANGUAGES } from '../constants';

interface LanguageSelectorProps {
    selectedLanguage: string;
    onSelectLanguage: (lang: string) => void;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({ selectedLanguage, onSelectLanguage }) => {
    return (
        <select
            value={selectedLanguage}
            onChange={(e) => onSelectLanguage(e.target.value)}
            className="w-full max-w-xs p-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition duration-150 ease-in-out"
        >
            {LANGUAGES.map(lang => (
                <option key={lang.code} value={lang.code}>
                    {lang.name}
                </option>
            ))}
        </select>
    );
};
