# 🍽️ Restaurant Voice Agent - React Web Client

Beautiful web client built with React + Vite + LiveKit SDK.

## ✅ Đã cài đặt

- React 18
- Vite
- LiveKit Client SDK
- LiveKit React Components
- LiveKit Components Styles

## 🚀 Cách chạy

### Bước 1: Đảm bảo services đang chạy

#### Terminal 1: Voice Agent
```bash
cd /Users/uyenvuong/Downloads/demo_voice
python restaurant_agent.py dev
```

#### Terminal 2: Token Server
```bash
cd /Users/uyenvuong/Downloads/demo_voice/web_client
python server.py
```

### Bước 2: Chạy React app

#### Terminal 3: React Dev Server
```bash
cd /Users/uyenvuong/Downloads/demo_voice/web-client-react
npm run dev
```

App sẽ chạy tại: **http://localhost:5173**

## 📋 Tính năng

- ✅ Giao diện đẹp, hiện đại
- ✅ Real-time voice conversation với AI agent
- ✅ Status indicators (listening, thinking, speaking)
- ✅ Voice visualizer animations
- ✅ Menu display
- ✅ Token generation tự động
- ✅ Responsive design
- ✅ Error handling

## 🎯 Cách sử dụng

1. Mở http://localhost:5173 trong browser
2. Nhập room name (mặc định: `test-room`)
3. Nhập tên của bạn
4. Click "Connect & Talk"
5. Cho phép microphone access
6. Bắt đầu nói chuyện!

### Câu mẫu:
- "Hello, I want to make a reservation"
- "I'd like to order pizza for takeaway"
- "What's on the menu?"

## 📦 Build cho production

```bash
npm run build
```

Dist folder sẽ được tạo trong `dist/`, bạn có thể deploy lên bất kỳ static hosting nào (Vercel, Netlify, GitHub Pages, etc.)

## 🛠️ Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool & dev server
- **LiveKit Client SDK** - WebRTC & real-time communication
- **LiveKit React Components** - Pre-built React hooks & components
- **Axios** - HTTP client for token generation

## 📝 Menu

- 🍕 Pizza: $10
- 🥗 Salad: $5
- 🍨 Ice Cream: $3
- ☕ Coffee: $2

## 🎭 Agent Features

### Greeter
- Chào khách
- Hiểu yêu cầu (reservation/takeaway)

### Reservation
- Lấy thông tin đặt bàn
- Thu thập tên, số điện thoại, thời gian

### Takeaway  
- Nhận order đồ ăn
- Xác nhận order

### Checkout
- Tính tiền
- Thu thập thông tin thanh toán

## 🔧 Troubleshooting

### Agent không join room?
- Kiểm tra `restaurant_agent.py dev` đang chạy
- Xem logs trong terminal

### Token generation failed?
- Kiểm tra `server.py` đang chạy tại port 8000
- Kiểm tra `.env` có đầy đủ credentials

### Microphone không hoạt động?
- Cho phép microphone access trong browser
- Kiểm tra microphone settings

## 📚 Documentation

- [LiveKit Docs](https://docs.livekit.io/)
- [LiveKit React Components](https://docs.livekit.io/reference/components/react/)
- [Vite Documentation](https://vitejs.dev/)

## 🎉 Enjoy!

Built with ❤️ using LiveKit Agents Framework
