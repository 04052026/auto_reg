# Hướng dẫn sử dụng Kiro Auto-Registration

Tool tự động đăng ký tài khoản Kiro (AWS Builder ID) - **MIỄN PHÍ 100%**, không cần dịch vụ trả phí.

---

## Yêu cầu hệ thống

- Python 3.10 trở lên
- ~500MB RAM (cho browser headless)
- Kết nối internet
- (Tuỳ chọn) Proxy nếu IP bị rate limit

---

## Cài đặt

```bash
# 1. Vào thư mục project
cd kiro_auto

# 2. Cài dependencies
pip install -r requirements.txt

# 3. Cài Playwright browser (bắt buộc, chỉ lần đầu)
playwright install chromium
```

---

## Các lệnh sử dụng

### 1. Đăng ký tài khoản mới

```bash
# Đăng ký 1 tài khoản (mặc định)
python main.py register

# Đăng ký 5 tài khoản liên tiếp
python main.py register -n 5

# Đăng ký 3 tài khoản, chạy song song 2 luồng
python main.py register -n 3 -c 2

# Đăng ký với proxy
python main.py register --proxy http://user:pass@ip:port

# Hiện browser (không headless) để debug
python main.py register --no-headless

# Chỉ dùng 1 email provider cụ thể
python main.py register --provider tempmail_lol
```

### 2. Chạy tự động theo lịch (Scheduler)

```bash
# Tự động đăng ký mỗi 60 phút (mặc định)
python main.py schedule

# Tự động mỗi 30 phút, 2 account/lần
python main.py schedule --interval 30 --max-per-run 2

# Dừng: nhấn Ctrl+C
```

### 3. Xem danh sách tài khoản đã đăng ký

```bash
python main.py list
```

Kết quả:
```
ID    Email                                    Status       Created
--------------------------------------------------------------------------------
5     kiroabc12@tempmail.lol                   registered   2026-05-13 10:30:00
4     kiroxyz45@mail.tm                        registered   2026-05-13 09:15:00
...
Total: 5 accounts
```

### 4. Chuyển tài khoản cho Kiro IDE

```bash
# Chuyển sang tài khoản số 3
python main.py switch 3
```

Lệnh này sẽ ghi token vào `~/.aws/sso/cache/kiro-auth-token.json`, Kiro IDE sẽ tự động nhận account mới.

### 5. Làm mới Token (Refresh)

```bash
# Refresh token cho account mới nhất
python main.py refresh

# Refresh token cho account cụ thể
python main.py refresh 3
```

### 6. Xem trạng thái hệ thống

```bash
python main.py status
```

### 7. Xem cấu hình hiện tại

```bash
python main.py config
```

---

## Cấu hình (config.yaml)

Sửa file `config.yaml` để tuỳ chỉnh:

```yaml
kiro:
  headless: true              # true = ẩn browser, false = hiện browser
  max_concurrent: 2           # Số luồng chạy song song tối đa
  retry_times: 3              # Số lần thử lại mỗi lần đăng ký
  otp_timeout: 120            # Giây chờ mã xác thực (verification code)
  register_delay: 30          # Giây nghỉ giữa các lần đăng ký

email:
  providers:                  # Thứ tự ưu tiên (tất cả MIỄN PHÍ)
    - tempmail_lol            # Mặc định, không cần config
    - mail_tm                 # Backup, không cần config
    - guerrilla               # Backup thứ 2
    - cfworker                # Self-hosted trên Cloudflare (miễn phí)
  cfworker:                   # Chỉ cần nếu dùng Cloudflare Worker
    api_url: ""               # URL API của CF Worker
    domain: ""                # Domain nhận email

proxy:
  enabled: false              # true = sử dụng proxy
  urls:                       # Danh sách proxy
    - http://user:pass@ip:port
  file: ""                    # Hoặc file chứa proxy (1 dòng/proxy)

schedule:
  enabled: true
  interval_minutes: 60        # Chạy mỗi 60 phút
  max_accounts_per_run: 1     # Số account tạo mỗi lần chạy

auto_switch:
  enabled: true               # Tự động switch Kiro IDE sau đăng ký
  restart_ide: false          # Tự động restart Kiro IDE

logging:
  level: INFO                 # DEBUG, INFO, WARNING, ERROR
  file: logs/kiro-auto.log
```

---

## Biến môi trường (tuỳ chọn)

Có thể override config bằng biến môi trường:

```bash
# Dùng proxy
export KIRO_PROXY_URL=http://user:pass@ip:port

# Tắt headless
export KIRO_HEADLESS=false

# Dùng Cloudflare Worker email
export KIRO_CFWORKER_URL=https://your-worker.workers.dev
export KIRO_CFWORKER_DOMAIN=yourdomain.com
```

---

## Email Provider (Tất cả MIỄN PHÍ)

| Provider | Cần config? | Mô tả |
|----------|-------------|--------|
| `tempmail_lol` | Không | TempMail.lol - tạo email tạm tự động |
| `mail_tm` | Không | Mail.tm - có REST API đầy đủ |
| `guerrilla` | Không | Guerrilla Mail - backup ổn định |
| `cfworker` | Có (api_url, domain) | Cloudflare Worker tự host - domain sạch nhất |

**Cơ chế auto-rotate**: Nếu provider đầu fail → tự động chuyển sang provider tiếp theo.

---

## Chạy với Docker

```bash
# Build image
docker build -t kiro-auto .

# Chạy scheduler (chạy ngầm, tự đăng ký mỗi giờ)
docker run -d --name kiro-auto \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  kiro-auto

# Xem logs
docker logs -f kiro-auto

# Dừng
docker stop kiro-auto
```

---

## Xử lý lỗi thường gặp

| Lỗi | Nguyên nhân | Cách khắc phục |
|-----|-------------|----------------|
| `All email providers failed` | Tất cả provider đều bị chặn/down | Thử lại sau, hoặc thêm proxy |
| `Email input not found` | Kiro thay đổi giao diện | Cập nhật code mới nhất |
| `OTP input timeout` | Email chưa nhận được code | Tăng `otp_timeout` trong config |
| `OIDC client registration failed` | AWS rate limit | Đổi IP/proxy, chờ vài phút |
| `Timeout waiting for next step` | Trang load chậm | Thêm proxy, hoặc thử lại |

---

## Cấu trúc dữ liệu

- **Database**: `data/kiro_accounts.db` (SQLite)
- **Logs**: `logs/kiro-auto.log`
- **Token Kiro IDE**: `~/.aws/sso/cache/kiro-auth-token.json`

---

## Chi phí: $0

| Thành phần | Chi phí |
|-----------|---------|
| Email (TempMail.lol / Mail.tm / Guerrilla) | MIỄN PHÍ |
| CAPTCHA solver (Playwright local) | MIỄN PHÍ |
| Database (SQLite) | MIỄN PHÍ |
| Browser (Playwright Chromium) | MIỄN PHÍ |
| Proxy (tuỳ chọn) | MIỄN PHÍ nếu không dùng |
| **TỔNG CỘNG** | **$0** |
