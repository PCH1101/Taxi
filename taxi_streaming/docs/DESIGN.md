---
name: Taxi Real-Time Analytics Design System
version: 1.0.0
colors:
  bg-base: "#020B18"
  bg-panel: "rgba(10, 22, 40, 0.88)"
  bg-card: "rgba(15, 23, 42, 0.8)"
  border-subtle: "rgba(56, 189, 248, 0.15)"
  border-glow: "rgba(0, 245, 255, 0.45)"
  cyan: "#00F5FF"
  sky: "#38BDF8"
  yellow: "#FACC15"
  green: "#22C55E"
  purple: "#A855F7"
  red: "#F43F5E"
  amber: "#F59E0B"
  text-primary: "#F1F5F9"
  text-muted: "#94A3B8"
typography:
  font-mono:
    fontFamily: "JetBrains Mono, monospace"
  font-sans:
    fontFamily: "Plus Jakarta Sans, -apple-system, BlinkMacSystemFont, sans-serif"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
---

# Hệ Thống Thiết Kế Dashboard Phân Tích Taxi Thời Gian Thực

## 1. Tổng Quan (Overview)
Bảng điều khiển đo xa không gian địa lý thời gian thực phong cách công nghệ cao phục vụ giám sát đội xe taxi và xe công nghệ New York City (Yellow Cab, Green Boro, FHVHV).

## 2. Bảng Màu Thiết Kế (Colors)
- Nền vũ trụ đêm sâu (Deep space midnight): `#020B18`, `rgba(10, 22, 40, 0.88)`
- Điểm nhấn Neon tương phản cao: Cyan (`#00F5FF`), Sky (`#38BDF8`), Yellow (`#FACC15`), Green (`#22C55E`), Purple (`#A855F7`)
- Phân cấp văn bản: Trắng sáng tương phản cao (`#F1F5F9`) và xám mờ (`#94A3B8`)

## 3. Kiểu Chữ (Typography)
- Giao diện người dùng chính: `Plus Jakarta Sans` đảm bảo khả năng đọc hiện đại, rõ nét
- Đo xa và số liệu Telemetry: `JetBrains Mono` phục vụ hiển thị số liệu bảng biểu và các chỉ số đo đạc chính xác

## 4. Chiều Sâu & Hiệu Ứng (Elevation & Depth)
- Các thẻ kính mờ bán trong suốt (Frosted glassmorphism, `backdrop-filter: blur(16px)`) kết hợp đường viền cyan phát sáng nhẹ
