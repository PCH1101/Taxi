# Kiến Trúc Luồng Dữ Liệu - NYC Taxi Real-Time Pipeline

> **Tài liệu đặc tả kiến trúc luồng dữ liệu thời gian thực (End-to-End Data Pipeline Architecture)**  
> Mô phỏng, xử lý luồng sự kiện tốc độ cao và trực quan hóa hơn 500 phương tiện di chuyển đồng thời trên 265 Taxi Zones tại New York City.

---

## 1. Sơ Đồ Kiến Trúc Luồng Tổng Thể (End-to-End Architecture)

```text
==================================================================================================
                                TẦNG 1: INGESTION & SIMULATOR
  +------------------------+        +------------------------+
  | TLC Parquet Replay     |        | Synthetic Generator    |
  | (Yellow, Green, FHVHV) |        | (Zone-weighted Spawner)|
  +-----------+------------+        +-----------+------------+
              |                                 |
              +----------------+----------------+
                               |
                               v
                [ asyncio.Queue (Buffer: 4000) ]
                               |
                [ AIOKafkaProducer (Batch: 100) ]
===============================+==================================================================
                               | JSON Telemetry Stream (400+ events/giây)
                               v
==================================================================================================
                          TẦNG 2: MESSAGE BROKER (APACHE KAFKA)
  +--------------------------------------------------------------------------------------------+
  | Topic: taxi.trips.live  |  6 Partitions  |  KRaft Mode (3.8.0)  |  Retention: 1h / 512 MB  |
  +--------------------------------------------------------------------------------------------+
===============================+==================================================================
                               | Consumer Group: taxi-flink-processor-group (auto_offset=latest)
                               v
==================================================================================================
                       TẦNG 3: STREAM PROCESSING ENGINE (FLINK PROCESSOR)
  +--------------------------------------------------------------------------------------------+
  | FlinkStreamEngine (Python Streaming Processor)                                             |
  |  +-- In-Memory Sliding Window (60s State Window, Stale Eviction)                           |
  |  +-- Zone Congestion Classifier (265 Zones: LOW / MODERATE / HEAVY / CRITICAL)             |
  |  +-- Fleet Territory Dominance Engine (Territory Ratios & Battleground Status)             |
  |  +-- In-Flight Revenue & Velocity Metrics Aggregator                                       |
  |  +-- Snapshot Trigger (Micro-batch interval: 2.0s)                                         |
  +--------------------------------------------------------------------------------------------+
===============================+==================================================================
                               | Redis Pipeline Write (SET / PUBLISH / HSET)
                               v
==================================================================================================
                       TẦNG 4: IN-MEMORY STATE & PUB/SUB STORE (REDIS 7.2)
  +--------------------------------------------------------------------------------------------+
  |  * kv:latest_density_metrics   -> JSON Snapshot 265 zones + danh sách xe đang hoạt động    |
  |  * kv:power_map_snapshot       -> Thị phần kiểm soát & khu vực tranh chấp (TTL 10s)       |
  |  * hash:realtime_kpis          -> Bộ đếm KPI vận hành & metadata hệ thống                  |
  |  * channel:density_metrics     -> Pub/Sub real-time broadcast channel                      |
  +--------------------------------------------------------------------------------------------+
===============================+==================================================================
                               | Async Subscriber / Memory Cache Query
                               v
==================================================================================================
                       TẦNG 5: REAL-TIME API GATEWAY (FASTAPI + WEBSOCKETS)
  +--------------------------------------------------------------------------------------------+
  | FastAPI + Uvicorn Async Server                                                             |
  |  +-- WebSocket Endpoints: /ws/fleet (Fleet telemetry), /ws/kpis (KPI broadcast)           |
  |  +-- High-throughput Fan-out Engine (Phân phối đồng thời hàng loạt Web clients)           |
  |  +-- OSRM Routing Proxy: /api/route (Định tuyến đường bộ thực tế theo mạng lưới NYC)       |
  +--------------------------------------------------------------------------------------------+
===============================+==================================================================
                               | WSS Streams & JSON REST APIs
                               v
==================================================================================================
                       TẦNG 6: MISSION CONTROL WEB SPA (REACT 18 + DECK.GL)
  +--------------------------------------------------------------------------------------------+
  | React 18, TypeScript, Vite, Deck.gl 9.0 (WebGL 3D GPU-Accelerated 60 FPS), ECharts 5.5     |
  |  +-- Tab 1: 3D Fleet Command Map (500+ xe 3D, Heatmap, Radar, OSRM Route HUD)              |
  |  +-- Tab 2: Live Stream Telemetry & Trends (KPIs, Throughput, Velocity, Fare Histogram)     |
  |  +-- Tab 3: Fleet Analytics & Deep Intelligence (Scoreboard, Borough Heatmap, Radar 5 trục) |
  +--------------------------------------------------------------------------------------------+
==================================================================================================
```

---

## 2. Chi Tiết Các Tầng Xử Lý Trong Pipeline

### Tầng 1: Ingestion & Simulator

- **Mã nguồn:**
  - [simulator/main.py](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/simulator/main.py)
  - [simulator/generator/](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/simulator/generator)
  - [simulator/loaders/](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/simulator/loaders)
  - [simulator/models/](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/simulator/models)
  - [simulator/producer/](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/simulator/producer)
  - [simulator/zones/](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/simulator/zones)

- **Đặc điểm vận hành kỹ thuật**:
  1. **Hỗ trợ 3 dòng xe NYC TLC**:
     - **Yellow Taxi (`YELLOW`)**: Taxi vàng truyền thống tập trung tại Manhattan và 2 sân bay quốc tế (ID: `yt-*`). Trọng số mặc định: **40%**.
     - **Green Taxi (`GREEN`)**: Boro Taxi phục vụ khu vực ngoại ô và Upper Manhattan (ID: `gt-*`). Trọng số mặc định: **10%**.
     - **FHVHV (`FHVHV`)**: Xe công nghệ lưu lượng cao (Uber và Lyft) phủ khắp 5 quận (ID: `hv-*`). Trọng số mặc định: **50%**.
  2. **2 Cơ chế nạp dữ liệu (`SOURCE_MODE`)**:
     - `PARQUET_REPLAY`: Đọc trực tiếp từ tệp tin Parquet thực tế với 19 cột canonical chuẩn TLC (`yellow_tripdata_2026-04.parquet`, `green_tripdata_2026-04.parquet`, `fhvhv_tripdata_2026-04.parquet`).
     - `SYNTHETIC_STREAM`: Sinh hành trình dựa trên trọng số phân bố 265 Taxi Zones và mô hình toán học vận tốc theo khung giờ trong ngày.
  3. **Kiến trúc Producer bất đồng bộ kép (Dual-Task Async Architecture)**:
     - **Task A (`_event_generator`)**: Khởi tạo cuốc xe mới hoặc nội suy tọa độ GPS theo thời gian thực cho xe đang di chuyển, đẩy vào `asyncio.Queue` (buffer tối đa 4,000 sự kiện).
     - **Task B (`_batch_sender`)**: Lấy dữ liệu từ hàng đợi theo lô (`BATCH_SIZE=100`) và gửi fire-and-forget qua `aiokafka.AIOKafkaProducer`.
  4. **Vòng đời sự kiện (3-State Lifecycle)**:
     $$\text{TRIP\_STARTED (progress=0.0)} \longrightarrow \text{LOCATION\_PING (0.0 < progress < 1.0)} \longrightarrow \text{TRIP\_COMPLETED (progress=1.0)}$$

---

### Tầng 2: Message Broker (Apache Kafka KRaft)

- **Phiên bản:** `apache/kafka:3.8.0` (vận hành ở chế độ KRaft, không phụ thuộc cụm ZooKeeper).
- **Topic nghiệp vụ:** `taxi.trips.live`
- **Thông số cấu hình tối ưu**:
  - **Số lượng Partitions:** `6` (cho phép nhiều consumer instances đọc song song không bị khóa luồng).
  - **Replication Factor:** `1` (phù hợp với môi trường container cục bộ).
  - **Log Retention Time:** `3600000 ms` (1 giờ).
  - **Log Retention Bytes:** `536870912 bytes` (512 MB - cơ chế chống đầy ổ đĩa trên máy chủ).
  - **Nén dữ liệu:** `gzip` (giảm thiểu 60-70% băng thông truyền tải trên mạng nội bộ).
  - **Khởi tạo tự động:** Container `kafka-init` thực thi script kiểm tra tính sẵn sàng của broker trước khi tạo topic.

---

### Tầng 3: Stream Processing Engine (Flink Processor)

- **Mã nguồn:**
  - [flink_processor/flink_streaming_job.py](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/flink_processor/flink_streaming_job.py)
  - [flink_processor/config.py](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/flink_processor/config.py)

- **Các thuật toán xử lý trọng tâm**:
  1. **Cửa Sổ Trượt Thời Gian (Sliding Window 60s)**:
     - Duy trì trạng thái về vị trí GPS, tốc độ, giá cước, điểm đón và điểm trả của từng `trip_id`.
     - Cơ chế **Stale Eviction**: Tự động dọn dẹp các xe không có tín hiệu ping mới qua thời gian quy định (`SLIDING_WINDOW_SECONDS=60`) hoặc khi nhận sự kiện hoàn thành `TRIP_COMPLETED`.
  2. **Bộ Phân Loại Mật Độ & Ùn Tắc Giao Thông (Zone Congestion Classifier)**:
     - Phân loại mức độ tập trung xe trên 265 Taxi Zones theo 4 cấp độ:
       - `LOW`: Dưới 3 xe.
       - `MODERATE`: Từ 3 đến 6 xe.
       - `HEAVY`: Từ 7 đến 11 xe.
       - `CRITICAL_CONGESTION`: Từ 12 xe trở lên.
  3. **Thuật Toán Thị Phần Kiểm Soát (Territory Dominance & Power Map)**:
     - Hàm `compute_zone_dominance()` đánh giá tỷ trọng số lượng xe của 3 đội tại từng Zone:
       - `dominant_fleet`: Đội xe nắm giữ số lượng phương tiện cao nhất.
       - `dominance_ratio`: Tỷ lệ chiếm lĩnh ($\frac{\text{Count}_{\text{dom}}}{\text{Total}}$).
       - `battle_status`:
         - `EMPTY`: 0 xe trong zone.
         - `DOMINATED`: Đội dẫn đầu chiếm từ 50% trở lên và bỏ xa các đội khác.
         - `CONTESTED`: Vùng tranh chấp quyết liệt (chênh lệch giữa top 2 đội chỉ từ 1 xe hoặc tỷ lệ thị phần cách nhau dưới 20%).
         - `BALANCED`: Phân bổ đồng đều giữa các đội xe.
  4. **Cơ Chế Ghi Snapshot Xuống Redis (Micro-batch Redis Sink Trigger)**:
     - Định kỳ mỗi chu kỳ `DENSITY_PUBLISH_INTERVAL` (2.0s), engine đóng gói toàn bộ thông số và đẩy xuống Redis bằng kỹ thuật `Pipeline`.

---

### Tầng 4: In-Memory State & Pub/Sub Store (Redis 7.2)

- **Phiên bản:** `redis:7.2-alpine` (Cổng mặc định `6379`).
- **Cấu Trúc Key & Data Contracts**:

| Redis Key / Channel | Kiểu dữ liệu | TTL | Mô tả chức năng |
|---|---|---|---|
| `kv:latest_density_metrics` | String (JSON) | Không | Snapshot toàn bộ 265 zones, danh sách xe active (tọa độ, vận tốc, tiến trình), phân bố quận huyện và 3 đội xe. |
| `kv:power_map_snapshot` | String (JSON) | **10 giây** | Danh sách zone tranh chấp (`invasion_zones`) và số lượng zone mỗi đội nắm quyền (`territory_counts`). Tự động hủy nếu pipeline dừng hoạt động. |
| `hash:realtime_kpis` | Hash | Không | Bộ đếm KPI vận hành nguyên tử: `total_active_vehicles`, `total_events_processed`, `last_density_update`, `engine`. |
| `channel:density_metrics` | Pub/Sub Channel | Không áp dụng | Kênh phát sóng snapshot theo thời gian thực mỗi 2 giây cho các consumer lắng nghe trực tiếp. |

---

### Tầng 5: Real-Time API Gateway (FastAPI + WebSockets)

- **Mã nguồn:**
  - [api_gateway/main.py](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/api_gateway/main.py)
  - [api_gateway/routers/](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/api_gateway/routers)
  - [api_gateway/services/](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/api_gateway/services)

- **Các điểm cuối (Endpoints) chính**:
  - `WebSocket /ws/fleet`: Truy xuất và broadcast toàn bộ vị trí phương tiện, tốc độ và hướng di chuyển tới giao diện 3D Deck.gl.
  - `WebSocket /ws/kpis`: Phát các chỉ số tổng hợp (xe hoạt động, tốc độ xử lý, doanh thu in-flight) với tần số 1s.
  - `GET /api/route`: OSRM Routing Proxy nhận tọa độ (kinh độ, vĩ độ) điểm đón/trả, gọi OSRM Engine và trả về tập hợp điểm polyline bám sát mặt đường phố NYC.
  - `GET /api/health`: Kiểm tra trạng thái kết nối tới Redis và tiến trình hệ thống.

---

### Tầng 6: Mission Control Web SPA (React 18 + Deck.gl 3D)

- **Mã nguồn:**
  - [web_dashboard/src/App.tsx](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/web_dashboard/src/App.tsx)
  - [web_dashboard/src/components/map/](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/web_dashboard/src/components/map)
  - [web_dashboard/src/components/telemetry/](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/web_dashboard/src/components/telemetry)
  - [web_dashboard/src/components/analytics/](file:///run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming/web_dashboard/src/components/analytics)

- **Giao diện chia thành 3 không gian tác chiến**:
  - **Tab 1: 3D Fleet Command Map**: Render GPU 60 FPS bằng Deck.gl, hiển thị vị trí hơn 500 xe, Heatmap đón khách, Radar báo động tại zone đông nhất và đường dẫn OSRM thực tế khi click chọn phương tiện.
  - **Tab 2: Live Stream Telemetry & Trends**: Theo dõi nhịp đập hệ thống thông qua 4 thẻ KPI thời gian thực, biểu đồ sóng Ingestion Throughput, biểu đồ phân phối cước phí và bảng Micro-batch Live Trip Feed.
  - **Tab 3: Fleet Analytics & Deep Intelligence**: Bảng so sánh 3-Fleet Scoreboard, ma trận chuyển đổi lưu thông giữa các quận (Borough Transition Heatmap), và biểu đồ mạng nhện 5 trục đánh giá hiệu năng đội xe.

---

## 3. Đặc Tả Schema Dữ Liệu Sự Kiện (Canonical Event Schema)

Mỗi thông điệp truyền trên Kafka topic `taxi.trips.live` tuân thủ Pydantic Model chuẩn:

```json
{
  "trip_id": "yt-202604-000142",
  "dataset_source": "YELLOW",
  "event_type": "LOCATION_PING",
  "pickup_datetime": "2026-04-12T14:30:00",
  "dropoff_datetime": "2026-04-12T14:48:00",
  "PULocationID": 237,
  "DOLocationID": 161,
  "pickup_zone_name": "Upper East Side South",
  "pickup_borough": "Manhattan",
  "dropoff_zone_name": "Midtown Center",
  "dropoff_borough": "Manhattan",
  "current_lat": 40.7682,
  "current_lng": -73.9621,
  "passenger_count": 1,
  "trip_distance": 2.45,
  "total_amount": 16.50,
  "progress_ratio": 0.42,
  "timestamp": 1776004245.12,
  "datetime_utc": "2026-04-12T18:30:45.120000+00:00"
}
```

### Ý nghĩa các trường dữ liệu chính:
- `trip_id`: Định danh duy nhất của cuốc xe (tiền tố `yt-` cho Yellow, `gt-` cho Green, `hv-` cho FHVHV).
- `dataset_source`: Nguồn dòng xe (`YELLOW`, `GREEN`, `FHVHV`).
- `event_type`: Loại sự kiện trong vòng đời (`TRIP_STARTED`, `LOCATION_PING`, `TRIP_COMPLETED`).
- `PULocationID`, `DOLocationID`: Mã định danh 265 Taxi Zones theo chuẩn NYC TLC.
- `current_lat`, `current_lng`: Tọa độ vị trí hiện tại của phương tiện sau khi nội suy.
- `progress_ratio`: Tiến độ hành trình từ `0.0` (vừa đón khách) đến `1.0` (đã trả khách).

---

## 4. Chỉ Số Hiệu Năng & Độ Trễ (Performance Benchmarks & SLAs)

| Hạng mục | Thông số cam kết | Cơ chế kỹ thuật bảo đảm |
|---|---|---|
| **Tốc độ sinh sự kiện (Simulator)** | 400+ events/giây | `asyncio.Queue` (buffer 4000) kết hợp `aiokafka` batch sending |
| **Độ trễ truyền tin Kafka (Broker Latency)** | < 5 ms | Kafka 3.8.0 KRaft mode kết nối nội bộ Docker Network |
| **Chu kỳ xử lý Stream (Flink Window Tick)** | 2.0 giây | Sliding Window bộ nhớ 60 giây + Redis Pipeline Write |
| **Độ trễ phát sóng WebSocket (Fan-out Latency)** | < 20 ms | FastAPI async event loop và Broadcast channels |
| **Tốc độ khung hình giao diện (UI Frame Rate)** | 60 FPS | Deck.gl 9.0 WebGL GPU-accelerated rendering |
| **Thời gian dọn dẹp trạng thái cũ (Stale Eviction)**| 60 giây timeout / 10 giây TTL | Tự động loại bỏ xe mất tín hiệu và hủy snapshot hết hạn |
