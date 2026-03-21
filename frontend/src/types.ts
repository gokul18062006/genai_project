export interface KeyClause {
  type: 'Obligation' | 'Penalty' | 'Date' | 'Right' | 'Condition' | 'Other';
  clause: string;
  explanation: string;
}

export interface RiskItem {
    risk: string;
    mitigation: string;
    severity: 'High' | 'Medium' | 'Low';
    applicableLaw: string;
    punishment: string;
}

export interface DocumentDetails {
    documentType: string;
    partiesOrEntities: string[];
    date: string;
    duration: string;
    jurisdiction: string;
    purpose: string;
}

export interface AnalysisResult {
  simplifiedText: string;
  summary: string;
  keyClauses: KeyClause[];
  riskAnalysis: RiskItem[];
  documentDetails: DocumentDetails;
}

export interface ChatMessage {
    sender: 'user' | 'ai';
    text: string;
}

export interface UploadedFile {
    name: string;
    mimeType: string;
    data: string; // base64 encoded
}
