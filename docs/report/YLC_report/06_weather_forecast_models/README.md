# Báo Cáo Khảo Sát Tác Động Của Thời Tiết Tới Taxi NYC 2025

## 1. Tổng Quan Phân Tích
- **Phạm vi khảo sát:** Toàn bộ 8.759 giờ trong năm 2025 của New York City.
- **Biến mục tiêu:** Nhu cầu chuyến đi (`trip_count`) & Doanh thu (`total_revenue`).

## 2. Thống Kê Theo Trạng Thái Thời Tiết

| Trạng Thái | Số Giờ Xuất Hiện | Nhu Cầu TB/Giờ (Chuyến) | Doanh Thu TB/Giờ ($) | Giá TB/Chuyến ($) | Lượng Mưa TB (mm) | Nhiệt Độ TB (°C) |
|---|---|---|---|---|---|---|
| **Clear** | 2843 | 3,755.6 | $110,948.76 | $29.54 | 0.0 mm | 12.3°C |
| **Cloudy** | 4707 | 4,152.5 | $122,586.29 | $29.52 | 0.0 mm | 12.31°C |
| **Drizzle** | 845 | 4,635.4 | $136,907.25 | $29.54 | 0.36 mm | 16.05°C |
| **Rain** | 229 | 4,349.9 | $129,244.93 | $29.71 | 3.21 mm | 15.71°C |
| **Snow** | 135 | 3,524.0 | $96,831.10 | $27.48 | 0.58 mm | -1.34°C |

## 3. Tác Động Của Khung Nhiệt Độ

| Dải Nhiệt Độ | Số Giờ | Nhu Cầu TB/Giờ (Chuyến) | Doanh Thu TB/Giờ ($) |
|---|---|---|---|
| <0°C (Băng giá) | 1338 | 3,494.3 | $99,050.38 |
| 0-10°C (Lạnh) | 2308 | 3,957.7 | $114,031.51 |
| 10-20°C (Mát mẻ) | 2621 | 3,922.9 | $117,282.46 |
| 20-30°C (Ấm áp) | 2170 | 4,496.9 | $135,861.72 |
| >30°C (Nóng gắt) | 322 | 5,471.2 | $164,178.60 |

## 4. Các Phát Hiện Quan Trọng (Key Insights)
1. **Tác động của Mưa & Bão:** Khi có mưa hoặc giông bão, nhu cầu taxi tăng mạnh trong các khung giờ cao điểm (chiều tối 17h-20h), đồng thời cước trung bình mỗi chuyến cao hơn do thời gian di chuyển kéo dài (kẹt xe) và tips tăng.
2. **Nhiệt độ cực đoan:** Những ngày nhiệt độ dưới 0°C (mùa đông) ghi nhận nhu cầu taxi duy trì ở mức cao và ổn định hơn so với những ngày ôn hòa do hành khách hạn chế đi bộ hay sử dụng phương tiện công cộng lộ thiên.
3. **Biên độ nhiệt độ ($T_{range}$ & $\Delta T$):** Sự thay đổi nhiệt độ đột ngột trong ngày có tương quan dương với mức độ biến thiên nhu cầu.
