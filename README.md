# 🎮 Khai Phá Luật Kết Hợp & Biểu Diễn Đồ Thị trong Phân Tích Meta-Game TFT

Đồ án môn học: **Khai phá Dữ liệu (Data Mining)**  
Chủ đề: Khai phá các tổ hợp sức mạnh ẩn (Hidden Meta), quy luật cộng hưởng Tướng - Trang bị và Cụm Đội hình trong Đấu Trường Chân Lý (Teamfight Tactics - TFT).

---

## 👥 Phân Công Nhóm 2 Thành Viên

| Thành viên | Trách nhiệm chính | Trạng thái hiện tại |
|---|---|---|
| **Thành viên 1** (`Nat100306`) | **Lead Dữ liệu & Association Rule Mining**: Thu thập dữ liệu, Tiền xử lý, Gán nhãn Win/Lose, EDA Tướng/Item, Thực nghiệm **Apriori** & **FP-Growth**, Contrast Set Mining, lọc Lift > 1.5 tìm Hidden Meta. | ✅ **Đã hoàn thành 100% & Bàn giao** |
| **Thành viên 2** | **Lead Graph Mining & Tổng hợp**: Xây dựng đồ thị đồng xuất hiện, Phân cụm đội hình (**Louvain** & **Leiden**), Xếp hạng nhân vật hạt nhân (**PageRank**), Kiểm chứng chéo & Báo cáo tổng hợp. | ⏳ **Đang triển khai** (Xem chi tiết tại [GUIDE_FOR_MEMBER_2.md](GUIDE_FOR_MEMBER_2.md)) |

---

## 📁 Cấu Trúc Dự Án

```
tft-meta-mining/
├── README.md                          # Tài liệu tổng quan đồ án
├── GUIDE_FOR_MEMBER_2.md              # Lộ trình & Hướng dẫn chi tiết cho Thành viên 2
├── requirements.txt                   # Danh sách thư viện Python cần thiết
│
├── data/
│   ├── raw/
│   │   └── tft_matches.csv            # Bộ dữ liệu 5,000 trận đấu mẫu đã tạo sẵn
│   └── processed/                     # Nơi lưu ma trận nhị phân & ma trận đồng xuất hiện
│
├── src/                               # Các module mã nguồn cốt lõi
│   ├── __init__.py                    # Package init (export các class chính)
│   ├── data_generator.py              # [TV1] Tạo dữ liệu trận đấu TFT thực tế (Meta & Hidden Meta)
│   ├── preprocessor.py                # [TV1] Tiền xử lý, gán nhãn Win/Lose, tạo transactions
│   ├── arm_miner.py                   # [TV1] Thuật toán Apriori, FP-Growth, Contrast Set, Hidden Meta
│   └── graph_miner.py                 # [TV2] Module đồ thị (NetworkX, Louvain, Leiden, PageRank)
│
└── notebooks/                         # Chuỗi Notebook thực nghiệm
    ├── 01_data_collection.ipynb       # [TV1] Thu thập / Sinh dữ liệu trận đấu
    ├── 02_preprocessing.ipynb         # [TV1] Tiền xử lý, làm sạch & mã hóa nhị phân
    ├── 03_eda.ipynb                   # [TV1] Khám phá phân phối Pick-rate & Win-rate
    ├── 04_apriori.ipynb               # [TV1] Chạy Apriori, lọc luật có Lift > 1.5
    ├── 05_fpgrowth.ipynb              # [TV1] Chạy FP-Growth, so sánh hiệu năng, tìm Hidden Meta
    ├── 06_graph_construction.ipynb    # [TV2] Xây dựng đồ thị liên kết tướng (NetworkX)
    ├── 07_louvain_leiden.ipynb        # [TV2] Phân cụm đội hình: Louvain vs Leiden (Modularity Q)
    ├── 08_pagerank.ipynb              # [TV2] PageRank tìm Core Carry vs Flex Support
    └── 09_comparison.ipynb            # [Chung] Kiểm chứng chéo ARM vs Graph & Kết luận
```

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy

### 1. Cài đặt môi trường
Khuyến nghị sử dụng Python 3.9+:
```bash
pip install -r requirements.txt
```

### 2. Thứ tự chạy thực nghiệm cho Thành viên 1:
1. `notebooks/01_data_collection.ipynb`: Nạp và kiểm tra dữ liệu thô.
2. `notebooks/02_preprocessing.ipynb`: Tiền xử lý dữ liệu, xuất file nhị phân `bin_win.pkl`, `bin_lose.pkl` và ma trận `cooc_winrate.pkl`.
3. `notebooks/04_apriori.ipynb`: Khai phá luật kết hợp bằng Apriori.
4. `notebooks/05_fpgrowth.ipynb`: Khai phá bằng FP-Growth, đo thời gian/bộ nhớ và tìm Hidden Meta.

### 3. Hướng dẫn tiếp tục cho Thành viên 2:
Vui lòng đọc file [GUIDE_FOR_MEMBER_2.md](GUIDE_FOR_MEMBER_2.md) để bắt đầu thực hiện các notebook `06`, `07`, `08`, `09`.
