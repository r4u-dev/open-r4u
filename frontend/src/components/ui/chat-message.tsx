import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
}

const messageVariants = cva(
  "p-4 rounded-lg max-w-[85%] break-words transition-all duration-200 ease-in-out",
  {
    variants: {
      role: {
        user: "bg-primary text-primary-foreground ml-auto w-fit shadow-sm border border-primary/20",
        assistant: "bg-muted text-foreground mr-auto shadow-sm border border-border/50",
      },
    },
    defaultVariants: {
      role: "assistant",
    },
  }
);

export interface ChatMessageProps extends VariantProps<typeof messageVariants> {
  message: ChatMessage;
  isLoading?: boolean;
  className?: string;
}

const ChatMessageComponent = React.forwardRef<HTMLDivElement, ChatMessageProps>(
  ({ message, isLoading = false, className, ...props }, ref) => {
    const isAssistant = message.role === 'assistant';
    const isUser = message.role === 'user';
    
    return (
      <div
        ref={ref}
        className={cn(messageVariants({ role: message.role }), className)}
        role="article"
        aria-label={`${isAssistant ? 'AI Assistant' : 'User'} message`}
        {...props}
      >
        {/* Screen reader label for message sender */}
        <div className="sr-only">
          {isAssistant ? 'AI Assistant says:' : 'You said:'}
        </div>
        
        <div className="text-sm leading-relaxed">
          {isLoading && isAssistant ? (
            <div 
              className="flex items-center gap-2"
              role="status"
              aria-live="polite"
              aria-label="AI Assistant is thinking"
            >
              <Loader2 
                className="h-4 w-4 animate-spin text-primary" 
                aria-hidden="true"
              />
              <span className="text-muted-foreground font-medium">Thinking...</span>
            </div>
          ) : (
            <div 
              className="whitespace-pre-wrap"
              role="text"
              aria-label={`Message content: ${message.content}`}
            >
              {message.content}
            </div>
          )}
        </div>
      </div>
    );
  }
);

ChatMessageComponent.displayName = "ChatMessage";

export { ChatMessageComponent as ChatMessage, messageVariants };