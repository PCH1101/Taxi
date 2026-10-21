# Khảo Sát Dữ Liệu - NYC Taxi Real-Time Pipeline

> **Phạm vi khảo sát:** `/run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/data/`  
> **Thời điểm đánh giá:** 16/09/2026  
> **Giai đoạn dữ liệu:** Tháng 04/2026  

---

## 1. Cấu Trúc Thư Mục Dữ Liệu

```text
data/
|-- yellow_tripdata_2026-04.parquet     (61.82 MB - Taxi vàng truyền thống)
|-- green_tripdata_2026-04.parquet      ( 1.03 MB - Taxi xanh ngoại thành)
|-- fhvhv_tripdata_2026-04.parquet     (486.25 MB - Xe công nghệ Uber & Lyft)
|-- taxi_zones.json                     (Metadata tọa độ 265 vùng)
+-- taxi_zones/                         (Shapefile ESRI địa lý 263 vùng)
    |-- taxi_zones.shp                  (Đa giác hình học Polygon)
    |-- taxi_zones.dbf                  (Bảng thuộc tính hành chính)
    |-- taxi_zones.shx                  (Chỉ mục không gian Shape Index)
    |-- taxi_zones.prj                  (Định nghĩa hệ quy chiếu)
    +-- taxi_zones.cpg                  (Bảng mã ký tự)
```

- **Tổng dung lượng lưu trữ:** ~549 MB  
- **Nguồn dữ liệu chính thức:** NYC Taxi and Limousine Commission (TLC) Trip Record Data  

---

## 2. Phân Tích Dữ Liệu Taxi Vàng (Yellow Taxi) - `yellow_tripdata_2026-04.parquet`

### 2.1 Tổng quan tập dữ liệu

| Thuộc tính kỹ thuật | Giá trị ghi nhận |
|---|---|
| **Tổng số dòng** | 3,831,240 bản ghi |
| **Số lượng cột** | 20 trường |
| **Số Row Groups** | 4 |
| **Dung lượng tệp tin** | 61.82 MB |
| **Phạm vi thời gian** | 01/04/2026 - 30/04/2026 |
| **Định dạng lưu trữ** | Apache Parquet (Snappy Compressed) |

### 2.2 Đặc tả Schema

| Tên cột | Kiểu dữ liệu | Số lượng Null | Tỷ lệ Null | Ý nghĩa kỹ thuật & Nghiệp vụ |
|---|---|---|---|---|
| `VendorID` | int32 | 0 | 0.0% | Mã định danh nhà cung cấp thiết bị (1=CMT, 2=VeriFone, 6, 7) |
| `tpep_pickup_datetime` | timestamp[us] | 0 | 0.0% | Mốc thời gian đón khách |
| `tpep_dropoff_datetime` | timestamp[us] | 0 | 0.0% | Mốc thời gian trả khách |
| `passenger_count` | int64 | 799,786 | 20.9% | Số lượng hành khách trên chuyến |
| `trip_distance` | double | 0 | 0.0% | Khoảng cách di chuyển tính bằng dặm (miles) |
| `RatecodeID` | int64 | 799,786 | 20.9% | Mã bảng giá cước (1=Tiêu chuẩn, 2=JFK, 3=Newark, 4=Nassau...) |
| `store_and_fwd_flag` | large_string | 799,786 | 20.9% | Cờ lưu trữ tạm trước khi truyền về máy chủ (Y/N) |
| `PULocationID` | int32 | 0 | 0.0% | Mã phân vùng đón khách TLC (1 - 263) |
| `DOLocationID` | int32 | 0 | 0.0% | Mã phân vùng trả khách TLC (1 - 263) |
| `payment_type` | int64 | 0 | 0.0% | Phương thức thanh toán (1=Thẻ, 2=Tiền mặt, 3=Không cước, 4=Tranh chấp) |
| `fare_amount` | double | 0 | 0.0% | Cước tính theo đồng hồ taximeter (USD) |
| `extra` | double | 0 | 0.0% | Phụ phí giờ cao điểm hoặc đêm muộn |
| `mta_tax` | double | 0 | 0.0% | Thuế giao thông công cộng MTA ($0.50) |
| `tip_amount` | double | 0 | 0.0% | Tiền boa tip khi quẹt thẻ |
| `tolls_amount` | double | 0 | 0.0% | Phí cầu phà và hầm đường bộ |
| `improvement_surcharge` | double | 0 | 0.0% | Phụ phí nâng cấp hạ tầng ($0.30 - $1.00) |
| `total_amount` | double | 0 | 0.0% | Tổng chi phí khách hàng chi trả (USD) |
| `congestion_surcharge` | double | 799,786 | 20.9% | Phụ phí ùn tắc khu vực trung tâm Manhattan ($2.50) |
| `Airport_fee` | double | 799,786 | 20.9% | Phí dịch vụ sân bay LaGuardia / JFK ($1.25 - $1.75) |
| `cbd_congestion_fee` | double | 0 | 0.0% | Phí chống ùn tắc lõi trung tâm thương mại NYC CBD |

### 2.3 Thống kê phân phối giá trị

| Chỉ số | Giá trị nhỏ nhất (Min) | Giá trị lớn nhất (Max) | Giá trị trung bình (Mean) |
|---|---|---|---|
| `total_amount` | -$1,278.40 | $1,452.66 | $30.00 |
| `trip_distance` | 0.00 dặm | 281,576.08 dặm | 5.18 dặm |

### 2.4 Giá trị phân loại (Categorical Values)
- `VendorID`: 1, 2, 6, 7
- `passenger_count`: 0 đến 9 khách
- `payment_type`: 0, 1, 2, 3, 4
- `RatecodeID`: 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 99.0

> **Đánh giá chất lượng dữ liệu:**
> - `trip_distance` ghi nhận giá trị cực đại 281,576 dặm - đây là lỗi nhập liệu hoặc lỗi thiết bị phần cứng, cần bộ lọc ngoại lai (Outlier Filter).
> - `total_amount` xuất hiện giá trị âm, phản ánh các giao dịch hoàn cước hoặc điều chỉnh hoàn tiền (refunds / chargebacks).
> - Khoảng 20.9% bản ghi bị thiếu thông tin ở các trường: `passenger_count`, `RatecodeID`, `store_and_fwd_flag`, `congestion_surcharge`, `Airport_fee`.

---

## 3. Phân Tích Dữ Liệu Taxi Xanh (Green Taxi) - `green_tripdata_2026-04.parquet`

### 3.1 Tổng quan tập dữ liệu

| Thuộc tính kỹ thuật | Giá trị ghi nhận |
|---|---|
| **Tổng số dòng** | 44,238 bản ghi |
| **Số lượng cột** | 21 trường |
| **Số Row Groups** | 1 |
| **Dung lượng tệp tin** | 1.03 MB |
| **Phạm vi thời gian** | 01/04/2026 - 30/04/2026 |
| **Định dạng lưu trữ** | Apache Parquet (Snappy Compressed) |

> Dòng taxi xanh (Boro Taxi) chủ yếu hoạt động tại các quận ngoài (Outer Boroughs) và phía bắc Manhattan. Dung lượng và lưu lượng thấp hơn Yellow Taxi khoảng 87 lần.

### 3.2 Đặc tả Schema

| Tên cột | Kiểu dữ liệu | Số lượng Null | Tỷ lệ Null | Ý nghĩa kỹ thuật & Nghiệp vụ |
|---|---|---|---|---|
| `VendorID` | int32 | 0 | 0.0% | 1, 2, 6 |
| `lpep_pickup_datetime` | timestamp[us] | 0 | 0.0% | Mốc thời gian đón khách |
| `lpep_dropoff_datetime` | timestamp[us] | 0 | 0.0% | Mốc thời gian trả khách |
| `store_and_fwd_flag` | large_string | 6,290 | 14.2% | Cờ lưu trữ tạm trước khi truyền |
| `RatecodeID` | int64 | 6,290 | 14.2% | Bảng giá cước |
| `PULocationID` | int32 | 0 | 0.0% | Vùng đón khách |
| `DOLocationID` | int32 | 0 | 0.0% | Vùng trả khách |
| `passenger_count` | int64 | 6,290 | 14.2% | Số lượng hành khách |
| `trip_distance` | double | 0 | 0.0% | Quãng đường di chuyển (dặm) |
| `fare_amount` | double | 0 | 0.0% | Cước cơ bản theo đồng hồ |
| `extra` | double | 0 | 0.0% | Phụ phí giờ cao điểm |
| `mta_tax` | double | 0 | 0.0% | Thuế giao thông công cộng MTA ($0.50) |
| `tip_amount` | double | 0 | 0.0% | Tiền tip |
| `tolls_amount` | double | 0 | 0.0% | Phí cầu đường |
| `ehail_fee` | double | 44,238 | **100.0%** | Trường đã lỗi thời (deprecated), hoàn toàn rỗng |
| `improvement_surcharge` | double | 0 | 0.0% | Phụ phí cơ sở hạ tầng |
| `total_amount` | double | 0 | 0.0% | Tổng chi phí chuyến đi |
| `payment_type` | int64 | 6,290 | 14.2% | Phương thức thanh toán |
| `trip_type` | int64 | 6,290 | 14.2% | 1=Đón vẫy trên đường (Street-hail), 2=Điều xe từ tổng đài (Dispatch) |
| `congestion_surcharge` | double | 6,290 | 14.2% | Phụ phí tắc đường |
| `cbd_congestion_fee` | double | 0 | 0.0% | Phí tắc đường khu vực thương mại trung tâm |

### 3.3 Thống kê phân phối giá trị

| Chỉ số | Giá trị nhỏ nhất (Min) | Giá trị lớn nhất (Max) | Giá trị trung bình (Mean) |
|---|---|---|---|
| `total_amount` | -$171.00 | $675.10 | $25.41 |
| `trip_distance` | 0.00 dặm | 95,906.47 dặm | 11.38 dặm |

> **Đánh giá chất lượng dữ liệu:**
> - Trường `ehail_fee` rỗng 100%, cần được loại bỏ trong quá trình chuẩn hóa schema.
> - `trip_distance` ghi nhận giá trị tối đa 95,906 dặm, cần áp dụng bộ lọc làm sạch tương tự Yellow Taxi.

---

## 4. Phân Tích Dữ Liệu Xe Công Nghệ (FHVHV) - `fhvhv_tripdata_2026-04.parquet`

### 4.1 Tổng quan tập dữ liệu

| Thuộc tính kỹ thuật | Giá trị ghi nhận |
|---|---|
| **Tổng số dòng** | 20,995,953 bản ghi |
| **Số lượng cột** | 25 trường |
| **Số Row Groups** | 21 |
| **Dung lượng tệp tin** | 486.25 MB |
| **Phạm vi thời gian** | 01/04/2026 - 30/04/2026 |
| **Nhà cung cấp** | Uber (HV0003) và Lyft (HV0005) |
| **Định dạng lưu trữ** | Apache Parquet (Snappy Compressed) |

> Đây là tập dữ liệu có quy mô lớn nhất trong hệ thống - gấp **5.5 lần** lưu lượng của Yellow Taxi, phản ánh toàn bộ các chuyến xe dịch vụ gọi qua ứng dụng di động tại 5 quận New York.

### 4.2 Đặc tả Schema

| Tên cột | Kiểu dữ liệu | Số lượng Null | Tỷ lệ Null | Ý nghĩa kỹ thuật & Nghiệp vụ |
|---|---|---|---|---|
| `hvfhs_license_num` | large_string | 0 | 0.0% | Mã giấy phép dịch vụ (HV0003=Uber, HV0005=Lyft) |
| `dispatching_base_num` | large_string | 0 | 0.0% | Mã pháp nhân cơ sở điều phối chuyến xe |
| `originating_base_num` | large_string | 5,594,175 | 26.6% | Cơ sở khởi tạo cuốc xe |
| `request_datetime` | timestamp[us] | 0 | 0.0% | Thời điểm hành khách đặt xe trên ứng dụng |
| `on_scene_datetime` | timestamp[us] | 0 | 0.0% | Thời điểm tài xế có mặt tại điểm đón |
| `pickup_datetime` | timestamp[us] | 0 | 0.0% | Thời điểm đón khách lên xe |
| `dropoff_datetime` | timestamp[us] | 0 | 0.0% | Thời điểm hoàn tất trả khách |
| `PULocationID` | int32 | 0 | 0.0% | Phân vùng đón khách |
| `DOLocationID` | int32 | 0 | 0.0% | Phân vùng trả khách |
| `trip_miles` | double | 0 | 0.0% | Quãng đường di chuyển (dặm) |
| `trip_time` | int64 | 0 | 0.0% | Thời gian di chuyển (giây) |
| `base_passenger_fare` | double | 0 | 0.0% | Cước phí cơ bản hành khách chi trả (USD) |
| `tolls` | double | 0 | 0.0% | Phí cầu phà |
| `bcf` | double | 0 | 0.0% | Đóng góp quỹ hỗ trợ Black Car Fund |
| `sales_tax` | double | 0 | 0.0% | Thuế bán hàng |
| `congestion_surcharge` | double | 0 | 0.0% | Phụ phí chống ùn tắc |
| `airport_fee` | double | 0 | 0.0% | Phí vào sân bay |
| `tips` | double | 0 | 0.0% | Tiền tip trên ứng dụng |
| `driver_pay` | double | 0 | 0.0% | Thu nhập thực nhận của tài xế (USD) |
| `shared_request_flag` | large_string | 0 | 0.0% | Yêu cầu đi chung xe (Y/N) |
| `shared_match_flag` | large_string | 0 | 0.0% | Ghép chuyến đi chung thành công (Y/N) |
| `access_a_ride_flag` | large_string | 0 | 0.0% | Chuyến xe hỗ trợ người khuyết tật Access-A-Ride |
| `wav_request_flag` | large_string | 0 | 0.0% | Yêu cầu xe hỗ trợ xe lăn (Wheelchair Accessible Vehicle) |
| `wav_match_flag` | large_string | 0 | 0.0% | Ghép xe hỗ trợ xe lăn thành công |
| `cbd_congestion_fee` | double | 0 | 0.0% | Phí ùn tắc khu vực thương mại trung tâm New York |

### 4.3 Thống kê phân phối giá trị

| Chỉ số | Giá trị nhỏ nhất (Min) | Giá trị lớn nhất (Max) | Giá trị trung bình (Mean) |
|---|---|---|---|
| `base_passenger_fare` | -$222.34 | $1,445.92 | $27.24 |
| `trip_miles` | 0.00 dặm | 1,468.15 dặm | 4.87 dặm |

> **Đặc điểm kiến trúc nổi bật của tập FHVHV:**
> - Cung cấp chuỗi 4 mốc thời gian hoàn chỉnh: `request_datetime` -> `on_scene_datetime` -> `pickup_datetime` -> `dropoff_datetime`.
> - Chuỗi dữ liệu này cho phép tính toán chính xác thời gian chờ xe (*wait time*), thời gian tài xế tiếp cận điểm đón (*dispatch lag*) và độ chính xác của thời gian dự kiến đến (*ETA accuracy*).

---

## 5. Dữ Liệu Phân Vùng Địa Lý (Taxi Zones) - `taxi_zones/`

### 5.1 Tổng quan hình học và hệ tọa độ

| Thuộc tính kỹ thuật | Giá trị ghi nhận |
|---|---|
| **Định dạng tệp tin** | ESRI Shapefile |
| **Loại hình học (Geometry)** | Polygon (Shape Type 5) |
| **Số lượng phân vùng** | 263 phân vùng địa lý chính thức |
| **Hệ tọa độ quy chiếu** | NAD 1983 StatePlane New York Long Island (FIPS 3104, Đơn vị: Feet) |
| **Tọa độ bao viền (Bounding Box)**| (913175.11, 120121.88) đến (1,067,382.51, 272,844.29) |

### 5.2 Thành phần các tệp tin trong bộ Shapefile

| Tên tệp tin | Dung lượng | Chức năng kỹ thuật |
|---|---|---|
| `taxi_zones.shp` | 1.51 MB | Chứa toàn bộ thông tin hình học đa giác (Polygon geometries) |
| `taxi_zones.dbf` | 58.5 KB | Bảng dữ liệu thuộc tính hành chính của các phân vùng |
| `taxi_zones.shx` | 2.15 KB | Tệp chỉ mục định vị không gian |
| `taxi_zones.prj` | 0.55 KB | Định nghĩa tham số toán học của phép chiếu bản đồ |
| `taxi_zones.cpg` | 5 Bytes | Mã hóa bộ ký tự |

### 5.3 Bảng thuộc tính hành chính (DBF Schema)

| Tên trường | Kiểu dữ liệu | Độ dài | Ý nghĩa kỹ thuật |
|---|---|---|---|
| `OBJECTID` | Numeric | 9 | Mã định danh nội bộ |
| `Shape_Leng` | Numeric | 24 | Chu vi của đa giác phân vùng |
| `Shape_Area` | Numeric | 24 | Diện tích của đa giác phân vùng |
| `zone` | Character | 80 | Tên phân vùng cụ thể (ví dụ: "JFK Airport", "Times Sq/Theatre District") |
| `LocationID` | Numeric | 9 | **Khóa liên kết chính (Join Key)** -> Ánh xạ trực tiếp với `PULocationID` / `DOLocationID` |
| `borough` | Character | 80 | Tên quận (Manhattan, Brooklyn, Queens, Bronx, Staten Island, EWR) |

> `LocationID` là khóa ngoại duy nhất để kết nối bảng sự kiện Parquet với tọa độ không gian. 263 phân vùng bao phủ toàn diện 5 quận thành phố New York và sân bay quốc tế Newark (EWR).

---

## 6. Tổng Hợp Quy Mô Các Tập Dữ Liệu Tháng 04/2026

| Phân lớp dữ liệu | Số lượng chuyến đi | Dung lượng tệp tin | Đơn vị vận hành | Địa bàn hoạt động chủ đạo |
|---|---|---|---|---|
| **Yellow Taxi** | 3,831,240 | 61.82 MB | CMT, VeriFone | Toàn thành phố (tập trung lõi Manhattan và sân bay) |
| **Green Taxi** | 44,238 | 1.03 MB | CMT, VeriFone | Các quận ngoài Manhattan, vùng phụ cận |
| **FHVHV (Uber/Lyft)** | 20,995,953 | 486.25 MB | Uber, Lyft | Phủ kín toàn bộ 5 quận New York |
| **TỔNG CỘNG** | **24,871,431** | **549.10 MB** | - | Toàn bộ mạng lưới giao thông New York |

---

## 7. Các Vấn Đề Chất Lượng Cần Xử Lý (Data Quality Gates)

### 7.1 Lọc bỏ giá trị dị biệt (Outlier Filtering)
- **Cự ly di chuyển vô lý:** `trip_distance` trong Yellow lên tới 281,576 dặm và Green lên tới 95,906 dặm. Cần thiết lập ngưỡng trần chất lượng: loại bỏ mọi bản ghi có `trip_distance > 200` dặm hoặc cự ly bằng 0 nhưng cước phí lớn.
- **Giá cước âm:** Toàn bộ bản ghi có `total_amount < 0` hoặc `base_passenger_fare < 0` phải được cách ly hoặc xử lý riêng biệt để không làm sai lệch tính toán doanh thu thời gian thực.

### 7.2 Xử lý giá trị khuyết thiếu (Null Handling)
- **Tập Yellow Taxi:** ~20.9% bản ghi khuyết thiếu trường `passenger_count` và `RatecodeID`. Giải pháp chuẩn hóa: gán giá trị mặc định `passenger_count = 1` và `RatecodeID = 1` (Standard Rate).
- **Tập Green Taxi:** Trường `ehail_fee` rỗng 100%, tiến hành drop bỏ trường này khỏi mô hình sự kiện.
- **Tập FHVHV:** Trường `originating_base_num` thiếu 26.6%, cho phép chấp nhận giá trị rỗng vì không ảnh hưởng đến tọa độ và cước phí.

### 7.3 Bất thường về mốc thời gian (Timestamp Anomalies)
- Tồn tại một số bản ghi có mốc thời gian thuộc năm 2001 hoặc vượt ngoài tháng 04/2026.
- Cần áp dụng bộ lọc biên thời gian (Boundary Filter): chỉ tiếp nhận các chuyến xe có mốc đón nằm trong phạm vi tháng khảo sát (hoặc dung sai trễ tối đa 24 giờ).

---

## 8. Mô Hình Quan Hệ Dữ Liệu (Entity Relationship & Shared Keys)

```text
========================================================================================
                                     taxi_zones
                           LocationID (263 Taxi Zones)
                                       ^
                                       |
                      +----------------+----------------+
                      | JOIN (PULocationID / DOLocationID)
                      |
    +-----------------+-----------------+-----------------+
    |                                   |                 |
yellow_tripdata                 green_tripdata      fhvhv_tripdata
========================================================================================
```

### Các trường liên kết dùng chung giữa 3 tập dữ liệu:
- `PULocationID` -> Ánh xạ tới `taxi_zones.LocationID` (Phân vùng đón khách).
- `DOLocationID` -> Ánh xạ tới `taxi_zones.LocationID` (Phân vùng trả khách).
- Mốc thời gian di chuyển -> Sử dụng làm khóa phân vùng thời gian (Watermarking & Windowing).
- `cbd_congestion_fee` -> Có mặt đồng bộ trên cả 3 tập dữ liệu theo quy định phí tắc đường khu vực trung tâm New York.

---

## 9. Khuyến Nghị Thiết Kế Cho Pipeline Thời Gian Thực (Streaming Architecture Recommendations)

| Mức ưu tiên | Hạng mục kỹ thuật | Giải pháp triển khai cụ thể |
|---|---|---|
| **P0 (Bắt buộc)** | **Bộ lọc ngoại lai (Filter Outliers)** | Loại bỏ bản ghi có `trip_distance > 200` dặm hoặc mốc thời gian sai lệch quá 1 ngày trước khi đẩy vào Kafka. |
| **P0 (Bắt buộc)** | **Chiến lược Watermark thống nhất** | Ánh xạ trường thời gian gốc về trường chuẩn: Yellow (`tpep_pickup_datetime`), Green (`lpep_pickup_datetime`), FHVHV (`pickup_datetime`). |
| **P1 (Quan trọng)**| **Loại bỏ cột thừa** | Drop trường rỗng 100% (`ehail_fee`) để tối ưu hóa kích thước gói tin JSON phát qua Kafka. |
| **P1 (Quan trọng)**| **Bộ đệm tham chiếu (Broadcast Cache)** | Tải tệp `taxi_zones.json` (hoặc shapefile) vào bộ nhớ RAM của Flink và API Gateway để tra cứu O(1) không cần truy vấn I/O. |
| **P2 (Cần thiết)** | **Điền khuyết thiếu mặc định** | Tự động gán `passenger_count = 1` và `RatecodeID = 1` khi phát hiện giá trị Null. |
| **P2 (Cần thiết)** | **Chuẩn hóa Schema sự kiện** | Ép kiểu toàn bộ 3 nguồn dữ liệu về một Canonical Pydantic Schema duy nhất (`TripEvent`) trước khi truyền qua mạng. |
| **P3 (Tối ưu hóa)**| **Phân vùng Kafka (Partition Key)** | Lựa chọn `PULocationID` làm partition key trên Kafka broker để đảm bảo thứ tự sự kiện của từng phân vùng được bảo toàn trên cùng một partition. |
