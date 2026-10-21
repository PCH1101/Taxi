# 03. Tương Quan Đa Biến (Scatter Plots Analytics)

> **Tập dữ liệu:** `delta.silver.yellow_trips` (Tầng Silver)  
> **Mục tiêu:** Khám phá mối quan hệ tương quan giữa 2 biến định lượng liên tục, nhận diện đường xu hướng, phân cụm và phân loại rõ ràng màu sắc của các điểm dữ liệu.

---

## Danh Sách 4 Biểu Đồ Scatter Plot (Đã Chú Thích Rõ Màu Sắc)

---

### 1. `01_scatter_distance_vs_fare.png` - Cự Ly Di Chuyển vs. Giá Cước Cơ Bản
![01 Distance vs Fare](./01_scatter_distance_vs_fare.png)

- **Chú thích màu sắc điểm dữ liệu:**
  - Điểm màu xanh dương (`#1f77b4`): Chuyến đi nội đô thông thường (*Standard Metered Trips*) tính theo đồng hồ cước.
  - Điểm màu đỏ (`#dc2626`): Chuyến đi sân bay (*Airport Trips: JFK Flat Rate $70 / Phụ phí sân bay*).
- **Hiện tượng & Đường xu hướng:**
  - **Đường dốc tuyến tính màu xanh lá (`#16a34a`):** Tương quan thuận cực mạnh ($r > 0.92$) bám theo công thức chuẩn: $\text{Fare} \approx \$3.00 + \$3.50 \times \text{Distance}$.
  - **Đường nằm ngang màu đỏ tại `$70.00` (*JFK Flat Rate*):** Toàn bộ các chuyến đi từ Manhattan đến sân bay JFK đều phân bố thẳng hàng tại $70.00 bất kể cự ly dao động từ 10 đến 25 dặm.
  - **Các điểm nằm lệch lên phía trên đường xanh:** Chuyến cự ly ngắn nhưng xe bị kẹt dừng chờ lâu ($0.70/phút khi xe chạy dưới 12 mph).

---

### 2. `02_scatter_distance_vs_duration.png` - Cự Ly vs. Thời Gian Di Chuyển (Colorbar Vận Tốc)
![02 Distance vs Duration](./02_scatter_distance_vs_duration.png)

- **Chú thích dải màu liên tục (*Viridis Colormap & Colorbar*):**
  - Dải màu tím sẫm (< 10 mph): Ùn tắc nội đô (*Urban Gridlock*), xe di chuyển chậm chạp trong lõi trung tâm Manhattan (quãng đường ngắn 1 - 3 dặm nhưng mất 30 - 55 phút).
  - Dải màu xanh ngọc / xanh lục (~20 - 25 mph): Lưu thông trên các trục đường chính (*Arterial Flow*) với tốc độ tiêu chuẩn.
  - Dải màu vàng sáng (> 35 - 50 mph): Di chuyển trên cao tốc (*Highway / Expressways: FDR Drive, BQE, Van Wyck*) với cự ly dài 15 - 25 dặm nhưng chỉ tốn 20 - 30 phút.
- **Đường tham chiếu vận tốc (*Speed Rays*):**
  - Đường nét đứt màu tím: **10 mph** (ngưỡng tốc độ kẹt xe nội đô).
  - Đường gạch chấm màu xanh: **25 mph** (ngưỡng tốc độ trung bình).
  - Đường chấm vàng: **45 mph** (ngưỡng tốc độ cao tốc).

---

### 3. `03_scatter_fare_vs_tip.png` - Giá Cước vs. Tiền Tip (Phân Tầng Tip & Chùm Tia POS)
![03 Fare vs Tip](./03_scatter_fare_vs_tip.png)

- **Chú thích màu sắc điểm dữ liệu theo hành vi Tip:**
  - Điểm màu xanh dương đậm (`#1d4ed8`): Nhóm **Tip chuẩn 20% (18% - 22%)** - nút bấm mặc định phổ biến nhất trên máy quẹt thẻ POS taxi.
  - Điểm màu xanh lá (`#16a34a`): Nhóm **Tip 25% (22.5% - 27.5%)** - nút bấm gợi ý thứ hai trên màn hình.
  - Điểm màu tím (`#9333ea`): Nhóm **Tip hào phóng >= 30%** - lựa chọn cao cấp hoặc khách hàng thưởng thêm.
  - Điểm màu cam (`#ea580c`): Nhóm **Tip số tiền chẵn ($5, $10, $20 Flat)** do khách hàng tự nhập số tròn.
  - Điểm màu xám (`#94a3b8`): Nhóm **Tip tùy biến / Dưới mức chuẩn (< 18%)**.
- **Phân tích chùm tia tương quan (*Ray Clusters*):**
  - Dữ liệu tập trung thành các dải tia rõ nét theo các đường cước 20%, 25%, 30%.
  - Cột dọc tại mốc cước `$70.00` (JFK Flat Rate) làm phát sinh cột tiền tip thẳng đứng từ **$14.00 đến $21.00**.

---

### 4. `04_scatter_hour_vs_speed.png` - Khung Giờ Trong Ngày vs. Vận Tốc Di Chuyển
![04 Hour vs Speed](./04_scatter_hour_vs_speed.png)

- **Chú thích màu sắc điểm theo 5 Khung Giờ Giao Thông (*Traffic Regimes*):**
  - Màu tím chàm (`#6366f1`): *Đêm & Rạng Sáng (00:00 - 05:59)* - Đường phố thông thoáng, tốc độ xe đạt mức cực đại.
  - Màu vàng hổ phách (`#f59e0b`): *Cao Điểm Sáng (06:00 - 09:59)* - Dòng người đi làm đổ vào thành phố, tốc độ giảm dốc.
  - Màu xanh da trời (`#0284c7`): *Giữa Ngày (10:00 - 15:59)* - Mật độ di chuyển nội đô ổn định (~10 mph).
  - Màu đỏ san hô (`#ef4444`): *Cao Điểm Chiều Tối (16:00 - 19:59)* - Đáy ùn tắc sâu nhất trong ngày.
  - Màu xanh ngọc (`#10b981`): *Đêm Muộn (20:00 - 23:59)* - Giao thông hạ nhiệt, tốc độ phục hồi dần.
- **Vùng cao điểm & Đường trung bình:**
  - Vùng đổ bóng vàng: **Cao điểm sáng (07:00 - 09:30 AM)**.
  - Vùng đổ bóng đỏ: **Cao điểm tối (16:30 - 19:30 PM)**.
  - Đường màu đỏ đậm: **Vận tốc trung bình 24 giờ**, đạt đỉnh tại **05:00 AM (21.3 mph)** và chạm đáy tại **17:00 PM (9.8 mph)**.
