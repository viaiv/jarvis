export type MessageRole = 'user' | 'assistant'

export interface ToolCall {
  name: string
  callId: string
  output?: string
}

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  toolCalls?: ToolCall[]
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'
