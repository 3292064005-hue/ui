import { useEffect, useRef, useCallback } from 'react';
import { useTelemetryStore } from '../store/telemetryStore';
import { useSessionStore } from '../store/sessionStore';

const WS_URL = 'ws://127.0.0.1:8000/ws/telemetry';
const MAX_BACKOFF = 8000;

/**
 * Centralized WebSocket hook with:
 * - Exponential backoff + jitter on reconnect
 * - Binary ArrayBuffer parsing (204 bytes: ts + pose16 + force + safety + joints7)
 * - Direct Zustand store writes (no React re-render chain)
 */
export function useTelemetrySocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1000);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    const ws = new WebSocket(WS_URL);
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;

    ws.onopen = () => {
      backoffRef.current = 1000; // reset backoff
      useTelemetryStore.getState().setConnected(true);
      useSessionStore.getState().addLog('success', '遥测通道已连接 (WebSocket)');
    };

    ws.onclose = () => {
      useTelemetryStore.getState().setConnected(false);
      if (!mountedRef.current) return;

      // Exponential backoff with jitter
      const jitter = Math.random() * 500;
      const delay = Math.min(backoffRef.current + jitter, MAX_BACKOFF);
      backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF);

      useSessionStore.getState().addLog('warn', `遥测断开，${(delay/1000).toFixed(1)}秒后重连...`);
      setTimeout(connect, delay);
    };

    ws.onerror = () => {
      // onclose will fire after onerror — just log
      useSessionStore.getState().addLog('error', 'WebSocket 连接错误');
    };

    ws.onmessage = (event) => {
      if (!(event.data instanceof ArrayBuffer)) return;
      const buf = event.data;
      const view = new DataView(buf);

      const sessionState = useSessionStore.getState();
      if (sessionState.scanState === 'halted') return; // ignore data during halt

      // ==== 204-byte format ====
      // [0..7]    int64   timestamp_ms
      // [8..135]  16×f64  4x4 pose matrix
      // [136..143] f64    force_z
      // [144..147] i32    safety_flag
      // [148..203] 7×f64  joint angles
      if (buf.byteLength === 204) {
        const ts = Number(view.getBigInt64(0, true));
        const force = view.getFloat64(136, true);
        const safety = view.getInt32(144, true);

        const joints: number[] = [];
        for (let i = 0; i < 7; i++) {
          joints.push(view.getFloat64(148 + i * 8, true));
        }

        // Latency = now - server timestamp
        const latency = Date.now() - ts;
        useTelemetryStore.getState().pushTelemetry(ts, force, safety, joints);
        useTelemetryStore.getState().setLatency(Math.max(0, latency));

        // Record force during scanning
        sessionState.pushForce(force);
        if (sessionState.scanState === 'scanning') {
          sessionState.incrementFrame();
        }
      }
      // Legacy 148-byte fallback
      else if (buf.byteLength === 148) {
        const ts = Number(view.getBigInt64(0, true));
        const force = view.getFloat64(136, true);
        const safety = view.getInt32(144, true);

        useTelemetryStore.getState().pushTelemetry(ts, force, safety, [0,0,0,0,0,0,0]);
        useTelemetryStore.getState().setLatency(Math.max(0, Date.now() - ts));
        sessionState.pushForce(force);
        if (sessionState.scanState === 'scanning') {
          sessionState.incrementFrame();
        }
      }
    };
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      wsRef.current?.close();
    };
  }, [connect]);
}
