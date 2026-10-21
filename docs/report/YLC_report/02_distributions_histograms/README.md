# 02. Phân Phối Đơn Biến (Histograms Analytics)

> **Tập dữ liệu:** `delta.silver.yellow_trips` (Tầng Silver)  
> **Mục tiêu:** Khám phá hình dạng phân phối, các giá trị tập trung và nhận diện hiện tượng đa đỉnh (*Multimodal Distributions*).

---

## Danh Sách 6 Biểu Đồ Histogram

---

### 1. `01_hist_trip_duration.png` - Phân Phối Thời Lượng Chuyến Đi
![01 Trip Duration](./01_hist_trip_duration.png)

- **Trung vị (Median):** **`13.5 phút`** | **Trung bình (Mean):** **`17.2 phút`** | **IQR:** **`8.2 -> 21.6 phút`**.
- **Giải thích:** Phân phối lệch phải (*Right-skewed*). Đỉnh nhọn (Mode) rơi vào khoảng **8 - 12 phút**. Đuôi phân phối kéo dài đến 60 phút đại diện cho các chuyến đi liên quận vượt sông hoặc kẹt xe nghiêm trọng lúc tan tầm.

---

### 2. `02_hist_trip_distance.png` - Phân Phối Cự Ly Di Chuyển
![02 Trip Distance](./02_hist_trip_distance.png)

- **Trung vị (Median):** **`1.72 dặm (~2.77 km)`** | **P90:** **`14.72 dặm`** | **P99:** **`20.02 dặm`**.
- **Giải thích:** Phân phối thể hiện 2 nhóm rõ rệt:
  1. **Nhóm ngắn nội đô (0.5 - 3.5 dặm):** Chiếm hơn 70% tổng lưu lượng.
  2. **Gờ phụ sân bay (12.0 - 18.0 dặm):** Phản ánh khoảng cách địa lý thực tế từ Manhattan đi sân bay LaGuardia (~10 dặm) và sân bay JFK (~16 dặm).

---

### 3. `03_hist_tip_percentage.png` - Phân Phối Tỷ Lệ Tiền Tip Trên Thẻ Tín Dụng
![03 Tip Percentage](./03_hist_tip_percentage.png)

- **Tỷ trọng thanh toán thẻ:** **`85.9%`** | **Tip trung bình:** **`25.48%`**.
- **Giải thích:** Xuất hiện **4 đỉnh nhọn sắc nét (*Quadrimodal Spikes*)** tại đúng các mốc **`15%`**, **`20%` (Đỉnh cao nhất)**, **`25%`**, và **`30%`**. Hiện tượng này chứng minh khách hàng bị chi phối bởi các nút bấm gợi ý mặc định trên máy POS quẹt thẻ taxi.

---

### 4. `04_hist_fare_amount.png` - Phân Phối Giá Cước Cơ Bản
![04 Fare Amount](./04_hist_fare_amount.png)

- **Trung vị (Median):** **`$13.48`** | **Trung bình (Mean):** **`$19.75`**.
- **Giải thích:** Đồ thị xuất hiện một cột đỉnh nhọn đứng độc lập tại mức **`$70.00`** - đây là bằng chứng định lượng về quy định cước trọn gói cố định (*Flat Rate*) của NYC cho tuyến Manhattan -> Sân bay JFK.

---

### 5. `05_hist_average_speed.png` - Phân Phối Vận Tốc Di Chuyển Trung Bình
![05 Average Speed](./05_hist_average_speed.png)

- **Vận tốc trung vị:** **`11.8 mph (~19.0 km/h)`** | **Trung bình:** **`13.4 mph`**.
- **Giải thích:** Vận tốc đô thị trung bình thấp do mật độ đèn tín hiệu và người đi bộ lớn tại Manhattan. Vận tốc > 30 mph chỉ xuất hiện vào ban đêm hoặc trên các tuyến cao tốc ven sông (FDR Drive).

---

### 6. `06_bimodal_rush_hours.png` - Phân Phối 2 Đỉnh Khung Giờ Cao Điểm Trong Ngày
![06 Bimodal Rush Hours](./06_bimodal_rush_hours.png)

- **Đỉnh 1 (Cao điểm sáng 08:00 - 09:00):** Đạt **~1.51 triệu chuyến/giờ** (giờ đi làm).
- **Đỉnh 2 (Cao điểm chiều/tối 17:00 - 19:00):** Đạt đỉnh cao nhất **~2.56 triệu chuyến/giờ** (tan sở + ăn tối, giải trí).
- **Trũng đêm (02:00 - 05:00):** Nhu cầu chạm đáy (166k chuyến), nhưng cước bình quân lại cao nhất ($34 - $39) do chủ yếu là chuyến đi xa hoặc ra sân bay đón chuyến sớm.
