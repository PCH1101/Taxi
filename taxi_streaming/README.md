# NYC Taxi Real-Time Streaming Pipeline

Nền tảng kỹ thuật dữ liệu thời gian thực (End-to-End Real-Time Data Engineering & Mission Control Platform) mô phỏng, xử lý luồng sự kiện tốc độ cao (400+ events/giây) và giám sát trực quan 3D hơn 500 xe taxi (Yellow, Green, FHVHV / Uber & Lyft) hoạt động đồng thời trên 265 Taxi Zones tại New York City.

---

## 1. Kiến Trúc Hệ Thống (System Architecture)

Hệ thống được thiết kế theo mô hình 6 Tầng Microservices vận hành độc lập trên Docker Network, đảm bảo luồng dữ liệu liên tục từ tệp tin Parquet raw đến giao diện WebGL 3D thời gian thực với độ trễ dưới 1 giây.

### 1.1 Sơ Đồ Kiến Trúc Luồng Tổng Thể

```text
========================================================================================
                              KIEN TRUC LUONG DU LIEU THOI GIAN THUC
========================================================================================

  +-----------------------+       +-----------------------+       +-----------------------+
  |      SIMULATOR        |       |     APACHE KAFKA      |       |    FLINK PROCESSOR    |
  |  (Parquet Replay &    |------>|  (KRaft Mode, Topic   |------>| (Sliding Window 60s,  |
  |   OSRM Interpolation, |       |   taxi.trips.live,    |       |  Congestion Engine,   |
  |   400+ events/giay)   |       |   6 Partitions, Gzip) |       |  Dominance Analysis)  |
  +-----------------------+       +-----------------------+       +-----------------------+
                                                                              |
                                                                              | Snapshot Sink
                                                                              v
  +-----------------------+       +-----------------------+       +-----------------------+
  |     WEB DASHBOARD     |       |      API GATEWAY      |       |       REDIS 7.2       |
  | (React 18 + Deck.gl 3D|<------| (FastAPI + WebSockets |<------|  (In-Memory State &   |
  |  ECharts 60 FPS SPA)  |  WSS  |  Fan-out Engine,      | Cache |   Pub/Sub Store,      |
  |                       |       |  OSRM Routing Proxy)  | Poll  |   KPI Atomic Counter) |
  +-----------------------+       +-----------------------+       +-----------------------+
========================================================================================
```

### 1.2 Chi Tiết 6 Tầng Microservices

1. **Tầng Ingestion & Simulator (`simulator/`)**:
   - Đọc song song dữ liệu Parquet thực tế từ NYC TLC (Yellow Taxi, Green Boro Taxi, FHVHV Uber/Lyft).
   - Nội suy tọa độ di chuyển theo thời gian thực bám sát mạng lưới đường bộ OSRM (Open Source Routing Machine).
   - Sử dụng AsyncIO Queue (buffer 4,000 sự kiện) và `aiokafka` Async Producer để phát luồng **400 sự kiện/giây** chia đều theo tỷ trọng cấu hình (Yellow 40%, Green 10%, FHVHV 50%).

2. **Tầng Message Broker (`kafka/`)**:
   - Apache Kafka 3.8.0 vận hành ở chế độ **KRaft** (Kafka Raft Metadata Mode - loại bỏ hoàn toàn phụ thuộc ZooKeeper).
   - Topic nghiệp vụ: `taxi.trips.live` được phân bổ trên **6 partitions** để tối ưu hóa khả năng đọc ghi song song.
   - Cơ chế nén `gzip` và thiết lập giới hạn lưu giữ (retention: 1 giờ / 512 MB) ngăn ngừa tràn đĩa trên môi trường phát triển.

3. **Tầng Stream Processing Engine (`flink_processor/`)**:
   - Đọc luồng sự kiện liên tục từ Kafka consumer group `taxi-flink-processor-group`.
   - Duy trì **Cửa sổ trượt thời gian 60 giây (Sliding Window 60s)** để tính toán mật độ xe trên 265 Taxi Zones.
   - Đánh giá mức độ ùn tắc giao thông đô thị (`compute_zone_dominance`), xác định hãng xe thống lĩnh từng khu vực, tính doanh thu đang chạy trên đường (*in-flight fare*) và tự động loại bỏ các xe dừng hoạt động (*stale vehicles*).

4. **Tầng In-Memory State & Pub/Sub Store (`redis/`)**:
   - Redis 7.2 Alpine đóng vai trò làm kho lưu trữ trạng thái trung tâm với tốc độ truy xuất microsecond.
   - Lưu trữ snapshot mật độ toàn thành phố (`kv:latest_density_metrics`), bản đồ tranh chấp thị phần (`kv:power_map_snapshot` TTL 10s), và bảng băm lưu trữ các bộ đếm KPI vận hành (`hash:realtime_kpis`).

5. **Tầng Real-Time API Gateway (`api_gateway/`)**:
   - Xây dựng trên nền tảng FastAPI và ASGI Server Uvicorn.
   - Thiết lập kết nối hai chiều WebSocket (`/ws/fleet`, `/ws/kpis`) với cơ chế Fan-out hiệu năng cao, đẩy dữ liệu tới hàng loạt client đồng thời mà không nghẽn luồng.
   - Đóng vai trò Reverse Proxy cho OSRM Routing Engine (`/api/route`) phục vụ truy vấn đường đi thực tế.

6. **Tầng Mission Control Web SPA (`web_dashboard/`)**:
   - Ứng dụng Single Page Application xây dựng trên React 18, TypeScript và Vite.
   - Tích hợp Deck.gl 9.0 (WebGL 3D GPU-Accelerated 60 FPS) kết hợp MapLibre GL dựng hình hàng trăm phương tiện di chuyển mượt mà.
   - Trực quan hóa dữ liệu đo xa (Telemetry) bằng Apache ECharts 5.5, quản lý trạng thái bằng Zustand và phong cách thiết kế Dark Cyberpunk chuẩn mực.

---

## 2. Ngăn Xếp Công Nghệ Chính (Core Tech Stack)

| Thành phần | Công nghệ / Phiên bản | Vai trò kỹ thuật trong Hệ thống |
|---|---|---|
| Event Producer | Python 3.11, AsyncIO, `aiokafka`, PyArrow | Đọc file Parquet 19 cột canonical, nội suy tọa độ GPS và phát luồng 400 events/giây |
| Message Broker | Apache Kafka 3.8.0 (KRaft Mode) | Hệ thống hàng đợi phân tán chịu lỗi cao, điều phối luồng dữ liệu trên 6 partitions |
| Stream Processor | Python 3.11, Sliding Window Engine | Xử lý cửa sổ trượt 60 giây, phát hiện điểm nóng giao thông và tỷ trọng chiếm lĩnh vùng |
| In-Memory Store | Redis 7.2 Alpine | Quản lý trạng thái tức thời, bộ đếm KPI nguyên tử và kênh Pub/Sub thời gian thực |
| API Gateway | FastAPI 0.110+, Uvicorn, WebSockets | Quản lý kết nối WebSocket tần số cao, phân phối dữ liệu (fan-out) và định tuyến OSRM |
| Frontend Framework | React 18, TypeScript, Vite | Nền tảng Single Page Application hiệu năng cao với thời gian tải và dựng hình tối ưu |
| 3D Geospatial Engine | Deck.gl 9.0, MapLibre GL | Hiển thị 500+ xe dưới dạng 3D GPU-accelerated 60 FPS, lớp Heatmap và lớp Radar |
| Analytics & Charts | Apache ECharts 5.5, `echarts-for-react` | Biểu đồ sóng Telemetry, Boxplot, Radar Spider và Ma trận nhiệt Borough Transition |
| State Management | Zustand 4.5 | Quản lý trạng thái luồng dữ liệu thời gian thực độc lập, hạn chế tối đa re-render thừa |
| Routing Engine | OSRM Driving Engine API | Thuật toán định tuyến đường bộ thực tế bám sát mạng lưới giao thông New York City |
| Container Platform | Docker & Docker Compose v2 | Đóng gói, cô lập và kết nối mạng nội bộ an toàn cho toàn bộ 6 microservices |

---

## 3. Cấu Trúc Mã Nguồn (Repository Structure)

```text
taxi_streaming/
|-- api_gateway/        # FastAPI WebSockets broadcast, OSRM routing proxy & REST API
|-- data/               # Metadata 265 Taxi Zones & tệp tin Parquet mẫu TLC
|-- docs/               # Tài liệu Data Contracts (DATA_FLOW.md) & Design Tokens (DESIGN.md)
|-- flink_processor/    # Engine xử lý luồng, Sliding Window 60s & Redis Sink
|-- simulator/          # Trình phát luồng sự kiện vi mô (400 events/giây) & Kafka Producer
|-- web_dashboard/      # Mission Control Web SPA (React 18, Deck.gl 3D, ECharts)
|-- docker-compose.yml  # Cấu hình điều phối cụm 6 microservices
+-- README.md           # Tài liệu hướng dẫn tổng quan và vận hành hệ thống
```

---

## 4. Hướng Dẫn Khởi Chạy Nhanh (Deployment & Quick Start)

### 4.1 Yêu Cầu Môi Trường
- **Docker Engine** 24.0+ và **Docker Compose** v2 trở lên.
- Dung lượng RAM khả dụng tối thiểu: **4 GB** (khuyến nghị 8 GB để vận hành đồng thời Kafka, Redis, Flink và SPA).

### 4.2 Khởi Động Toàn Bộ Dịch Vụ

1. Di chuyển vào thư mục dự án:
```bash
cd /run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming
```

2. Khởi chạy toàn bộ hệ thống bằng Docker Compose:
```bash
docker compose up -d --build
```

3. Kiểm tra trạng thái sẵn sàng của 6 dịch vụ:
```bash
docker compose ps
```

### 4.3 Danh Mục Cổng Truy Cập và Điểm Cuối Dịch Vụ

| Dịch vụ | Địa chỉ URL / Port | Thông tin Xác thực | Chức năng Kỹ thuật |
|---|---|---|---|
| Mission Control Web SPA | http://localhost:3000 | Truy cập tự do | Bảng điều hành giám sát luồng xe 3D Deck.gl và Telemetry |
| API Gateway (Swagger UI) | http://localhost:8080/docs | Truy cập tự do | Tài liệu REST API, kiểm tra WebSocket `/ws/fleet`, `/ws/kpis` |
| Kafka Broker External | localhost:19092 | PLAINTEXT | Cổng kết nối Kafka cho client bên ngoài mạng máy chủ |
| Redis In-Memory Store | localhost:6379 | Không mật khẩu | Truy xuất dữ liệu tức thời qua Redis CLI / Key-Value Store |

---

## 5. Các Không Gian Tác Chiến Trên Dashboard (Mission Control)

Giao diện điều hành được phân chia thành 3 màn hình chuyên biệt thông qua thanh điều hướng `TabNav`:

### 5.1 Tab 1: 3D Fleet Command Map
- **Engine Đồ Họa 3D Deck.gl (60 FPS):** Hiển thị vị trí thực tế của hơn 500 phương tiện với màu sắc phân định theo dòng xe:
  - Màu vàng (`#FACC15`): Xe taxi vàng truyền thống (Yellow Cab).
  - Màu xanh lá (`#22C55E`): Xe taxi xanh ngoại thành (Green Boro Taxi).
  - Màu tím (`#A855F7`): Xe công nghệ lưu lượng cao (FHVHV - Uber & Lyft).
- **Chế Độ Hiển Thị Màu Linh Hoạt:** Cho phép chuyển đổi màu xe theo *Loại xe (Taxi Type)*, *Vận tốc (Speed MPH)*, *Mức cước (Fare Amount)* hoặc *Hiệu suất (Efficiency)*.
- **Các Lớp Bản Đồ Tương Tác:** Bật/tắt bản đồ nhiệt nhu cầu đón khách (*Demand Heatmap*), vòng tròn radar phát sáng tại khu vực đông nhất (*Busiest Zone Radar*), và 3 sân bay quốc tế (*JFK, LGA, EWR*).
- **Interactive Driver Focus HUD:** Nhấp chọn bất kỳ xe nào để mở HUD chi tiết: vẽ lộ trình thực tế qua OSRM (nhánh đã qua màu Cyan, nhánh sắp tới màu Crimson), tự động tính điểm tối ưu lộ trình (*Route Detour Score*).

### 5.2 Tab 2: Live Stream Telemetry & Trends
- **4 Thẻ Chỉ Số Vận Hành Tức Thời (Real-Time KPIs):**
  - *Active Fleet Deployed*: Số lượng phương tiện đang lăn bánh thực tế trên toàn thành phố.
  - *Ingestion Throughput*: Tốc độ nạp sự kiện vi mô qua Kafka/Flink (events/giây).
  - *In-Flight Fare Revenue*: Tổng giá trị cước của các chuyến đi đang diễn ra trên đường.
  - *Fleet Average Speed*: Vận tốc trung bình của toàn đội xe và cảnh báo ùn tắc.
- **Hệ Thống 3 Biểu Đồ Phân Tích Đồng Bộ:**
  1. *Top Congested Pickup Hubs (Hotspots Bar Chart)*: Xếp hạng 8 điểm nóng tập trung lượng xe đón trả khách đông nhất.
  2. *Streaming Throughput & Velocity*: Biểu đồ sóng kép tự động co giãn trục Y hiển thị nhịp thở xử lý `ops/s` và vận tốc `MPH`.
  3. *Fare Value Distribution ($ USD)*: Biểu đồ Histogram liên tục kết hợp đường mật độ phân phối cước phí.
- **Micro-Batch Live Trip Feed:** Bảng cập nhật sự kiện vi mô kèm tính năng *Click-to-Inspect* — nhấp vào bất kỳ dòng nào để camera 3D bay tới định vị xe ngay lập tức.

### 5.3 Tab 3: Fleet Analytics & Deep Intelligence
- **3-Fleet Scoreboard:** Bảng so sánh trực diện thị phần, doanh thu trung bình, vận tốc và tỷ lệ hoàn thành chuyến giữa Yellow, Green và FHVHV.
- **Borough Transition Matrix Heatmap:** Ma trận nhiệt trực quan hóa các luồng dịch chuyển đón - trả khách giữa 5 quận (Manhattan, Queens, Brooklyn, Bronx, Staten Island).
- **5-Axis Fleet Performance Radar:** Biểu đồ mạng nhện đánh giá 5 chiều: Tốc độ trung bình, Cước bình quân, Độ phủ sóng, Tỷ lệ đón sân bay, và Doanh thu trên mỗi dặm.
- **Fare Outlier Box Plot & Trip Bubble Scatter:** Phân tích độ lệch chuẩn cước phí và mối tương quan đa biến giữa Quãng đường - Thời gian - Cước phí.

---

## 6. Cấu Hình Biến Môi Trường (Environment Variables)

Các tham số điều khiển được quản lý tập trung trong [docker-compose.yml](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/docker-compose.yml):

| Biến môi trường | Dịch vụ áp dụng | Giá trị khuyến nghị | Ý nghĩa vận hành |
|---|---|---|---|
| `SOURCE_MODE` | `simulator` | `PARQUET_REPLAY` | Chế độ phát dữ liệu (`PARQUET_REPLAY` hoặc `SYNTHETIC_STREAM`) |
| `ENABLED_DATASETS` | `simulator` | `YELLOW,GREEN,FHVHV` | Danh sách các tập dữ liệu phương tiện được kích hoạt |
| `EVENTS_PER_SECOND` | `simulator` | `400.0` | Tần số phát sự kiện vi mô mục tiêu |
| `BATCH_SIZE` | `simulator` | `100` | Số lượng sự kiện đóng gói trong một micro-batch |
| `MAX_CONCURRENT_TRIPS` | `simulator` | `400` | Số lượng chuyến đi hoạt động đồng thời trên bản đồ |
| `SLIDING_WINDOW_SECONDS` | `flink-processor` | `60` | Độ dài cửa sổ trượt thời gian phân tích mật độ xe |
| `DENSITY_PUBLISH_INTERVAL`| `flink-processor` | `2.0` | Chu kỳ cập nhật snapshot mật độ xuống Redis (giây) |
| `REDIS_URL` | `api-gateway`, `flink-processor` | `redis://redis:6379/0` | Chuỗi kết nối mạng nội bộ đến Redis State Store |

---

## 7. Lệnh Vận Hành & Gỡ Lỗi Thường Dùng (Operations & Debugging)

```bash
# 1. Kiem tra trang thai hoat dong cua toan bo cum 6 containers
docker compose ps

# 2. Theo doi nhat ky logs truc tiep theo tung dich vu
docker compose logs -f simulator           # Logs phat su kien Kafka
docker compose logs -f flink-processor     # Logs xu ly cua so truot Flink
docker compose logs -f api-gateway         # Logs WebSocket va REST API
docker compose logs -f web-dashboard       # Logs Nginx Web Server

# 3. Chay thu nghiem Simulator o che do Dry-Run doc lap (khong can Kafka)
python simulator/main.py --dry-run -n 50

# 4. Rebuild va cap nhat nhanh Web Dashboard khi sua doi giao dien
docker compose build web-dashboard && docker compose up -d --no-deps web-dashboard

# 5. Dung va giai phong toan bo tai nguyen container
docker compose down
```

---

## 8. Tài Liệu Kỹ Thuật Tham Khảo (Documentation References)

- **Đặc tả luồng dữ liệu & Data Contracts:** [docs/DATA_FLOW.md](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/docs/DATA_FLOW.md)
- **Hệ thống Design Tokens & Cyberpunk Theme:** [docs/DESIGN.md](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/docs/DESIGN.md)
- **Báo cáo khám phá dữ liệu Parquet:** [data/DATA_DISCOVERY.md](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/data/DATA_DISCOVERY.md)
- **Nguồn dữ liệu gốc:** [NYC Taxi and Limousine Commission (TLC) Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
