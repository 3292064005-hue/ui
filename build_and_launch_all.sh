#!/bin/bash
set -e

echo "[+] Initiating SPINE ULTRASOUND PLATFORM Clinical Build..."

# 1. Build React/WebGL Frontend
echo "[+] Building Modern Frontend..."
cd ui_frontend
npm install
npm run build
cd ..

# 2. Compile Real-Time C++ Core
echo "[+] Compiling C++ 1ms Admittance Core..."
cd cpp_robot_core
mkdir -p build && cd build
cmake ..
make -j8
cd ../..

# 3. Setup Python Backend Environment
echo "[+] Constructing GPU Python Sandbox..."
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-clinical.txt

# 4. Triggering System Boot
echo "[+] =========================================="
echo "[+] ALL SYSTEMS GO. READY FOR CLINICAL USE."
echo "[+] Run './scripts/setup_ubuntu_rt.sh' to isolate CPUs."
echo "[+] Run 'uvicorn spine_ultrasound_ui.api_server:app --reload' to start the Headless API."
echo "[+] Run './cpp_robot_core/build/spine_robot_core' to engage Robot SDK."
echo "[+] =========================================="
