# Kiro Auto-Registration Tool - Architecture Plan

## Mục tiêu
Tách từ dự án `auto_reg` hiện tại thành một tool **chuyên biệt cho Kiro** (AWS Builder ID), hoàn toàn **miễn phí**, tự động hóa cao, không phụ thuộc dịch vụ trả phí.

---

## 1. Phân tích hệ thống hiện tại

### Những gì cần giữ lại (từ auto_reg):
| Module | Mục đích | Giữ/Bỏ |
|--------|----------|---------|
| `platforms/kiro/core.py` | Logic đăng ký Kiro qua Playwright | ✅ Giữ + tối ưu |
| `platforms/kiro/switch.py` | Chuyển đổi account Kiro IDE | ✅ Giữ |
| `core/base_mailbox.py` | Factory pattern cho email providers | ✅ Giữ (chỉ free providers) |
| `core/proxy_pool.py` | Quản lý proxy pool | ✅ Giữ (tùy chọn) |
| `core/task_runtime.py` | Task control (stop/skip) | ✅ Giữ |
| `core/scheduler.py` | Lịch chạy tự động | ✅ Giữ + đơn giản hóa |

### Những gì BỎ (tốn tiền/không cần):
| Module | Lý do bỏ |
|--------|----------|
| `core/luckmail/` | Dịch vụ email TRẢ PHÍ |
| `YesCaptcha` integration | Dịch vụ giải CAPTCHA TRẢ PHÍ |
| `skymail`, `moemail`, `maliapi`, `gptmail` | Tất cả yêu cầu API key trả phí |
| Frontend React | Không cần UI phức tạp, chạy CLI |
| FastAPI server | Không cần REST API |
| Tất cả platforms khác (chatgpt, cursor, grok, trae...) | Chỉ chuyên Kiro |

---

## 2. Giải pháp Email MIỄN PHÍ

### Phương án chính (ưu tiên):

#### A. TempMail.lol (FREE, không cần config)
- Tự tạo email tạm thời
- Nhận verification code tự động
- Không cần API key, không tốn phí
- **Hạn chế**: Domain bị block trên một số service

#### B. Cloudflare Worker Email (Self-hosted FREE)
- Deploy trên Cloudflare Free Tier (miễn phí)
- Dùng domain riêng (mua domain ~$1/năm hoặc dùng free subdomain)
- Không giới hạn số lượng email
- **Ưu điểm**: Domain sạch, ít bị block

#### C. Guerrilla Mail (FREE backup)
- API miễn phí
- Tự động tạo email + nhận code
- Backup khi TempMail.lol down

#### D. Mail.tm (FREE backup)
- RESTful API miễn phí
- Tạo account + đọc inbox
- Rate limit cao

### Chiến lược auto-rotate:
```
tempmail_lol → mail_tm → guerrilla → cfworker (fallback)
```
Nếu provider nào fail → tự động chuyển sang provider tiếp theo.

---

## 3. Giải pháp CAPTCHA MIỄN PHÍ

### Local Solver (Camoufox-based)
- Chạy local browser (camoufox/playwright)
- Tự động solve Turnstile/reCAPTCHA
- **Chi phí: $0** (chỉ tốn CPU local)

### Playwright Stealth
- Dùng `playwright-stealth` để tránh detection
- Random fingerprint (UA, viewport, timezone, locale)
- Human-like typing/clicking delays

---

## 4. Kiến trúc mới (Standalone)

```
kiro-auto-reg/
├── main.py                    # CLI entry point
├── config.yaml                # Cấu hình (proxy, schedule, email provider...)
├── requirements.txt
├── Dockerfile
│
├── core/
│   ├── __init__.py
│   ├── config.py              # Load/validate config
│   ├── db.py                  # SQLite storage (accounts, logs)
│   ├── scheduler.py           # Cron-like scheduler
│   ├── task_runner.py         # Task execution engine
│   └── proxy_pool.py          # Optional proxy management
│
├── email_providers/
│   ├── __init__.py
│   ├── base.py                # Abstract email provider
│   ├── tempmail_lol.py        # TempMail.lol (FREE)
│   ├── mail_tm.py             # Mail.tm (FREE)
│   ├── guerrilla.py           # Guerrilla Mail (FREE)
│   └── cfworker.py            # Cloudflare Worker (self-hosted FREE)
│
├── captcha/
│   ├── __init__.py
│   ├── local_solver.py        # Local Turnstile solver
│   └── stealth.py             # Anti-detection utilities
│
├── kiro/
│   ├── __init__.py
│   ├── register.py            # Kiro registration flow (Playwright)
│   ├── switch.py              # Switch Kiro IDE account
│   ├── token_manager.py       # Token refresh/validate
│   └── fingerprint.py         # Browser fingerprint randomization
│
└── utils/
    ├── __init__.py
    ├── logger.py              # Structured logging
    ├── password.py            # Password generator
    └── retry.py               # Retry with backoff
```

---

## 5. Flow đăng ký tự động

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Scheduler  │───▶│  Task Runner     │───▶│  Email Provider  │
│  (cron)     │    │  (concurrency)   │    │  (auto-rotate)   │
└─────────────┘    └──────────────────┘    └─────────────────┘
                           │                        │
                           ▼                        ▼
                   ┌──────────────────┐    ┌─────────────────┐
                   │  Kiro Register   │◀───│  Get Email +     │
                   │  (Playwright)    │    │  Wait OTP Code   │
                   └──────────────────┘    └─────────────────┘
                           │
                           ▼
                   ┌──────────────────┐
                   │  Save Account    │───▶ SQLite DB
                   │  + Switch IDE    │───▶ ~/.aws/sso/cache/
                   └──────────────────┘
```

### Chi tiết flow:
1. **Scheduler** trigger task theo lịch (mỗi X phút/giờ)
2. **Task Runner** tạo task mới, chọn email provider (auto-rotate nếu fail)
3. **Email Provider** tạo email tạm miễn phí
4. **Kiro Register** (Playwright headless):
   - Mở `https://app.kiro.dev/signin`
   - Điền email → Submit
   - Chờ OTP từ email provider (polling)
   - Điền OTP → Set password → Hoàn tất
   - Capture tokens (accessToken, refreshToken, clientId, clientSecret)
5. **Save**: Lưu account vào SQLite + tự động switch Kiro IDE

---

## 6. Tính năng tự động hóa

| Tính năng | Mô tả |
|-----------|--------|
| **Auto Email** | Tự tạo email mới cho mỗi lần đăng ký, không cần input |
| **Auto OTP** | Polling inbox, tự động extract verification code |
| **Auto Retry** | Fail → retry với email/proxy khác (max 3 lần) |
| **Auto Rotate** | Email provider fail → chuyển provider tiếp |
| **Auto Schedule** | Chạy theo lịch (mỗi 30 phút, mỗi giờ, tùy config) |
| **Auto Switch** | Đăng ký xong → tự động switch Kiro IDE sang account mới |
| **Auto Token Refresh** | Tự động refresh token trước khi hết hạn |
| **Proxy Rotation** | Tự động xoay proxy (nếu có) |
| **Fingerprint Random** | Mỗi lần đăng ký = browser fingerprint khác nhau |

---

## 7. Cấu hình (config.yaml)

```yaml
# Kiro Auto-Registration Configuration
kiro:
  headless: true              # true = không hiện browser
  max_concurrent: 2           # Số task chạy song song
  retry_times: 3              # Số lần retry mỗi task
  otp_timeout: 120            # Giây chờ verification code
  register_delay: 30          # Giây nghỉ giữa các lần đăng ký

email:
  providers:                  # Thứ tự ưu tiên
    - tempmail_lol
    - mail_tm
    - guerrilla
    - cfworker
  cfworker:                   # Nếu dùng Cloudflare Worker
    api_url: ""
    domain: ""

proxy:
  enabled: false
  urls: []                    # Danh sách proxy URLs
  # Hoặc file chứa proxy list
  file: ""

schedule:
  enabled: true
  interval_minutes: 60        # Chạy mỗi 60 phút
  max_accounts_per_run: 1     # Số account tạo mỗi lần

auto_switch:
  enabled: true               # Tự động switch Kiro IDE
  restart_ide: false          # Tự động restart IDE sau switch

logging:
  level: INFO
  file: logs/kiro-auto.log
```

---

## 8. Chi phí = $0

| Thành phần | Chi phí |
|-----------|---------|
| Email (TempMail.lol / Mail.tm) | FREE |
| CAPTCHA (Local Solver) | FREE |
| Database (SQLite local) | FREE |
| Browser (Playwright/Camoufox) | FREE |
| Proxy (tùy chọn, không bắt buộc) | FREE (nếu không dùng) |
| **TỔNG** | **$0** |

---

## 9. Yêu cầu hệ thống

- Python 3.10+
- Playwright (chromium)
- ~500MB RAM cho headless browser
- Kết nối internet
- (Tùy chọn) Proxy nếu IP bị rate limit

---

## 10. Lộ trình triển khai

### Phase 1: Core (MVP)
- [x] Architecture plan
- [ ] Free email providers (tempmail_lol, mail_tm)
- [ ] Kiro registration core (từ existing code)
- [ ] Local CAPTCHA solver
- [ ] SQLite storage
- [ ] CLI interface

### Phase 2: Automation
- [ ] Scheduler (cron-like)
- [ ] Auto-rotate email providers
- [ ] Auto-retry logic
- [ ] Auto-switch Kiro IDE

### Phase 3: Enhancement
- [ ] Proxy pool support
- [ ] Token auto-refresh
- [ ] Docker deployment
- [ ] Logging & monitoring
