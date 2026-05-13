#!/bin/bash
# ============================================================
#    KIRO AUTO-REGISTRATION TOOL - CÀI ĐẶT NHANH (Linux/VPS)
#    Tự động cài đặt mọi thứ cần thiết và khởi động tool
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}   KIRO AUTO-REGISTRATION TOOL - CÀI ĐẶT NHANH${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# === BƯỚC 1: Tìm Python phù hợp ===
echo -e "${YELLOW}[1/6] Đang tìm Python trên máy...${NC}"

PYTHON_CMD=""

# Thử các lệnh Python theo thứ tự ưu tiên
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VER=$($cmd --version 2>&1 | grep -oP '\d+\.\d+')
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON_CMD="$cmd"
            echo -e "   Đã tìm thấy: $($cmd --version 2>&1)"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}[LỖI] Không tìm thấy Python 3.10+ trên máy!${NC}"
    echo ""
    echo "Cài Python trên Ubuntu/Debian:"
    echo "   sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip"
    echo ""
    echo "Cài Python trên CentOS/RHEL:"
    echo "   sudo yum install -y python3.11"
    echo ""
    exit 1
fi
echo ""

# === BƯỚC 2: Cài dependencies hệ thống (cho Playwright) ===
echo -e "${YELLOW}[2/6] Kiểm tra và cài dependencies hệ thống...${NC}"

# Kiểm tra nếu có quyền root/sudo
if [ "$(id -u)" = "0" ] || command -v sudo &>/dev/null; then
    SUDO_CMD=""
    if [ "$(id -u)" != "0" ]; then
        SUDO_CMD="sudo"
    fi

    # Detect OS
    if [ -f /etc/debian_version ]; then
        echo "   Phát hiện Debian/Ubuntu..."
        $SUDO_CMD apt-get update -qq
        $SUDO_CMD apt-get install -y -qq python3-venv python3-pip \
            libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
            libcups2 libdrm2 libxkbcommon0 libatspi2.0-0 \
            libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
            libgbm1 libpango-1.0-0 libcairo2 libasound2 \
            2>/dev/null || true
    elif [ -f /etc/redhat-release ]; then
        echo "   Phát hiện CentOS/RHEL..."
        $SUDO_CMD yum install -y python3-pip nss nspr atk cups-libs \
            libdrm libxkbcommon at-spi2-atk libXcomposite libXdamage \
            libXfixes libXrandr mesa-libgbm pango cairo alsa-lib \
            2>/dev/null || true
    fi
    echo -e "   ${GREEN}Đã cài xong dependencies hệ thống${NC}"
else
    echo -e "   ${YELLOW}Không có quyền sudo, bỏ qua cài system deps${NC}"
    echo "   (Nếu Playwright lỗi, chạy: sudo apt install -y libnss3 libgbm1)"
fi
echo ""

# === BƯỚC 3: Tạo Virtual Environment ===
echo -e "${YELLOW}[3/6] Tạo môi trường ảo (venv)...${NC}"

if [ -d "venv" ]; then
    echo "   Đã có venv, bỏ qua..."
else
    $PYTHON_CMD -m venv venv
    echo -e "   ${GREEN}Đã tạo venv thành công!${NC}"
fi

# Kích hoạt venv
source venv/bin/activate
echo ""

# === BƯỚC 4: Cài đặt Python dependencies ===
echo -e "${YELLOW}[4/6] Cài đặt thư viện Python...${NC}"

pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo -e "   ${GREEN}Đã cài xong dependencies!${NC}"
echo ""

# === BƯỚC 5: Cài Playwright Chromium ===
echo -e "${YELLOW}[5/6] Cài đặt trình duyệt Chromium (Playwright)...${NC}"

playwright install chromium 2>/dev/null || {
    echo -e "   ${YELLOW}Thử cài với deps...${NC}"
    playwright install-deps chromium 2>/dev/null || true
    playwright install chromium
}
echo -e "   ${GREEN}Đã cài xong Chromium!${NC}"
echo ""

# === BƯỚC 6: Tạo thư mục và file tiện ích ===
echo -e "${YELLOW}[6/6] Tạo thư mục và scripts tiện ích...${NC}"

mkdir -p data logs

# Tạo script khởi động nhanh
cat > start.sh << 'STARTEOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python main.py "$@"
STARTEOF
chmod +x start.sh

# Tạo script chạy scheduler ngầm
cat > start-scheduler.sh << 'SCHEDEOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "Đang khởi động Kiro Auto-Reg Scheduler..."
echo "Logs tại: logs/kiro-auto.log"
echo "Dừng: kill $(cat scheduler.pid)"
nohup python main.py schedule > logs/scheduler-output.log 2>&1 &
echo $! > scheduler.pid
echo "PID: $(cat scheduler.pid)"
echo "Đã khởi động thành công!"
SCHEDEOF
chmod +x start-scheduler.sh

# Tạo script dừng scheduler
cat > stop-scheduler.sh << 'STOPEOF'
#!/bin/bash
cd "$(dirname "$0")"
if [ -f scheduler.pid ]; then
    PID=$(cat scheduler.pid)
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        rm scheduler.pid
        echo "Đã dừng scheduler (PID: $PID)"
    else
        echo "Scheduler không chạy (PID $PID đã tắt)"
        rm scheduler.pid
    fi
else
    echo "Không tìm thấy scheduler.pid"
fi
STOPEOF
chmod +x stop-scheduler.sh

echo -e "   ${GREEN}Đã tạo scripts tiện ích!${NC}"
echo ""

# === HOÀN TẤT ===
echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}   CÀI ĐẶT HOÀN TẤT!${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo "   Các lệnh sử dụng:"
echo "   ----------------------------------------------------------"
echo "   Đăng ký 1 account:      ./start.sh register"
echo "   Đăng ký 5 account:      ./start.sh register -n 5"
echo "   Chạy scheduler ngầm:    ./start-scheduler.sh"
echo "   Dừng scheduler:         ./stop-scheduler.sh"
echo "   Xem danh sách:          ./start.sh list"
echo "   Chuyển account:         ./start.sh switch [ID]"
echo "   Xem trạng thái:         ./start.sh status"
echo "   ----------------------------------------------------------"
echo ""

# Hiển thị status
echo -e "${YELLOW}Đang kiểm tra hệ thống...${NC}"
python main.py status 2>/dev/null || echo "(Database mới, chưa có account)"
echo ""
echo -e "${GREEN}Sẵn sàng sử dụng! Chạy: ./start.sh register${NC}"
