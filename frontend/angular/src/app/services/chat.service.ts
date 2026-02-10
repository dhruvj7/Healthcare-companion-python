// src/app/services/chat.service.ts

import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, BehaviorSubject, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import {
  ChatRequest,
  ChatResponse,
  Message,
  Capability,
  ConversationHistory
} from '../models/chat.models';

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private apiUrl = `${environment.apiUrl}/public`;
  private sessionId: string | null = null;

  // BehaviorSubject to manage conversation state
  private messagesSubject = new BehaviorSubject<Message[]>([]);
  public messages$ = this.messagesSubject.asObservable();

  constructor(private http: HttpClient) {
    this.loadSessionFromStorage();
  }

  /**
   * Send a message to the unified chat API
   */
  sendMessage(message: string, context?: Record<string, any>): Observable<ChatResponse> {
    const request: ChatRequest = {
      message,
      session_id: this.sessionId || undefined,
      context
    };

    // Add user message to UI immediately
    this.addMessage({
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    });

    // Add loading message
    this.addMessage({
      role: 'assistant',
      content: '...',
      timestamp: new Date().toISOString(),
      isLoading: true
    });

    return this.http.post<ChatResponse>(`${this.apiUrl}/chat`, request).pipe(
      tap(response => {
        // Store session ID
        if (response.session_id) {
          this.sessionId = response.session_id;
          this.saveSessionToStorage();
        }

        // Remove loading message
        this.removeLoadingMessage();

        // Add assistant response
        this.addMessage({
          role: 'assistant',
          content: this.formatResponseMessage(response),
          timestamp: response.timestamp,
          intent: response.intent,
          confidence: response.confidence
        });
      }),
      catchError(error => {
        this.removeLoadingMessage();
        this.addMessage({
          role: 'assistant',
          content: '❌ Sorry, I encountered an error processing your request. Please try again.',
          timestamp: new Date().toISOString()
        });
        return throwError(() => error);
      })
    );
  }

  /**
   * Get system capabilities
   */
  getCapabilities(): Observable<{ capabilities: Capability[], notes: string[] }> {
    return this.http.get<{ capabilities: Capability[], notes: string[] }>(
      `${this.apiUrl}/capabilities`
    );
  }

  /**
   * Get conversation history
   */
  getConversationHistory(): Observable<ConversationHistory> {
    if (!this.sessionId) {
      return throwError(() => new Error('No active session'));
    }

    return this.http.get<ConversationHistory>(
      `${this.apiUrl}/conversation/${this.sessionId}`
    );
  }

  /**
   * Clear conversation
   */
  clearConversation(): Observable<void> {
    if (this.sessionId) {
      return this.http.delete<void>(`${this.apiUrl}/conversation/${this.sessionId}`).pipe(
        tap(() => {
          this.sessionId = null;
          this.messagesSubject.next([]);
          this.clearSessionFromStorage();
        })
      );
    }

    // If no session, just clear local messages
    this.messagesSubject.next([]);
    return new Observable(observer => {
      observer.next();
      observer.complete();
    });
  }

  /**
   * Get current session ID
   */
  getSessionId(): string | null {
    return this.sessionId;
  }

  /**
   * Format response message for display
   */
  private formatResponseMessage(response: ChatResponse): string {
    let message = response.result.message;

    // Add follow-up questions if any
    if (response.follow_up_questions && response.follow_up_questions.length > 0) {
      message += '\n\n**Follow-up questions:**\n';
      response.follow_up_questions.forEach((q, i) => {
        message += `${i + 1}. ${q}\n`;
      });
    }

    return message;
  }

  /**
   * Add message to conversation
   */
  private addMessage(message: Message): void {
    const currentMessages = this.messagesSubject.value;
    this.messagesSubject.next([...currentMessages, message]);
  }
  // chat.service.ts

/**
 * Public method to push a message into the stream (like the welcome message)
 */
public pushSystemMessage(message: Message): void {
  const currentMessages = this.messagesSubject.value;
  this.messagesSubject.next([...currentMessages, message]);
}


  /**
   * Remove loading message
   */
  private removeLoadingMessage(): void {
    const currentMessages = this.messagesSubject.value;
    const filtered = currentMessages.filter(m => !m.isLoading);
    this.messagesSubject.next(filtered);
  }

  /**
   * Save session to localStorage
   */
  private saveSessionToStorage(): void {
    if (this.sessionId) {
      localStorage.setItem('healthcare_session_id', this.sessionId);
    }
  }

  /**
   * Load session from localStorage
   */
  private loadSessionFromStorage(): void {
    const stored = localStorage.getItem('healthcare_session_id');
    if (stored) {
      this.sessionId = stored;
    }
  }

  /**
   * Clear session from localStorage
   */
  private clearSessionFromStorage(): void {
    localStorage.removeItem('healthcare_session_id');
  }
}
