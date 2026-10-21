# NYC Taxi Lakehouse Pipeline

Hệ thống Data Lakehouse cục bộ triển khai theo Kiến trúc Medallion (Bronze -> Silver -> Gold), hỗ trợ xử lý đa tập dữ liệu (Yellow Taxi, Green Taxi, FHV, FHVHV) kết hợp pipeline Machine Learning dự báo nhu cầu và doanh thu theo thời tiết.

---

## 1. Tổng quan Hệ thống và Kiến trúc (System Architecture)

Hệ thống được thiết kế dựa trên mô hình Data Lakehouse hiện đại, phân tách hoàn toàn giữa tầng lưu trữ đối tượng (Object Storage) và tầng tính toán (Compute Engine), đồng thời áp dụng định dạng bảng Delta Lake để đảm bảo tính toàn vẹn dữ liệu (giao dịch ACID, Time Travel, Schema Enforcement và tối ưu ghi đồng thời).

### 1.1 Sơ đồ Kiến trúc Tổng thể

```text
========================================================================================
                                 EXTERNAL DATA SOURCES
  + NYC TLC Trip Records (Yellow, Green, FHV, FHVHV qua CloudFront CDN)
  + Open-Meteo Historical & Forecast Weather API (Tọa độ New York City)
========================================================================================
                                           |
                    +----------------------+----------------------+
                    |                                             |
            [Airflow Pipeline]                            [Airflow Pipeline]
           taxi_monthly_pipeline                     taxi_weather_forecast_pipeline
                    |                                             |
                    v                                             v
========================================================================================
                         STORAGE LAYER: MinIO (S3-Compatible)
========================================================================================

  [1] s3a://bronze/
      +-- yellow_trips/      Dữ liệu thô thu thập từ NYC TLC, bổ sung các trường
      +-- green_trips/       metadata: _ingest_timestamp, _source_file, _source_month.
      +-- fhv_trips/
      +-- fhvhv_trips/
      +-- quarantine/        Bản ghi không đạt tiêu chuẩn kiểm định chất lượng (Quality Gate),
                             kèm mã lỗi và nguyên nhân chi tiết (_quarantine_reason).

  [2] s3a://silver/
      +-- yellow_trips/      Dữ liệu đã làm sạch, tính toán các chỉ số dẫn xuất
      +-- green_trips/       (duration_min, speed_mph, tip_rate),
      +-- fhv_trips/         phân vùng (partitioned) theo source_month.
      +-- dim_taxi_zones/    Bảng danh mục 265 phân vùng taxi NYC (LocationID, Borough, Zone).
      +-- dim_weather_hourly/Dữ liệu thời tiết theo giờ: nhiệt độ, lượng mưa, tuyết, tốc độ gió.

  [3] s3a://gold/
      +-- hourly_zone_metrics/          Tổng hợp nhu cầu, doanh thu, tiền tip theo giờ và phân vùng.
      +-- green_hourly_zone_metrics/    Tổng hợp dữ liệu cho dòng xe taxi xanh.
      +-- fhv_hourly_zone_metrics/      Tổng hợp dữ liệu cho xe hợp đồng dịch vụ (FHV).
      +-- weather_taxi_features_hourly/ Bảng feature kết hợp dữ liệu chuyến đi và thời tiết.
      +-- forecast_hourly_metrics/      Kết quả dự báo nhu cầu & doanh thu 24h tới từ mô hình LightGBM.

========================================================================================
                                 SERVING & AUDIT LAYER
========================================================================================

  + Trino Distributed SQL Engine:
    Truy vấn trực tiếp trên Delta Lake (delta.bronze, delta.silver, delta.gold)
    thông qua cơ chế MinIO File Metastore mà không cần dịch vụ Hive Metastore phức tạp.

  + PostgreSQL Audit Repository:
    Ghi nhận nhật ký kiểm toán toàn bộ tiến trình qua bảng pipeline_execution_history
    (số dòng đọc/ghi trên từng tầng, tỷ lệ bản ghi lỗi quarantine, thời gian thực thi).

  + Analytics & Visualization Suite:
    Tập hợp các script phân tích chuyên sâu (EDA, Heatmaps, bản đồ GIS) kết nối tới Trino.
========================================================================================
```

### 1.2 Chi tiết các Tầng Dữ liệu (Medallion Data Layers)

1. **Tầng Bronze (Raw Data Ingestion & Quarantine)**:
   - Tiếp nhận dữ liệu nguyên bản từ hệ thống CDN của NYC Taxi and Limousine Commission (TLC) dưới định dạng Parquet hoặc nạp từ tệp tin cục bộ.
   - Bảo toàn cấu trúc schema gốc, bổ sung các trường metadata phục vụ truy vết: `_ingest_timestamp`, `_source_file`, `_source_month`.
   - Cơ chế Quarantine: Các bản ghi vi phạm tính toàn vẹn (tọa độ ngoài phạm vi, thời gian đón sau thời gian trả khách, cự ly hoặc cước phí mang giá trị âm/vô lý) được phân loại và ghi vào bảng `s3a://bronze/quarantine` kèm theo lý do lỗi chi tiết.

2. **Tầng Silver (Cleaned, Enriched & Conformed Data)**:
   - Loại bỏ các bản ghi trùng lặp và lọc bỏ toàn bộ bản ghi không vượt qua bộ tiêu chuẩn Quality Gates.
   - Chuẩn hóa kiểu dữ liệu và định dạng tên cột nhất quán giữa các loại phương tiện (Yellow, Green, FHV, FHVHV).
   - Tính toán các chỉ số bổ sung: thời lượng hành trình (`duration_min`), vận tốc trung bình (`speed_mph`), tỷ lệ tiền tip (`tip_rate`).
   - Lưu trữ dưới dạng bảng Delta Lake và phân vùng theo tháng (`source_month`), giúp tối ưu hóa hiệu năng quét dữ liệu (data skipping/partition pruning).
   - Duy trì bảng danh mục phân vùng (`dim_taxi_zones`) và dữ liệu khí tượng chuẩn hóa (`dim_weather_hourly`).

3. **Tầng Gold (Aggregated Business Metrics & ML Features)**:
   - Dữ liệu được tổng hợp theo cấp độ giờ và khu vực đón/trả khách (hourly, zone-level).
   - Tính toán các chỉ số nghiệp vụ trọng yếu: tổng số chuyến đi, tổng doanh thu, doanh thu trung bình trên mỗi dặm, tỷ lệ tip bình quân, số lượng hành khách.
   - Bảng đặc trưng Machine Learning (`weather_taxi_features_hourly`): kết hợp đặc trưng thời gian (giờ trong ngày, ngày trong tuần), đặc trưng độ trễ (lag features) và các yếu tố thời tiết từ tầng Silver.
   - Bảng kết quả dự báo (`forecast_hourly_metrics`): lưu trữ kết quả suy luận từ mô hình LightGBM cho 24 giờ tiếp theo.

4. **Tầng Phục vụ & Kiểm toán (Serving & Governance Layer)**:
   - Truy vấn SQL phân tán hiệu năng cao thông qua Trino, đọc trực tiếp metadata của Delta Lake và các tệp Parquet lưu trên MinIO.
   - Giám sát độ tin cậy và số lượng bản ghi qua từng tầng xử lý thông qua bảng kiểm toán `pipeline_execution_history` trên PostgreSQL.

---

## 2. Ngăn xếp Công nghệ Chính (Core Tech Stack)

| Thành phần | Công nghệ / Phiên bản | Vai trò trong Kiến trúc |
|---|---|---|
| Distributed Storage | MinIO (RELEASE.2024+) | Hệ thống lưu trữ đối tượng tương thích chuẩn S3 API, quản lý 3 bucket chuyên biệt: `bronze`, `silver`, `gold`. |
| Table Format | Delta Lake 3.2.0 | Tầng định dạng bảng hỗ trợ giao dịch ACID, quản lý phiên bản (Time Travel), kiểm soát schema và cho phép ghi đồng thời an toàn. |
| Compute / Processing | Apache Spark 3.5.3 (PySpark) | Engine tính toán phân tán chịu trách nhiệm toàn bộ quy trình ETL, biến đổi dữ liệu, kiểm tra Quality Gates và tổng hợp OLAP. |
| Workflow Orchestration | Apache Airflow 2.10.3 | Nền tảng lập lịch và điều phối các pipeline dữ liệu, quản lý phụ thuộc giữa các tác vụ và tự động hóa chu trình suy luận ML. |
| Distributed SQL Engine | Trino 465 | Công cụ truy vấn SQL phân tán tốc độ cao, kết nối trực tiếp MinIO qua Delta Lake connector và File Metastore. |
| Metadata & Audit Store | PostgreSQL 16 | Cơ sở dữ liệu lưu trữ metadata của Apache Airflow và bảng nhật ký kiểm toán đường ống `pipeline_execution_history`. |
| Machine Learning Framework | LightGBM 4.x + Scikit-Learn | Huấn luyện mô hình hồi quy Gradient Boosting và thực hiện suy luận dự báo nhu cầu di chuyển, doanh thu theo thời tiết. |
| External Ingestion API | Open-Meteo REST API | Thu thập dữ liệu khí tượng lịch sử và dự báo thời tiết 48 giờ tới (nhiệt độ, lượng mưa, tuyết rơi, tốc độ gió) tại New York. |
| Container Platform | Docker & Docker Compose | Đóng gói và cô lập toàn bộ hạ tầng dịch vụ (Spark/Airflow, Trino, MinIO, Postgres) kèm cấu hình giới hạn tài nguyên và health check. |
| Data Analytics & Viz | Python (Matplotlib, Seaborn, Folium) | Xây dựng các báo cáo phân tích dữ liệu khám phá (EDA), ma trận tương quan, biểu đồ phân phối và bản đồ nhiệt GIS. |

---

## 3. Cấu trúc Mã nguồn (Repository Structure)

```text
taxi_lakehouse/
|-- dags/
|   |-- scripts/
|   |   |-- bronze.py                 # Logic nạp dữ liệu vào Bronze và cơ chế Quarantine
|   |   |-- silver.py                 # Làm sạch, chuẩn hóa, tính toán chỉ số và ghi Silver Delta
|   |   |-- gold.py                   # Tổng hợp các chỉ số OLAP theo giờ và khu vực
|   |   |-- weather_etl.py            # Thu thập và xử lý dữ liệu thời tiết từ Open-Meteo
|   |   |-- feature_engineering.py    # Xây dựng tập đặc trưng thời gian, thời tiết và độ trễ
|   |   |-- train_forecast_models.py  # Huấn luyện mô hình LightGBM dự báo nhu cầu & doanh thu
|   |   |-- predict_24h.py            # Suy luận dự báo 24h tiếp theo và ghi vào tầng Gold
|   |-- utils/
|   |   |-- spark.py                  # Khởi tạo SparkSession tối ưu với Delta Lake và MinIO S3A
|   |   |-- trino_helper.py           # Đồng bộ metadata, đăng ký bảng và làm tươi cache Trino
|   |   |-- audit_logger.py           # Ghi nhận nhật ký kiểm toán vào PostgreSQL
|   |-- models/                       # Tập tin mô hình LightGBM đã huấn luyện (.pkl)
|   |-- taxi_pipeline_dag.py          # Airflow DAG: Medallion ETL (Bronze -> Silver -> Gold -> Audit)
|   |-- taxi_forecast_dag.py          # Airflow DAG: Weather Ingestion & 24h ML Forecast
|-- scripts/
|   |-- minio-init.sh                 # Script khởi tạo bucket và phân quyền MinIO khi khởi động
|   |-- plot_heatmaps.py              # Trực quan hóa ma trận tương quan và mật độ chuyến đi
|   |-- plot_hist_scatter.py          # Biểu đồ phân phối đơn biến và đa biến
|   |-- plot_spatial_heatmaps.py      # Bản đồ nhiệt không gian GIS theo phân vùng NYC Taxi
|   |-- plot_forecast_vs_actual.py    # Đánh giá độ chính xác của dự báo LightGBM so với thực tế
|   |-- plot_fhv_*.py                 # Tập script phân tích chuyên biệt cho dữ liệu xe FHV
|-- trino/
|   |-- catalog/delta.properties      # Cấu hình Trino Delta Lake Catalog kết nối với MinIO
|   |-- config.properties             # Cấu hình bộ nhớ và các tham số thực thi truy vấn Trino
|-- report/
|   |-- YLC_report/                   # Báo cáo phân tích chuyên sâu cho dữ liệu Yellow Taxi
|   |-- FHV_report/                   # Báo cáo đánh giá chất lượng dữ liệu cho dòng xe FHV
|-- docker-compose.yml                # Tệp định nghĩa và khởi chạy hệ thống container
|-- Dockerfile                        # Custom image cho Airflow tích hợp OpenJDK 17 và PySpark
|-- requirements.txt                  # Danh mục các thư viện Python phụ thuộc
+-- .env.example                      # Tệp mẫu cấu hình các biến môi trường
```

---

## 4. Cơ chế Vận hành các Pipeline trên Airflow

Hệ thống bao gồm 2 DAG chính được quản lý và tự động hóa trên Apache Airflow:

### 4.1 DAG 1: taxi_monthly_pipeline (Medallion ETL Pipeline)

Pipeline xử lý biến đổi dữ liệu toàn diện qua 4 giai đoạn tuần tự:

```text
bronze_layer -> silver_layer -> gold_layer -> audit_layer
```

- **bronze_layer**:
  - Tải dữ liệu Parquet từ hệ thống CloudFront CDN của NYC TLC (hoặc thư mục nội bộ) và truyền thẳng (stream) vào `s3a://bronze/{dataset_type}_trips`.
  - Giữ trọn vẹn dữ liệu gốc và gắn kèm thông tin truy vết nguồn gốc.
- **silver_layer**:
  - Áp dụng bộ quy tắc kiểm định chất lượng dữ liệu (Quality Gates):
    - Kiểm tra tính hợp lý của thời gian (`pickup_datetime < dropoff_datetime`).
    - Kiểm tra khoảng cách di chuyển (`trip_distance > 0`).
    - Kiểm tra đơn giá và cước phí (`total_amount > 0`).
    - Kiểm tra vị trí đón/trả dựa trên danh mục phân vùng hợp lệ.
  - Các bản ghi vi phạm được tự động chuyển vào `s3a://bronze/quarantine`.
  - Các bản ghi hợp lệ được làm giàu thêm các chỉ số dẫn xuất và lưu vào bảng Delta `s3a://silver/{dataset_type}_trips` có phân vùng theo tháng (`source_month`).
- **gold_layer**:
  - Tổng hợp dữ liệu theo từng giờ và phân vùng (`hourly_zone_metrics`).
  - Tự động gọi thủ tục Trino để đăng ký bảng (`register_table`) và làm sạch bộ nhớ đệm metadata (`flush_trino_metadata_cache`).
- **audit_layer**:
  - Đối soát số lượng bản ghi giữa các tầng (Bronze, Silver, Quarantine, Gold).
  - Ghi nhận nhật ký chi tiết vào cơ sở dữ liệu PostgreSQL nhằm phục vụ theo dõi SLA và tính toàn vẹn của dữ liệu.

#### Tham số cấu hình khi kích hoạt DAG thủ công (Trigger DAG with config):

- `dataset_type`:
  - `yellow`: Dữ liệu xe taxi vàng truyền thống (mặc định).
  - `green`: Dữ liệu xe taxi xanh khu vực ngoại thành.
  - `fhv`: Dữ liệu xe hợp đồng dịch vụ truyền thống (For-Hire Vehicle).
  - `fhvhv`: Dữ liệu xe công nghệ lưu lượng cao (Uber, Lyft).
- `source_month`:
  - `"2025-01"`: Chạy duy nhất cho 1 tháng cụ thể.
  - `"2025-01..2025-06"`: Chạy liên tục cho một dải tháng.
  - `"2025"`: Chạy trọn vẹn toàn bộ 12 tháng của năm.
- `source_mode`:
  - `REMOTE_NYC_CDN` (Khuyến nghị): Tải và stream trực tiếp từ CDN vào MinIO, không tốn dung lượng ổ đĩa máy chủ.
  - `AUTO`: Ưu tiên đọc tập tin có sẵn trong thư mục `data/`, nếu chưa có sẽ tự động tải từ CDN.
  - `LOCAL`: Chỉ đọc các tập tin Parquet sẵn có trong thư mục `data/`.

### 4.2 DAG 2: taxi_weather_forecast_pipeline (Weather & 24h ML Forecast)

Được thiết lập lịch trình tự động vào lúc 00:00 UTC hàng ngày (`0 0 * * *`):

```text
refresh_weather_forecast -> generate_24h_forecast -> register_and_flush_trino
```

- **refresh_weather_forecast**: Gọi Open-Meteo REST API để cập nhật dữ liệu thời tiết thực tế gần nhất và dự báo 48 giờ tới, nạp vào `s3a://silver/dim_weather_hourly`.
- **generate_24h_forecast**:
  - Đọc mô hình LightGBM đã huấn luyện từ `dags/models/`.
  - Trích xuất đặc trưng thời gian, độ trễ và các chỉ số thời tiết (nhiệt độ, mưa, tuyết, gió).
  - Thực hiện suy luận dự báo nhu cầu và doanh thu cho từng giờ trong 24 giờ tiếp theo, ghi vào bảng `s3a://gold/forecast_hourly_metrics`.
- **register_and_flush_trino**: Tự động đồng bộ và làm tươi metadata trong Trino để dữ liệu dự báo có thể truy vấn được ngay.

---

## 5. Hướng dẫn Triển khai & Vận hành (Deployment Guide)

### 5.1 Khởi tạo Hệ thống với Docker Compose

1. Tạo tệp cấu hình biến môi trường từ tệp mẫu:

```bash
cp .env.example .env
```

2. Khởi chạy toàn bộ cụm dịch vụ:

```bash
docker compose up -d
```

3. Kiểm tra trạng thái sẵn sàng của các container:

```bash
docker compose ps
```

### 5.2 Danh mục Cổng và Giao diện Quản trị

| Dịch vụ | Địa chỉ Endpoint / Web UI | Tài khoản Mặc định | Chức năng Chính |
|---|---|---|---|
| Airflow Webserver | http://localhost:8090 | admin / 12345678 (hoặc theo .env) | Giao diện điều phối, quản lý và theo dõi DAGs |
| MinIO Console | http://localhost:9001 | admin / 12345678 | Quản lý hệ thống lưu trữ S3 Buckets |
| MinIO S3 API | http://localhost:9000 | Access/Secret key trong .env | Endpoint kết nối S3A cho Spark và Trino |
| Trino Web UI | http://localhost:8080 | trino | Theo dõi hiệu năng và chi tiết truy vấn phân tán |
| PostgreSQL | localhost:5432 | airflow / airflow (Database: airflow) | Lưu trữ metadata Airflow và bảng lịch sử kiểm toán |

---

## 6. Truy vấn và Kiểm tra Dữ liệu trên Trino

Mở giao diện dòng lệnh Trino CLI trực tiếp từ container:

```bash
docker exec -it trino trino --catalog delta
```

### 6.1 Kiểm tra danh mục Schema và Bảng

```sql
SHOW SCHEMAS;
SHOW TABLES FROM delta.bronze;
SHOW TABLES FROM delta.silver;
SHOW TABLES FROM delta.gold;
```

### 6.2 Đối soát dữ liệu giữa các tầng (Data Reconciliation)

```sql
SELECT '1. Bronze Yellow' AS layer, count(*) AS total_records FROM delta.bronze.yellow_trips
UNION ALL
SELECT '2. Bronze Quarantine', count(*) FROM delta.bronze.quarantine
UNION ALL
SELECT '3. Silver Yellow', count(*) FROM delta.silver.yellow_trips
UNION ALL
SELECT '4. Gold Hourly Metrics', count(*) FROM delta.gold.hourly_zone_metrics
UNION ALL
SELECT '5. Gold 24h Forecast', count(*) FROM delta.gold.forecast_hourly_metrics;
```

### 6.3 Phân tích nguyên nhân các bản ghi bị Quarantine

```sql
SELECT 
    _quarantine_reason,
    count(*) AS error_count
FROM delta.bronze.quarantine
GROUP BY _quarantine_reason
ORDER BY error_count DESC;
```

### 6.4 Top 10 khu vực có doanh thu cao nhất (Tầng Gold)

```sql
SELECT 
    borough,
    zone_name,
    SUM(trip_count) AS total_trips,
    ROUND(SUM(total_revenue), 2) AS grand_total_revenue,
    ROUND(AVG(tip_rate) * 100, 2) AS avg_tip_percentage
FROM delta.gold.hourly_zone_metrics
GROUP BY borough, zone_name
ORDER BY grand_total_revenue DESC
LIMIT 10;
```

### 6.5 Truy vấn kết quả dự báo 24h tới kết hợp yếu tố thời tiết

```sql
SELECT 
    forecast_timestamp,
    temp_celsius,
    precipitation_mm,
    predicted_demand_trips,
    predicted_revenue_usd
FROM delta.gold.forecast_hourly_metrics
ORDER BY forecast_timestamp ASC;
```

---

## 7. Giám sát Nhật ký Kiểm toán Pipeline trên PostgreSQL

Kiểm tra số liệu thống kê và lịch sử thực thi của các lần chạy pipeline thông qua bảng `pipeline_execution_history`:

```bash
docker exec -it postgres psql -U airflow -d airflow -c "
SELECT 
    id,
    dag_id,
    dataset_type,
    source_month,
    duration_seconds,
    bronze_rows,
    silver_rows,
    quarantine_rows,
    gold_rows,
    status,
    created_at
FROM pipeline_execution_history
ORDER BY id DESC
LIMIT 10;
"
```

---

## 8. Bộ Script Phân tích và Trực quan hóa Dữ liệu

Cài đặt các thư viện cần thiết trên máy host (nếu muốn chạy các script sinh biểu đồ từ xa qua Trino):

```bash
pip install -r requirements.txt
```

Các script phân tích trong thư mục `scripts/`:

```bash
# 1. Vẽ Dashboard ma trận nhiệt về nhu cầu, tốc độ di chuyển và tương quan
python scripts/plot_heatmaps.py

# 2. Vẽ biểu đồ phân phối đơn biến và biểu đồ phân tán
python scripts/plot_hist_scatter.py

# 3. Vẽ bản đồ nhiệt không gian GIS theo quận và phân vùng taxi NYC
python scripts/plot_spatial_heatmaps.py

# 4. So sánh kết quả dự báo LightGBM với thực tế theo chuỗi thời gian
python scripts/plot_forecast_vs_actual.py

# 5. Bộ script phân tích chuyên biệt cho dòng xe hợp đồng FHV
python scripts/plot_fhv_heatmaps.py
python scripts/plot_fhv_hist_scatter.py
python scripts/plot_fhv_spatial.py
```

Các báo cáo phân tích chi tiết đã được xuất sẵn tại:
- [report/YLC_report/README.md](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_lakehouse/report/YLC_report/README.md)
- [report/FHV_report/README.md](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_lakehouse/report/FHV_report/README.md)
- [report/FHV_report/FHV_DATA.md](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_lakehouse/report/FHV_report/FHV_DATA.md)

---

## 9. Dừng và Dọn dẹp Môi trường

```bash
# Tạm dừng và hạ toàn bộ cụm container
docker compose down

# Xóa toàn bộ container cùng với các volume dữ liệu (MinIO data, PostgreSQL, Airflow)
docker compose down -v
```
