# 01. Tổng Quan Dữ Liệu & Executive Dashboard (FHVHV - Uber & Lyft)

> **Tập dữ liệu:** High-Volume For-Hire Vehicles (FHVHV) - NYC Taxi Lakehouse  
> **Quy mô:** **243,576,832 chuyến đi sạch** năm 2025 (~20M chuyến/tháng).  
> **Nền tảng chủ đạo:** **Uber (HV0003 ~75%)** và **Lyft (HV0005 ~25%)**.

---

## Biểu Đồ: silver_visual_dashboard.png

![Executive Dashboard](./silver_visual_dashboard.png)

---

## Giải Thích Chi Tiết 6 Góc Nhìn Phân Tích

| Khía cạnh | Chỉ số thực tế | Ý nghĩa kỹ thuật & Nghiệp vụ |
|---|---|---|
| **1. Thời lượng di chuyển** | Trung vị: **16.0 phút** (Trung bình: **19.8 phút**) | FHVHV phục vụ các chặng di chuyển dài hơn xe taxi truyền thống, kết nối các quận ngoài (Outer Boroughs). |
| **2. Cự ly di chuyển** | Trung vị: **2.76 dặm** (P90: **10.67 dặm**) | Cự ly trung vị cao gấp gần 3 lần Yellow Taxi (~1.72 dặm), phản ánh độ bao phủ toàn diện 5 quận của New York. |
| **3. Tỷ lệ Tip điện tử** | Tỷ lệ có tip: **~19.0%** (Trung vị khi tip: **18.9%**) | Khác với taxi truyền thống quẹt thẻ (tip >80%), ứng dụng gọi xe có tỷ lệ khách tip thấp hơn, tập trung tại các mốc gợi ý in-app (15%, 20%). |
| **4. Cự ly vs Giá cước** | Dynamic Surge Pricing: ~$8.00 + $2.50/mi | Giá cước thuật toán linh hoạt (Surge Pricing) theo nhu cầu thời gian thực thay vì đồng hồ công tơ mét cố định. |
| **5. Cước phí vs Tiền Tip** | Chùm tia phân bổ 15%, 20%, 25% | Khi khách hàng quyết định tip, tiền tip bám chặt theo các dải phần trăm mặc định trên giao diện app. |
| **6. Vận tốc theo 24 giờ** | Đáy ùn tắc: **~9.5 - 11 mph** (17h - 19h) | Vận tốc giảm mạnh vào giờ cao điểm tan tầm và tăng cao vào rạng sáng khi đường phố thông thoáng. |
