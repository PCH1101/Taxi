# 01. Tổng Quan Dữ Liệu & Executive Dashboard (Silver Layer)

> **Tập dữ liệu:** `delta.silver.yellow_trips` (NYC Taxi Lakehouse)  
> **Quy mô:** **35,611,613 chuyến đi sạch** trong 366 ngày năm 2025.

---

## Biểu Đồ: silver_visual_dashboard.png

![Executive Dashboard](./silver_visual_dashboard.png)

---

## Giải Thích Chi Tiết 6 Góc Nhìn Phân Tích

| Khía cạnh | Chỉ số thực tế | Ý nghĩa kỹ thuật & Nghiệp vụ |
|---|---|---|
| **1. Thời lượng di chuyển** | Trung vị: **13.5 phút** (Trung bình: **17.2 phút**) | Hơn 85% chuyến đi trong nội đô Manhattan kết thúc dưới 25 phút. |
| **2. Cự ly di chuyển** | Trung vị: **1.72 dặm** (P90: **14.72 dặm**) | Taxi chủ yếu phục vụ nhu cầu đi lại cự ly ngắn; gờ phụ 12 - 18 dặm là tuyến sân bay. |
| **3. Tỷ lệ Tip thẻ tín dụng** | Đỉnh nhọn tại **15%, 20%, 25%, 30%** | Khách hàng chọn theo các nút bấm mặc định trên máy POS quẹt thẻ taxi. |
| **4. Cự ly vs Giá cước** | Taximeter: ~$3.00 + $3.50/mi; JFK: **$70 flat** | Phân tách đường dốc tính cước đồng hồ và đường ngang cước trọn gói sân bay JFK. |
| **5. Cước phí vs Tiền Tip** | Chùm tia phân bổ 20%, 25%, 30% | Tiền tip tăng theo tỷ lệ thuận khi cước phí tăng (cuốc sân bay $70 tip $14 - $21). |
| **6. Vận tốc theo 24 giờ** | Đáy ùn tắc: **8.5 - 9.8 mph** (17h - 19h) | Thung lũng tốc độ vào giờ tan tầm; phục hồi lên >20 mph vào rạng sáng. |
