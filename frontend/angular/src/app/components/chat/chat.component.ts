// src/app/components/chat/chat.component.ts

import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { ChatService } from '../../services/chat.service';
import { Message } from '../../models/chat.models';

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent implements OnInit, AfterViewChecked {
  @ViewChild('messagesContainer') private messagesContainer!: ElementRef;

  messages: Message[] = [];
  userInput: string = '';
  isLoading: boolean = false;
  error: string | null = null;
  sessionId: string | null = null;

  // Example prompts for quick start
  examplePrompts = [
    'I have a fever and cough for 3 days',
    'Verify my Blue Cross insurance',
    'Book appointment with cardiologist',
    'Where is the cafeteria?',
    'What is diabetes?'
  ];

  constructor(private chatService: ChatService) {}

  ngOnInit(): void {
    // Subscribe to messages
    this.chatService.messages$.subscribe(messages => {
      this.messages = messages;
      this.sessionId = this.chatService.getSessionId();
    });

    // Add welcome message
    if (this.messages.length === 0) {
      this.addWelcomeMessage();
    }
  }

  ngAfterViewChecked(): void {
    this.scrollToBottom();
  }

  /**
   * Send user message
   */
  sendMessage(): void {
    const message = this.userInput.trim();

    if (!message) {
      return;
    }

    this.isLoading = true;
    this.error = null;

    this.chatService.sendMessage(message).subscribe({
      next: (response) => {
        console.log('Response received:', response);
        this.isLoading = false;
        this.userInput = '';
      },
      error: (error) => {
        console.error('Error sending message:', error);
        this.error = 'Failed to send message. Please try again.';
        this.isLoading = false;
      }
    });
  }

  /**
   * Use example prompt
   */
  useExample(example: string): void {
    this.userInput = example;
    this.sendMessage();
  }

  /**
   * Clear conversation
   */
  clearChat(): void {
    if (confirm('Are you sure you want to clear the conversation?')) {
      this.chatService.clearConversation().subscribe({
        next: () => {
          console.log('Conversation cleared');
          this.addWelcomeMessage();
        },
        error: (error) => {
          console.error('Error clearing conversation:', error);
          this.error = 'Failed to clear conversation.';
        }
      });
    }
  }

  /**
   * Handle Enter key press
   */
  onKeyPress(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  /**
   * Add welcome message
   */
  private addWelcomeMessage(): void {
    const welcomeMessage: Message = {
      role: 'assistant',
      content: `👋 **Welcome to Healthcare Companion!**

I'm your AI healthcare assistant. I can help you with:

💊 **Symptom Analysis** - Describe your symptoms
🏥 **Insurance Verification** - Verify coverage
📅 **Appointment Booking** - Schedule appointments
🧭 **Hospital Navigation** - Find locations
❓ **Health Questions** - Ask anything health-related

Just type your question or concern below, and I'll help you!`,
      timestamp: new Date().toISOString()
    };

    this.messages = [welcomeMessage];
  }

  /**
   * Get intent badge color
   */
  getIntentBadgeColor(intent?: string): string {
    if (!intent) return 'gray';

    const colorMap: Record<string, string> = {
      'symptom_analysis': 'blue',
      'insurance_verification': 'green',
      'appointment_booking': 'purple',
      'hospital_navigation': 'orange',
      'general_health_question': 'teal',
      'emergency': 'red'
    };

    return colorMap[intent] || 'gray';
  }

  /**
   * Get intent display name
   */
  getIntentDisplayName(intent?: string): string {
    if (!intent) return '';

    const nameMap: Record<string, string> = {
      'symptom_analysis': 'Symptom Analysis',
      'insurance_verification': 'Insurance',
      'appointment_booking': 'Appointment',
      'hospital_navigation': 'Navigation',
      'general_health_question': 'General Question',
      'emergency': 'EMERGENCY',
      'unknown': 'Unknown'
    };

    return nameMap[intent] || intent;
  }

  /**
   * Scroll to bottom of messages
   */
  private scrollToBottom(): void {
    try {
      if (this.messagesContainer) {
        this.messagesContainer.nativeElement.scrollTop =
          this.messagesContainer.nativeElement.scrollHeight;
      }
    } catch (err) {
      console.error('Error scrolling to bottom:', err);
    }
  }

  /**
   * Format timestamp for display
   */
  formatTimestamp(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
