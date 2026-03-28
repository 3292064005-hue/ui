import { apiUrl } from './config';

export interface ReplyEnvelope {
  ok: boolean;
  message: string;
  request_id?: string;
  data: Record<string, unknown>;
  protocol_version: number;
}

export interface ProtocolSchema {
  api_version: string;
  protocol_version: number;
  commands: Record<string, Record<string, unknown>>;
  telemetry_topics: Record<string, Record<string, unknown>>;
  force_control: {
    max_z_force_n: number;
    warning_z_force_n: number;
    max_xy_force_n: number;
    desired_contact_force_n: number;
    emergency_retract_mm: number;
    force_filter_cutoff_hz: number;
  };
}

export interface TelemetryMessage {
  topic: string;
  ts_ns: number;
  data: Record<string, unknown>;
}

function readErrorDetail(payload: unknown): string {
  if (!payload || typeof payload !== 'object') {
    return 'adapter request failed';
  }
  const detail = (payload as { detail?: unknown }).detail;
  return typeof detail === 'string' && detail ? detail : 'adapter request failed';
}

export async function postCommand(
  command: string,
  payload: Record<string, unknown> = {},
): Promise<ReplyEnvelope> {
  const response = await fetch(apiUrl(`/api/v1/commands/${command}`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const body = (await response.json()) as unknown;
  if (!response.ok) {
    throw new Error(readErrorDetail(body));
  }
  return body as ReplyEnvelope;
}

export async function fetchProtocolSchema(): Promise<ProtocolSchema> {
  const response = await fetch(apiUrl('/api/v1/schema'));
  const body = (await response.json()) as unknown;
  if (!response.ok) {
    throw new Error(readErrorDetail(body));
  }
  return body as ProtocolSchema;
}

export function parseTelemetryMessage(raw: unknown): TelemetryMessage | null {
  if (typeof raw !== 'string') {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as Partial<TelemetryMessage>;
    if (!parsed || typeof parsed !== 'object') {
      return null;
    }
    if (typeof parsed.topic !== 'string' || typeof parsed.ts_ns !== 'number' || typeof parsed.data !== 'object' || parsed.data === null) {
      return null;
    }
    return parsed as TelemetryMessage;
  } catch {
    return null;
  }
}
