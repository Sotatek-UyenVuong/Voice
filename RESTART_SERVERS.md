# 🔄 Restart Servers - Đã sửa CORS

## Vấn đề đã sửa
✅ CORS header bị duplicate → Đã fix trong `server.py`

## Cần làm ngay:

### 1. Restart Token Server

Trong terminal đang chạy `server.py`:
1. Nhấn `Ctrl + C` để stop
2. Chạy lại:
```bash
cd /Users/uyenvuong/Downloads/demo_voice/web_client
python server.py
```

### 2. Refresh React App

Trong browser (http://localhost:5173):
1. Nhấn `Cmd + R` hoặc F5 để refresh
2. Click "Connect & Talk"

---

## Các services cần chạy:

### ✅ Terminal 1: Voice Agent
```bash
cd /Users/uyenvuong/Downloads/demo_voice
python restaurant_agent.py dev
```
**Status:** Đang chạy ✓

### 🔄 Terminal 2: Token Server (CẦN RESTART)
```bash
cd /Users/uyenvuong/Downloads/demo_voice/web_client
python server.py
```
**Action:** Stop (Ctrl+C) và chạy lại!

### ✅ Terminal 3: React App
```bash
cd /Users/uyenvuong/Downloads/demo_voice/web-client-react
npm run dev
```
**Status:** Đang chạy tại http://localhost:5173 ✓

---

## Test sau khi restart:

1. ✅ Server.py đã khởi động lại
2. ✅ React app đã refresh
3. ✅ Click "Connect & Talk"
4. ✅ Token được generate thành công
5. ✅ Kết nối với LiveKit
6. ✅ Bắt đầu nói chuyện!

**Thử nói:** "Hello, I want to make a reservation"

🎉 **DONE!**

