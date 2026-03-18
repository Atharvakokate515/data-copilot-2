export interface ChartSuggestion {
  type: "bar" | "line" | "pie" | "table";
  x_axis: string;
  y_axis: string;
}

export interface ExecutionResult {
  success: boolean;
  query_type: "SELECT" | "INSERT" | "UPDATE" | "DELETE";
  execution_time_sec: number;
  result: {
    type: string;
    col_names?: string[];
    rows?: any[][];
    row_count?: number;
    rows_affected?: number;
    updated_table?: {
      col_names: string[];
      rows: any[][];
    };
  };
}

export interface Plan {
  intent: string;
  tables: string[];
  columns: string[];
}

export interface Citation {
  source: string;
  page: number;
  confidence: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "error" | "clarification";
  content: string;
  metadata?: {
    sql?: string;
    summary?: string;
    chart?: ChartSuggestion | null;
    execution?: ExecutionResult;
    plan?: Plan;
    wasRetried?: boolean;
    tool?: string;
    sqlUsed?: boolean;
    ragUsed?: boolean;
    citations?: Citation[] | null;
    answerGrounded?: boolean;
    errorCode?: string;
    question?: string;
    originalInput?: string;
  };
}

export interface NL2SQLSession {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface CopilotSession {
  chat_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface DocInfo {
  source: string;
  chunk_count: number;
  ingested_at: string;
}

export interface DBConnectionResult {
  success: boolean;
  db_name: string;
  tables: string[];
  error: string | null;
}

export interface ChatDBResponse {
  success: boolean;
  stage?: string;
  generated_sql?: string;
  summary?: string;
  chart_suggestion?: ChartSuggestion | null;
  was_retried?: boolean;
  plan?: Plan;
  execution?: ExecutionResult;
  error_code?: string;
  error?: string;
  needs_clarification?: boolean;
  question?: string;
  original_sql?: string;
}

export interface AgentChatResponse {
  success: boolean;
  response: {
    tool: string;
    answer: string;
    sql_used: boolean;
    rag_used: boolean;
    citations: Citation[] | null;
    answer_grounded: boolean;
  };
}

export interface SessionHistory {
  session_id: string;
  title: string;
  last_sql: string | null;
  chat_history: { role: string; content: string }[];
}

export interface CopilotHistory {
  chat_id: number;
  title: string;
  messages: { role: string; content: string }[];
}
