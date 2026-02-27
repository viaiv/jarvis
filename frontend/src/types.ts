export type MessageRole = 'user' | 'assistant'

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'
