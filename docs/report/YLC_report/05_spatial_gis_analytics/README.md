# 05. Phân Tích Địa Lý & Bản Đồ Nhiệt Không Gian (Spatial GIS Analytics)

> **Tập dữ liệu:** `delta.silver.yellow_trips` kết hợp `delta.silver.dim_taxi_zones` (262 Taxi Zones trên 5 quận New York)  
> **Mục tiêu:** Khảo sát luồng giao thông, mất cân bằng Cung - Cầu xe, mật độ doanh thu và hành lang sân bay.

---

## Danh Sách 5 Biểu Đồ & Bản Đồ Không Gian

---

### 0. Bản Đồ Web Tương Tác Toàn Thành Phố (*Interactive Leaflet Map*)
Mở trực tiếp trên trình duyệt web: [`interactive_spatial_heatmap.html`](./interactive_spatial_heatmap.html)

- **Lớp Heatmap mật độ đón khách:** Vệt nhiệt phát sáng phản ánh mật độ đón khách thực tế tại New York.
- **Lớp Net-Flow Markers:** 
  - Vòng tròn màu đỏ (Deficit): Vùng thiếu hụt xe (Số lượt đón > Số lượt trả) - cần điều chuyển xe đến.
  - Vòng tròn màu xanh lá (Surplus): Vùng dư thừa xe (Số lượt trả > Số lượt đón).
- **Popup tương tác:** Click chuột vào từng điểm để xem: *Tên Zone, Quận, Pickups, Dropoffs, Net Flow chênh lệch, và Cước trung bình*.
- **Bộ chuyển đổi nền (Layer Control):** Tích hợp chuyển đổi giữa CartoDB Light, CartoDB Dark (Night mode) và Esri Streets.

---

### 1. `01_spatial_borough_od_heatmap.png` - Ma Trận Luồng Di Chuyển Giữa Các Quận
![01 Borough OD Flow](./01_spatial_borough_od_heatmap.png)

- **83.5% chuyến đi (29.74M chuyến)** diễn ra hoàn toàn nội quận Manhattan.
- Luồng liên quận lớn nhất là giữa Manhattan và 2 sân bay JFK/LGA thuộc Queens (hơn **3.7M chuyến**).

---

### 2. `02_spatial_zone_netflow_heatmap.png` - Bản Đồ Mất Cân Bằng Cung - Cầu Xe (Net Flow)
![02 Zone Net Flow](./02_spatial_zone_netflow_heatmap.png)

- **Sân bay JFK thâm hụt nặng nhất:** $\text{Net Flow} = \mathbf{-1,120,500}$ xe (Lượng khách đón xe rời sân bay vượt xa lượng xe đến).
- **Upper East Side North dư thừa xe:** $\text{Net Flow} = \mathbf{+280,400}$ xe (Khách đi taxi về nhà ngủ nhưng sáng hôm sau đi làm bằng tàu điện ngầm Subway).

---

### 3. `03_spatial_zone_revenue_heatmap.png` - Bản Đồ Nhiệt Mỏ Vàng Kinh Tế Đa Chỉ Số
![03 Zone Revenue Multi Metric](./03_spatial_zone_revenue_heatmap.png)

- Sân bay JFK dẫn đầu toàn diện về doanh thu (**$154.21M**), cước bình quân (**$81.94/chuyến**), và cự ly (**15.53 dặm**).
- Các Zone nội đô như Midtown Center và Times Square mang lại doanh thu lớn nhờ lưu lượng chuyến khổng lồ.

---

### 4. `04_spatial_airport_dispersal_heatmap.png` - Hành Lang Giải Tỏa Khách Sân Bay
![04 Airport Dispersal](./04_spatial_airport_dispersal_heatmap.png)

- Hơn **65%** lượng khách hạ cánh tại JFK và LGA đổ thẳng về chuỗi khách sạn và văn phòng tại **Midtown Center, Times Square, Upper East Side South, và Midtown East**.
