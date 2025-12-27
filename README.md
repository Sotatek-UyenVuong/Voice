# 🍽️ Bistro Bliss - Voice AI Restaurant Agent

Demo ứng dụng Voice AI cho nhà hàng sử dụng **LiveKit Agents SDK** với khả năng đặt bàn, gọi món mang về và thanh toán qua giọng nói.

## 📋 Tính năng

- 🎙️ **Voice Chat**: Giao tiếp với AI agent bằng giọng nói
- 📅 **Đặt bàn**: Đặt chỗ trước với số người, ngày giờ
- 🥡 **Gọi món mang về**: Đặt món takeaway
- 💳 **Thanh toán**: Xác nhận và hoàn tất đơn hàng
- 📱 **Telegram**: Gửi thông báo đơn hàng tự động

## 🛠️ Công nghệ sử dụng

| Component | Technology |
|-----------|------------|
| **Voice Agent** | LiveKit Agents SDK 1.3.6 |
| **LLM** | Google Gemini 2.5 Flash |
| **STT** | Deepgram / Soniox |
| **TTS** | ElevenLabs / Google TTS |
| **VAD** | Silero |
| **Frontend** | React + Vite / Static HTML |
| **Real-time** | LiveKit Cloud |

## 📁 Cấu trúc dự án

```
demo_voice/
├── restaurant_agent.py    # Main voice agent
├── https_server.py        # HTTPS server cho static files
├── inventory.json         # Menu items database
├── manage_inventory.py    # Quản lý kho hàng
├── manage_rooms.py        # Quản lý phòng LiveKit
├── requirements.txt       # Python dependencies
├── Homepage.html          # Trang chủ + Voice Chat
├── Menu.html              # Menu nhà hàng
├── About.html             # Giới thiệu
├── Blog.html              # Blog
├── BlogDetail.html        # Chi tiết blog
└── web-client-react/      # React client (alternative)
    ├── src/
    │   ├── App.jsx
    │   └── components/
    ├── package.json
    └── vite.config.js
```

## ⚙️ Cài đặt

### 1. Clone & Setup Python Environment

```bash
# Tạo và kích hoạt môi trường ảo
conda create -n pana python=3.10
conda activate pana

# Cài đặt dependencies
cd /home/sotatek/Documents/Uyen/demo_voice
pip install -r requirements.txt
```

### 2. Cấu hình Environment Variables

Tạo file `.env`:

```env
# LiveKit Configuration
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# Google Gemini
GEMINI_API_KEY=your_gemini_api_key

# Deepgram STT
DEEPGRAM_API_KEY=your_deepgram_api_key

# ElevenLabs TTS
ELEVEN_API_KEY=your_elevenlabs_api_key

# Soniox STT (optional)
SONIOX_API_KEY=your_soniox_api_key

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### 3. Cài đặt Node.js (cho React client)

```bash
# Cài NVM nếu chưa có
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Cài Node.js 20.19.6
nvm install 20.19.6
nvm use 20.19.6

# Cài dependencies cho React client
cd web-client-react
npm install
```

## 🚀 Chạy ứng dụng

### Cách 1: Sử dụng Tmux (Recommended)

Mở 2 terminal sessions:

**Terminal 1 - Voice Agent:**
```bash
# Tạo tmux session
tmux new -s sotayummyserver

# Chạy agent
conda activate pana
cd /home/sotatek/Documents/Uyen/demo_voice
python restaurant_agent.py dev
```

**Terminal 2 - Web Server:**
```bash
# Tạo tmux session
tmux new -s sotayummy

# Chạy HTTPS server
conda activate pana
cd /home/sotatek/Documents/Uyen/demo_voice
python https_server.py
```

### Cách 2: Chạy thủ công

**Bước 1: Chạy Voice Agent**
```bash
conda activate pana
cd /home/sotatek/Documents/Uyen/demo_voice
python restaurant_agent.py dev
```

**Bước 2: Chạy Web Server** (terminal khác)
```bash
cd /home/sotatek/Documents/Uyen/demo_voice
python https_server.py
```

### Cách 3: Sử dụng React Client (Alternative)

```bash
# Terminal 1: Agent
conda activate pana
python restaurant_agent.py dev

# Terminal 2: React Client
source ~/.nvm/nvm.sh && nvm use 20.19.6
cd /home/sotatek/Documents/Uyen/demo_voice/web-client-react
npm run dev
```

Hoặc ngắn gọn:
```bash
cd web-client-react
nvm use  # tự động dùng Node 20.19.6 từ .nvmrc
npm run dev
```

## 🌐 Truy cập ứng dụng

| Interface | URL |
|-----------|-----|
| **Homepage (HTTPS)** | `https://192.168.200.22:8099/Homepage.html` |
| **React Client** | `https://localhost:5173` |
| **Token API** | `https://192.168.200.22:8089/api/token` |

> ⚠️ **Lưu ý**: Do sử dụng self-signed certificate, bạn cần accept certificate trong browser lần đầu.

## 🎯 Sử dụng

1. Truy cập `https://192.168.200.22:8099/Homepage.html`
2. Click nút **"Book A Table"**
3. Cho phép truy cập microphone
4. Nói chuyện với AI agent:
   - *"Tôi muốn đặt bàn cho 4 người"*
   - *"Cho tôi xem menu"*
   - *"Tôi muốn đặt món mang về"*
   - *"Thanh toán"*

## 📱 Tmux Commands

```bash
# Attach vào session
tmux attach -t sotayummyserver
tmux attach -t sotayummy

# Xem tất cả sessions
tmux ls

# Detach khỏi session
Ctrl+B, D

# Kill session
tmux kill-session -t session_name
```

## 🔧 Troubleshooting

### Lỗi Port đã được sử dụng
```bash
# Tìm process đang dùng port
lsof -i :8089
lsof -i :8099

# Kill process
kill -9 <PID>
```

### Lỗi "no candidates in the response" (Gemini)
Đổi model từ `gemini-2.5-flash-lite` sang `gemini-2.5-flash` hoặc `gemini-2.0-flash` trong `restaurant_agent.py`.

### Microphone không hoạt động
- Đảm bảo sử dụng **HTTPS** (không phải HTTP)
- Browser yêu cầu secure context để truy cập microphone
- Truy cập qua `localhost` hoặc domain với SSL certificate

### Agent không join room
Kiểm tra:
1. Agent đã registered thành công (xem log)
2. `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` đúng
3. Room được tạo trước khi dispatch agent

## 📄 License

MIT License

## 👤 Author

Sotatek - Demo Voice AI Restaurant Agent

