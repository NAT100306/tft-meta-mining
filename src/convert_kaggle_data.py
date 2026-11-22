"""
convert_kaggle_data.py - Chuyển đổi dữ liệu thực tế từ Kaggle (Riot API KR Server)
sang định dạng chuẩn của dự án TFT Meta Mining.
"""

import os
import glob
import json
import ast
import pandas as pd
import numpy as np

def convert_kaggle_dataset():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(root_dir, "data", "kaggle_raw")
    output_dir = os.path.join(root_dir, "data", "raw")
    os.makedirs(output_dir, exist_ok=True)
    
    target_csv = os.path.join(output_dir, "tft_matches.csv")
    backup_csv = os.path.join(output_dir, "tft_matches_synthetic_backup.csv")
    
    # Backup file cũ nếu chưa backup
    if os.path.exists(target_csv) and not os.path.exists(backup_csv):
        print(f"📦 Đang sao lưu dữ liệu synthetic cũ sang {backup_csv}...")
        os.rename(target_csv, backup_csv)
        print("✅ Đã sao lưu thành công!")
    
    files = sorted(glob.glob(os.path.join(raw_dir, "*.csv")))
    print(f"🔍 Tìm thấy {len(files)} files dữ liệu thực tế từ Kaggle:")
    for f in files:
        print(f"  - {os.path.basename(f)}")
        
    converted_dfs = []
    
    for f in files:
        tier_name = os.path.basename(f).replace("TFT_", "").replace("_MatchData.csv", "")
        print(f"\n⏳ Đang xử lý {os.path.basename(f)} (Rank: {tier_name})...", flush=True)
        
        # Đọc dữ liệu theo chunk để tối ưu RAM
        chunk_size = 20000
        for chunk in pd.read_csv(f, chunksize=chunk_size):
            records = []
            for _, row in chunk.iterrows():
                try:
                    c_str = row['champion']
                    t_str = row['combination']
                    
                    champ_dict = ast.literal_eval(c_str) if isinstance(c_str, str) else {}
                    traits_dict = ast.literal_eval(t_str) if isinstance(t_str, str) else {}
                    
                    champions = list(champ_dict.keys())
                    champion_stars = {k: v.get('star', 1) for k, v in champ_dict.items() if isinstance(v, dict)}
                    items = {k: v.get('items', []) for k, v in champ_dict.items() if isinstance(v, dict) and v.get('items')}
                    total_items = sum(len(v) for v in items.values())
                    
                    records.append({
                        'match_id': row['gameId'],
                        'player_id': f"{row['gameId']}_{row['Ranked']}",
                        'placement': int(row['Ranked']),
                        'tier': tier_name,
                        'level': int(row['level']),
                        'rounds_survived': int(row['lastRound']),
                        'game_duration_s': float(row['gameDuration']),
                        'champions': json.dumps(champions),
                        'champion_stars': json.dumps(champion_stars),
                        'items': json.dumps(items),
                        'active_traits': json.dumps(traits_dict),
                        'num_champions': len(champions),
                        'num_items': total_items,
                        'num_active_traits': len(traits_dict)
                    })
                except Exception as e:
                    continue
            
            sub_df = pd.DataFrame(records)
            converted_dfs.append(sub_df)
            print(f"  -> Đã chuyển đổi thêm {len(sub_df):,} bản ghi...", flush=True)
            
    print("\n🔗 Đang ghép toàn bộ dữ liệu...")
    full_df = pd.concat(converted_dfs, ignore_index=True)
    print(f"✅ Tổng cộng bản ghi thực tế: {len(full_df):,}")
    print(f"🎮 Số trận đấu độc nhất: {full_df['match_id'].nunique():,}")
    
    # Lưu file CSV mới
    print(f"💾 Đang lưu vào {target_csv}...")
    full_df.to_csv(target_csv, index=False)
    size_mb = os.path.getsize(target_csv) / (1024 * 1024)
    print(f"🎉 Hoàn tất! File tft_matches.csv mới có kích thước: {size_mb:.2f} MB")

if __name__ == "__main__":
    convert_kaggle_dataset()

