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

export interface User {
  id: number
  username: string
  email: string
  role: 'user' | 'admin'
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
}

export interface LoginCredentials {
  username: string
  password: string
}

// --- Admin types ---

export interface AdminUser {
  id: number
  username: string
  email: string
  role: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UserCreate {
  username: string
  email: string
  password: string
  role?: string
}

export interface UserUpdate {
  email?: string
  role?: string
  is_active?: boolean
}

export interface ConfigData {
  system_prompt?: string | null
  model_name?: string | null
  history_window?: number | null
  max_tool_steps?: number | null
}

export interface ThreadSummary {
  thread_id: string
  user_id: number | null
  username: string | null
  message_count: number
}

export interface ThreadListResponse {
  threads: ThreadSummary[]
  total: number
}

export interface ThreadMessage {
  role: string
  content: string
}

// --- Agent Runs ---

export interface AgentRun {
  id: number
  repo: string
  issue_number: number
  issue_title: string
  action: string
  category: string | null
  status: 'processing' | 'completed' | 'failed'
  tool_steps: number
  error_message: string | null
  started_at: string
  finished_at: string | null
}

export interface AgentRunListResponse {
  runs: AgentRun[]
  total: number
}

// --- Tools ---

export interface ToolInfo {
  name: string
  description: string
  enabled: boolean
}

export interface ToolsResponse {
  tools: ToolInfo[]
}
