import { useEffect } from 'react';
import { useTelemetryStore } from './store/telemetryStore';
import { useSessionStore } from './store/sessionStore';
import { useUIStore } from './store/uiStore';
import { useTelemetrySocket } from './hooks/useWebSocket';

import ThreeDView from './components/ThreeDView';
import ForceGraph from './components/ForceGraph';
import RollingChart from './components/RollingChart';
import CameraFeed from './components/CameraFeed';
import UltrasoundFeed from './components/UltrasoundFeed';
import Sidebar from './components/Sidebar';
import JointAnglePanel from './components/JointAnglePanel';
import SystemLog from './components/SystemLog';
import SessionTimer from './components/SessionTimer';
import StatusBar from './components/StatusBar';
import ToastContainer from './components/Toast';

import { Activity, ShieldAlert, WifiOff, Loader2, Play, Square, Zap } from 'lucide-react';

export default function App() {
  // Connect the centralized WebSocket
  useTelemetrySocket();

  // Store hooks
  const { force, safety, connected } = useTelemetryStore();
  const { scanState, startScan, stopScan, triggerHalt, resetHalt, addLog } = useSessionStore();
  const { showCamera, showUltrasound, showForceGraph, show3DView, showJoints, showLog, addToast } = useUIStore();

  const isHalted = scanState === 'halted';
  const isScanning = scanState === 'scanning';

  // Handle scan button
  const handleScanToggle = () => {
    if (isHalted) return;
    if (isScanning) {
      stopScan();
      addToast('扫描已停止', 'info');
    } else {
      startScan();
      addToast('扫描已启动', 'success');
    }
  };

  // Handle E-STOP
  const handleEStop = () => {
    triggerHalt();
    addToast('⚠ 紧急制动已激活', 'error');
  };

  // Handle RESET
  const handleReset = () => {
    resetHalt();
    addToast('制动已解除，系统恢复', 'warn');
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === ' ' || e.code === 'Space') {
        e.preventDefault();
        handleScanToggle();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        if (isHalted) handleReset();
        else handleEStop();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  });

  return (
    <div className="relative w-screen h-screen">

      {/* === Layer 0: 3D Background === */}
      <div className={`absolute inset-0 z-0 transition-opacity duration-500 ${show3DView && !isHalted ? 'opacity-100' : 'opacity-20'}`}>
        <ThreeDView />
      </div>

      {/* === Layer 1: HUD Overlays === */}
      <div className="absolute inset-0 z-10 pointer-events-none flex flex-col" style={{ paddingBottom: '28px' }}>

        {/* ── Top Header Bar ── */}
        <header className="flex justify-between items-center glass-panel p-3 mx-4 mt-4 pointer-events-auto shadow-[0_0_30px_rgba(0,0,0,0.6)]">
          <div className="flex items-center space-x-3">
            <Activity className={`w-5 h-5 animate-pulse-fast ${isHalted ? 'text-clinical-error' : 'text-clinical-cyan'}`} />
            <h1 className={`text-lg font-mono tracking-widest font-bold ${isHalted ? 'text-clinical-error' : 'text-clinical-cyan'}`}>
              脊柱超声机器人
            </h1>
            <span className="text-[10px] text-gray-600 font-mono">SPINE.US / ROKAE xMate ER3</span>
          </div>

          <div className="flex items-center space-x-4">
            {/* Session Timer */}
            <SessionTimer />

            {/* Connection Status */}
            {connected ? (
              <span className={`font-mono text-xs flex items-center ${isHalted ? 'text-clinical-error' : 'text-clinical-emerald'}`}>
                <div className={`w-1.5 h-1.5 rounded-full mr-1.5 animate-pulse ${isHalted ? 'bg-clinical-error' : 'bg-clinical-emerald'}`} />
                {isHalted ? '数据暂停' : '已同步'}
              </span>
            ) : (
              <span className="text-clinical-error font-mono text-xs flex items-center">
                <WifiOff className="w-4 h-4 mr-1.5" /> 离线
              </span>
            )}
          </div>
        </header>

        {/* ── Main Content Area ── */}
        <div className={`flex flex-1 mt-3 px-4 pointer-events-none min-h-0 transition-opacity duration-300 ${isHalted ? 'opacity-30' : ''}`}>

          {/* Left: Sidebar */}
          <Sidebar />

          {/* Center: Flexible space (3D shows through) */}
          <div className="flex-1" />

          {/* Right Column: Video feeds + Joints */}
          <div className="flex flex-col items-end space-y-0 pointer-events-none max-h-full overflow-y-auto custom-scrollbar pr-1">
            {showCamera && <CameraFeed />}
            {showUltrasound && <UltrasoundFeed />}
            {showJoints && (
              <div className="mt-3">
                <JointAnglePanel />
              </div>
            )}
          </div>
        </div>

        {/* ── Bottom Control Strip ── */}
        <div className={`flex justify-between items-end px-4 pb-2 mt-2 pointer-events-none transition-opacity duration-300 ${isHalted ? 'opacity-30' : ''}`}>

          {/* Left Bottom: Force Telemetry + Chart + Log */}
          <div className="flex items-end space-x-3 pointer-events-auto">
            {/* Force Gauge */}
            {showForceGraph && (
              <div className="w-80 glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.5)] animate-fade-in-up">
                <h3 className="text-[10px] text-gray-500 font-bold tracking-widest mb-3">Z 轴力控</h3>
                <ForceGraph latestForce={force} maxForce={15.0} />
              </div>
            )}

            {/* Oscilloscope */}
            {showForceGraph && (
              <div className="glass-panel p-2 shadow-[0_0_20px_rgba(0,0,0,0.5)] animate-fade-in-up">
                <h3 className="text-[10px] text-clinical-cyan font-bold tracking-widest px-1 mb-1">力传感器示波器</h3>
                <RollingChart
                  latestValue={force}
                  color={Math.abs(force - 10.0) < 1.0 ? '#00FA9A' : Math.abs(force - 10.0) < 3.0 ? '#FFB800' : '#FF2A55'}
                  width={300}
                  height={100}
                />
              </div>
            )}

            {/* System Log */}
            {showLog && <SystemLog />}
          </div>

          {/* Right Bottom: Action Buttons */}
          <div className="glass-panel p-2 flex space-x-2 pointer-events-auto shadow-[0_0_20px_rgba(0,0,0,0.5)]">
            <button
              onClick={handleScanToggle}
              disabled={isHalted}
              className={`px-6 py-3 border rounded-xl font-bold text-sm tracking-wider transition-all hover:scale-105 active:scale-95 flex items-center justify-center min-w-[150px] disabled:opacity-30 disabled:cursor-not-allowed
                ${isScanning
                  ? 'bg-clinical-emerald/15 border-clinical-emerald/40 text-clinical-emerald hover:bg-clinical-emerald/30'
                  : 'bg-clinical-cyan/15 border-clinical-cyan/40 text-clinical-cyan hover:bg-clinical-cyan/30'}`}
            >
              {isScanning ? (
                <><Square className="w-4 h-4 mr-2" /> 停止扫描</>
              ) : (
                <><Play className="w-4 h-4 mr-2" /> 开始扫描</>
              )}
            </button>
            <button
              onClick={handleEStop}
              className="px-6 py-3 bg-clinical-error/15 hover:bg-clinical-error/30 border border-clinical-error/40
                         rounded-xl font-bold text-sm tracking-wider transition-all hover:scale-105 active:scale-95
                         min-w-[130px] text-clinical-error flex items-center justify-center"
            >
              <Zap className="w-4 h-4 mr-2" /> 紧急制动
            </button>
          </div>
        </div>
      </div>

      {/* === Layer 2: E-STOP Overlay === */}
      {isHalted && (
        <div className="absolute inset-0 z-50 flex items-center justify-center pointer-events-auto bg-black/40 backdrop-blur-sm">
          <div className="bg-clinical-error/90 p-10 rounded-3xl backdrop-blur-3xl shadow-[0_0_120px_rgba(255,42,85,0.8)] flex flex-col items-center space-y-5 animate-pulse max-w-lg">
            <div className="flex items-center space-x-6">
              <ShieldAlert className="w-16 h-16 text-white" />
              <div>
                <h2 className="text-4xl font-extrabold tracking-tight text-white">紧急制动</h2>
                <p className="font-mono mt-2 text-base text-white/80">所有执行器已锁定，等待操作员确认</p>
              </div>
            </div>
            <div className="flex items-center space-x-2 text-white/60 text-xs font-mono">
              <span>按 ESC 键</span>
              <span>或点击下方按钮解除</span>
            </div>
            <button
              onClick={handleReset}
              className="px-8 py-3 bg-white text-clinical-error font-bold tracking-widest rounded-xl hover:bg-gray-100 transition-all hover:scale-105 active:scale-95 text-sm"
            >
              解除制动 (OVERRIDE)
            </button>
          </div>
        </div>
      )}

      {/* === Layer 3: Status Bar === */}
      <StatusBar />

      {/* === Layer 4: Toast Notifications === */}
      <ToastContainer />
    </div>
  );
}
