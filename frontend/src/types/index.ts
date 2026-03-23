export interface User {
  id: string;
  email: string;
  role: "owner" | "readonly";
}

export interface Message {
  role: "user" | "assistant" | "tool";
  content: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  created_at: string;
  messages?: Message[];
}

export interface PendingAction {
  tool_name: string;
  inputs: Record<string, unknown>;
  confirmation_message: string;
}

export interface ChatResponse {
  reply: string;
  conversation_id: string;
  tool_calls: { tool: string; inputs: Record<string, unknown> }[];
  requires_confirmation: boolean;
  pending_action: PendingAction | null;
}

export interface HealthStatus {
  is_up: boolean;
  status_code: number | null;
  response_time_ms: number | null;
  ssl_expiry_days: number | null;
  url: string;
  checked_at: string;
  error: string | null;
}

export interface DeployEvent {
  id: string;
  status: "pending" | "running" | "success" | "failed";
  trigger: string;
  commit_sha: string | null;
  deploy_url: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface Lead {
  id: string;
  name: string;
  email: string;
  message: string | null;
  status: "new" | "classified" | "contacted" | "converted" | "spam";
  classification: "hot" | "warm" | "cold" | "spam" | null;
  source: string | null;
  created_at: string;
}

export interface AuditLog {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  meta: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface ContentItem {
  id: string;
  slug: string;
  type: string;
  title: string | null;
  published: boolean;
  updated_at: string | null;
}