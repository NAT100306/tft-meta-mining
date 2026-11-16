# Hướng dẫn dữ liệu TFT Match Data

Do bộ dữ liệu gốc đầy đủ (50,000 trận ranked) có dung lượng > 200MB vượt quá giới hạn 100MB của GitHub, file `tft_matches.csv` đã được loại trừ khỏi git tracking.

## Cách tạo dữ liệu cục bộ:
Chỉ cần chạy lệnh sau từ thư mục gốc của dự án:
```bash
python src/data_generator.py
```
Lệnh trên sẽ tự động sinh file `data/raw/tft_matches.csv` đầy đủ để chạy toàn bộ các notebook thực nghiệm.
