import { create } from 'zustand';

export interface LogEntry {
  time: string;
  level: 'info' | 'warn' | 'error' | 'success';
  msg: string;
}

interface SessionState {
  // Scan state
  scanState: 'idle' | 'scanning' | 'halted';
  sessionId: string | null;
  startTime: number | null;
  frameCount: number;

  // Event log
  logs: LogEntry[];

  // Force history for CSV export
  forceHistory: { t: number; v: number }[];

  // Actions
  startScan: () => void;
  stopScan: () => void;
  triggerHalt: () => void;
  resetHalt: () => void;
  addLog: (level: LogEntry['level'], msg: string) => void;
  pushForce: (v: number) => void;
  incrementFrame: () => void;
  exportCSV: () => void;
}

const genSessionId = () => {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `SES-${d.getFullYear()}${pad(d.getMonth()+1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
};

const timeStr = () => {
  const d = new Date();
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}.${String(d.getMilliseconds()).padStart(3,'0')}`;
};

export const useSessionStore = create<SessionState>((set, get) => ({
  scanState: 'idle',
  sessionId: null,
  startTime: null,
  frameCount: 0,
  logs: [{ time: timeStr(), level: 'info', msg: '系统初始化完成，等待连接...' }],
  forceHistory: [],

  startScan: () => {
    const sid = genSessionId();
    set({ scanState: 'scanning', sessionId: sid, startTime: Date.now(), frameCount: 0, forceHistory: [] });
    get().addLog('success', `扫描启动 [${sid}]`);
  },

  stopScan: () => {
    const sid = get().sessionId;
    set({ scanState: 'idle', startTime: null });
    get().addLog('info', `扫描停止 [${sid}]，共 ${get().frameCount} 帧`);
  },

  triggerHalt: () => {
    set({ scanState: 'halted' });
    get().addLog('error', '⚠ 紧急制动已激活 — 硬件锁定');
  },

  resetHalt: () => {
    set({ scanState: 'idle' });
    get().addLog('warn', '制动已解除 — 系统恢复待机');
  },

  addLog: (level, msg) => {
    set(s => ({
      logs: [...s.logs.slice(-200), { time: timeStr(), level, msg }]
    }));
  },

  pushForce: (v) => {
    if (get().scanState !== 'scanning') return;
    set(s => ({
      forceHistory: [...s.forceHistory.slice(-3000), { t: Date.now(), v }]
    }));
  },

  incrementFrame: () => set(s => ({ frameCount: s.frameCount + 1 })),

  exportCSV: () => {
    const rows = get().forceHistory;
    if (rows.length === 0) return;
    const csv = 'timestamp_ms,force_N\n' + rows.map(r => `${r.t},${r.v.toFixed(4)}`).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `force_data_${get().sessionId || 'export'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    get().addLog('success', `已导出 ${rows.length} 条力数据至 CSV`);
  },
}));
