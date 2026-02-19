// src/app/models/chat.models.ts

export interface ChatRequest {
  message: string;
  session_id?: string;
  context?: Record<string, any>;
}

export interface ChatResponse {
  session_id: string;
  timestamp: string;
  user_input: string;
  intent: string;
  confidence: number;
  reasoning: string;
  requires_more_info: boolean;
  follow_up_questions: string[];
  result: ChatResult;
}

export interface ChatResult {
  status: string;
  message: string;
  [key: string]: any; // Additional properties based on intent
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  intent?: string;
  confidence?: number;
  isLoading?: boolean;
}

export interface Capability {
  name: string;
  intent: string;
  description: string;
  example: string;
  icon: string;
}

export interface ConversationHistory {
  session_id: string;
  messages: Message[];
  message_count: number;
}
