import {
  Component,
  OnInit,
  ViewChild,
  ElementRef,
  AfterViewChecked
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { ChatService } from '../../services/chat.service';
import { Message } from '../../models/chat.models';
import { SafeHtmlPipe } from '../../pipes/safe-html.pipe';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [
    CommonModule,   // ngIf, ngFor, ngClass
    FormsModule,    // ngModel
    SafeHtmlPipe    // safeHtml pipe
  ],
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent implements OnInit, AfterViewChecked {
  @ViewChild('messagesContainer') private messagesContainer!: ElementRef;

  messages: Message[] = [];
  userInput = '';
  isLoading = false;
  error: string | null = null;
  sessionId: string | null = null;

  examplePrompts = [
    'I have a fever and cough for 3 days',
    'Verify my Blue Cross insurance',
    'Book appointment with cardiologist',
    'Where is the cafeteria?',
    'What is diabetes?'
  ];

  constructor(private chatService: ChatService) {}

  // chat.component.ts

ngOnInit(): void {
  this.chatService.messages$.subscribe(messages => {
    this.messages = messages;
    this.sessionId = this.chatService.getSessionId();
  });
   console.log("sessionId",this.chatService.getSessionId() )
  // Show welcome message only once at startup
  if (this.chatService.getSessionId() === null) {
    this.addWelcomeMessage();
  }
}


  ngAfterViewChecked(): void {
    this.scrollToBottom();
  }

sendMessage(): void {
  // this.isLoading=true
  const message = this.userInput.trim();
  if (!message) return;

  this.error = null;
  this.userInput = '';

  this.chatService.sendMessage(message).subscribe({
    next: () => {
      this.userInput = '';
      // this.isLoading=false
    },
    error: () => {
      this.error = 'Failed to send message. Please try again.';
    }
  });
}

  useExample(example: string): void {
    this.userInput = example;
    this.sendMessage();
  }

  clearChat(): void {
    if (!confirm('Are you sure you want to clear the conversation?')) return;

    this.chatService.clearConversation().subscribe({
      next: () => this.addWelcomeMessage(),
      error: () => {
        this.error = 'Failed to clear conversation.';
      }
    });
  }

  onKeyPress(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  private addWelcomeMessage(): void {
    const welcomeMessage: Message = {
      role: 'assistant',
      content: `👋 **Welcome to Healthcare Companion!**

I'm your AI healthcare assistant. I can help you with:

💊 **Symptom Analysis**
🏥 **Insurance Verification**
📅 **Appointment Booking**
🧭 **Hospital Navigation**
❓ **Health Questions**

Just type your question below!`,
      timestamp: new Date().toISOString()
    };

 
    this.chatService.pushSystemMessage(welcomeMessage);
  }

  getIntentBadgeColor(intent?: string): string {
    const colorMap: Record<string, string> = {
      symptom_analysis: 'blue',
      insurance_verification: 'green',
      appointment_booking: 'purple',
      hospital_navigation: 'orange',
      general_health_question: 'teal',
      emergency: 'red'
    };
    return colorMap[intent ?? ''] || 'gray';
  }

  getIntentDisplayName(intent?: string): string {
    const nameMap: Record<string, string> = {
      symptom_analysis: 'Symptom Analysis',
      insurance_verification: 'Insurance',
      appointment_booking: 'Appointment',
      hospital_navigation: 'Navigation',
      general_health_question: 'General Question',
      emergency: 'EMERGENCY',
      unknown: 'Unknown'
    };
    return nameMap[intent ?? ''] || '';
  }

  private scrollToBottom(): void {
    if (this.messagesContainer) {
      this.messagesContainer.nativeElement.scrollTop =
        this.messagesContainer.nativeElement.scrollHeight;
    }
  }

  formatTimestamp(timestamp: string): string {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
