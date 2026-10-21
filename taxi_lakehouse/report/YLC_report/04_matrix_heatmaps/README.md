# 04. Ma Trận Nhiệt Thời Gian & Tương Quan (Heatmaps Analytics)

> **Tập dữ liệu:** `delta.silver.yellow_trips` (Tầng Silver)  
> **Mục tiêu:** Khám phá các quy luật định kỳ theo tuần/giờ, ma trận tương quan đa biến và tính mùa vụ cả năm.

---

## Danh Sách 6 Biểu Đồ Heatmap

---

### 0. `00_heatmap_master_dashboard.png` - Dashboard Ma Trận Nhiệt Tổng Hợp
![00 Master Heatmap Dashboard](./00_heatmap_master_dashboard.png)

Tổng hợp 4 chiều phân tích: Nhu cầu tuần, Điểm nghẽn ùn tắc, Luồng liên quận, và Phân khúc tiền tip.

---

### 1. `01_heatmap_weekly_demand.png` - Nhu Cầu Theo Tuần (Thứ trong tuần x Giờ trong ngày)
![01 Weekly Demand](./01_heatmap_weekly_demand.png)

- **Trục Y:** Thứ trong tuần (Thứ 2 -> Chủ Nhật) | **Trục X:** 24 khung giờ (00:00 -> 23:00).
- **Giải thích:**
  - **Ngày trong tuần (Thứ 2 - Thứ 6):** Tập trung vào giờ tan tầm **17:00 - 19:00** (vượt trên **400k - 440k chuyến/giờ**).
  - **Cuối tuần (Thứ 7 - Chủ Nhật):** Đỉnh chuyển dịch sang **đêm muộn Thứ 6 và Thứ 7 (21:00 - 02:00 sáng)** do nhu cầu vui chơi, giải trí về đêm.

---

### 2. `02_heatmap_weekly_speed.png` - Bản Đồ Ùn Tắc Giao Thông Tuần (Vận Tốc Trung Bình mph)
![02 Weekly Speed](./02_heatmap_weekly_speed.png)

- **Bảng màu RdYlBu_r:** Đỏ = Tắc đường nặng (<10 mph), Vàng = Trung bình, Xanh = Thông thoáng (>20 mph).
- **Giải thích:**
  - **Kẹt xe nghiêm trọng nhất:** Chiều Thứ Năm và Thứ Sáu lúc 16:00 - 19:00 với vận tốc chạm đáy **7.8 - 8.3 mph**.
  - **Thông thoáng nhất:** Khung giờ rạng sáng 01:00 - 05:00 và toàn bộ ngày Chủ Nhật (duy trì 13 - 25 mph).

---

### 3. `03_heatmap_feature_correlation.png` - Ma Trận Tương Quan Pearson
![03 Feature Correlation](./03_heatmap_feature_correlation.png)

- **Giải thích:**
  - `Distance` <-> `Fare`: $r = \mathbf{0.94}$ (Cước phí phụ thuộc gần như tuyệt đối vào cự ly).
  - `Distance` <-> `Tolls`: $r = \mathbf{0.68}$ (Cuốc đi xa thường qua cầu/hầm thu phí).
  - `passenger_count` hoàn toàn độc lập với cước phí ($r = \mathbf{0.01}$).

---

### 4. `04_heatmap_fare_vs_hour_tipping.png` - Tỷ Lệ Tip Theo Mức Cước x Khung Giờ
![04 Fare vs Hour Tipping](./04_heatmap_fare_vs_hour_tipping.png)

- **Giải thích:**
  - Cuốc xe ngắn **dưới $10** có tỷ lệ tip % cao nhất (**26.5% - 28.2%**) do thói quen làm tròn tiền boa tối thiểu ($2.00 hoặc $3.00 trên cuốc $8.00 tương đương 25% - 37%).
  - Khung giờ tối muộn và đêm có tỷ lệ tip cao hơn ban ngày 1.5% - 2.5%.

---

### 5. `05_heatmap_calendar_year_demand.png` - Bản Đồ Nhiệt Mùa Vụ 365 Ngày (Tháng x Ngày)
![05 Calendar Year Demand](./05_heatmap_calendar_year_demand.png)

- **Trục Y:** 12 tháng | **Trục X:** 31 ngày trong tháng.
- **Giải thích:**
  - Nhu cầu đạt đỉnh vào mùa lễ hội cuối năm (Tháng 10, 11, 12 với >115k chuyến/ngày).
  - Nhu cầu chạm đáy vào đợt nghỉ hè (Tháng 7, 8) và các ngày bão tuyết mùa đông (Tháng 1, 2).
