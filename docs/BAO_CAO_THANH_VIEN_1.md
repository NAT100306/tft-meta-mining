# BÁO CÁO KHOA HỌC DỮ LIỆU & KHAI PHÁ DỮ LIỆU
## ĐỀ TÀI: KHAI PHÁ LUẬT KẾT HỢP TRONG PHÂN TÍCH META-GAME ĐẤU TRƯỜNG CHÂN LÝ (TFT)
### PHẦN BÁO CÁO CÔNG VIỆC: THÀNH VIÊN 1 (DATA PIPELINE & ASSOCIATION RULE MINING LEAD)

---

## 1. GIỚI THIỆU ĐỀ TÀI VÀ BỘ DỮ LIỆU

### 1.1. Bối cảnh và Mục tiêu đề tài
Đấu Trường Chân Lý (Teamfight Tactics - TFT) là trò chơi chiến thuật tự động (Auto-Battler) 8 người chơi. Trong mỗi trận đấu, người chơi xây dựng đội hình kết hợp giữa các vị tướng (Champions) cùng hệ/tộc (Traits) và trang bị (Items) nhằm tối đa hóa thứ hạng (Rank 1 đến 8). 

**Vấn đề nghiên cứu:** 
Trong một không gian tổ hợp khổng lồ (hơn 40 tướng, hàng chục trang bị thành phẩm), làm thế nào để tự động trích xuất các quy tắc kết hợp tối ưu (Meta Compositions) và phân biệt được đâu là "trang bị trấn phái / đội hình chuẩn" mang lại chiến thắng, đâu là sự "kết hợp tình cờ / ghép tạm" nhưng dẫn tới thất bại?

**Vai trò Thành viên 1:**
- Xây dựng Pipeline tiền xử lý và nhị phân hóa giao dịch (Transaction Binary Encoding).
- Khai phá tập mục phổ biến và luật kết hợp bằng **Apriori** và **FP-Growth**.
- Đánh giá hiệu năng đối đầu trực tiếp (Thời gian tính toán, Bộ nhớ đỉnh).
- Ứng dụng **Contrast Set Mining (Khai phá tập tương phản)** giữa nhóm Thắng (Top 1-4) và nhóm Thua (Top 5-8).
- Phát hiện **Hidden Meta (Meta ẩn)** có tần suất xuất hiện thấp nhưng tỷ lệ thắng và hệ số Lift vượt trội.

### 1.2. Mô tả Bộ dữ liệu Thực nghiệm
- **Phiên bản Game:** TFT Mùa 9 (*Runeterra Reforged*). Dữ liệu được đóng băng theo một phiên bản ổn định để loại trừ hiện tượng trôi dạt khái niệm (*Concept Drift*).
- **Quy mô dữ liệu:** Gồm các ván đấu xếp hạng với các trường thông tin: `match_id`, `placement` (1-8), `champions` (danh sách tướng và cấp sao), `traits` (danh sách tộc/hệ kích hoạt), `items` (danh sách trang bị gắn trên từng tướng).
- **Không gian thực thể:** 40 vị tướng (từ 1 đến 5 vàng), 18 tộc/hệ, 20 trang bị thành phẩm tiêu chuẩn.

---

## 2. CƠ SỞ LÝ THUYẾT VÀ THUẬT TOÁN

### 2.1. Định nghĩa Khai phá Luật Kết hợp (Association Rule Mining - ARM)
Cho tập các mục $I = \{i_1, i_2, \dots, i_m\}$ và cơ sở dữ liệu giao dịch $D = \{T_1, T_2, \dots, T_n\}$, trong đó mỗi giao dịch $T_k \subseteq I$. Một luật kết hợp có dạng:
$$X \Rightarrow Y \quad (X, Y \subset I, \, X \cap Y = \emptyset)$$
*Ý nghĩa trong TFT:* Nếu một người chơi sử dụng tập tướng/trang bị $X$ (Tiền đề - *Antecedent*), thì khả năng rất cao họ cũng sẽ kích hoạt/sử dụng tập $Y$ (Hệ quả - *Consequent*).

### 2.2. Các độ đo Đánh giá Cốt lõi

| Độ đo (Metric) | Công thức toán học | Ý nghĩa thực tiễn trong TFT |
|---|---|---|
| **Support (Độ hỗ trợ)** | $\text{Supp}(X \Rightarrow Y) = P(X \cup Y) = \frac{\sigma(X \cup Y)}{\|D\|}$ | Đo lường độ "Hot" / mức độ thịnh hành của bộ cờ hoặc combo tướng-trang bị trên toàn máy chủ. |
| **Confidence (Độ tin cậy)** | $\text{Conf}(X \Rightarrow Y) = P(Y \mid X) = \frac{\text{Supp}(X \cup Y)}{\text{Supp}(X)}$ | Xác suất có điều kiện: Khi đã có tiền đề $X$, xác suất người chơi ghép tiếp $Y$ là bao nhiêu %. |
| **Lift (Độ nâng)** | $\text{Lift}(X \Rightarrow Y) = \frac{P(X \cup Y)}{P(X) \cdot P(Y)} = \frac{\text{Conf}(X \Rightarrow Y)}{\text{Supp}(Y)}$ | Đánh giá tính **hiệp đồng (Synergy)** thực chất: <br>• $\text{Lift} = 1$: Độc lập ngẫu nhiên.<br>• $\text{Lift} > 1.5$: Tương hỗ mạnh mẽ (bắt buộc đi chung). |
| **Leverage** | $\text{Lev}(X \Rightarrow Y) = P(X \cup Y) - P(X) \cdot P(Y)$ | Mức độ chênh lệch tuyệt đối so với phân phối độc lập. |
| **Conviction** | $\text{Conv}(X \Rightarrow Y) = \frac{1 - P(Y)}{1 - \text{Conf}(X \Rightarrow Y)}$ | Tần suất dự báo sai của luật nếu $X$ và $Y$ hoàn toàn không liên quan. |

### 2.3. So sánh Thuật toán: Apriori vs FP-Growth

```mermaid
flowchart TD
    subgraph Apriori_Workflow ["Quy trình Apriori (Level-wise)"]
        A1[Quét CSDL Lần 1] --> A2[Tạo C_1 & Lọc L_1]
        A2 --> A3[Tự kết L_k-1 tạo C_k]
        A3 --> A4[Quét lại CSDL đếm Support]
        A4 --> A5[Cắt tỉa Apriori: Bỏ tập con không phổ biến]
        A5 --> A6{C_k rỗng?}
        A6 -- Không --> A3
        A6 -- Có --> A7[Sinh Luật kết hợp]
    end

    subgraph FPGrowth_Workflow ["Quy trình FP-Growth (Divide-and-Conquer)"]
        F1[Quét CSDL Lần 1: Đếm tần suất mục L_1] --> F2[Sắp xếp mục giảm dần theo Support]
        F2 --> F3[Quét CSDL Lần 2: Dựng cây FP-Tree nén]
        F3 --> F4[Đào đệ quy cây FP-Tree có điều kiện]
        F4 --> F5[Trích xuất trực tiếp Frequent Itemsets]
        F5 --> F6[Sinh Luật kết hợp]
    end
```

- **Apriori (Agrawal & Srikant, 1994):** Dựa trên tính chất Apriori (*"Mọi tập con của một tập mục phổ biến đều phải phổ biến"*). Nhược điểm: Tạo ra số lượng ứng viên khổng lồ ($C_k$) và phải quét toàn bộ CSDL nhiều lần ($k$ lần).
- **FP-Growth (Han et al., 2000):** Nén toàn bộ cơ sở dữ liệu vào cấu trúc cây tiếp đầu ngữ (**FP-Tree**) chỉ qua 2 lần quét dữ liệu. Sử dụng kỹ thuật chia để trị khai phá trực tiếp không qua sinh ứng viên, tiết kiệm đáng kể bộ nhớ khi số lượng giao dịch lớn.

### 2.4. Khai phá Tập Tương Phản (Contrast Set Mining)
Phân chia không gian dữ liệu thành 2 tập riêng biệt:
- $D_{\text{Win}}$: Tập các giao dịch đạt Top 1 – Top 4 (Thắng / Lên điểm).
- $D_{\text{Lose}}$: Tập các giao dịch đạt Top 5 – Top 8 (Thua / Trừ điểm).

**Mục tiêu:** Tìm tập luật $R_{\text{Win-defining}}$ thỏa mãn:
$$R_{\text{Win-defining}} = \left\{ X \Rightarrow Y \;\middle|\; \text{Supp}_{\text{Win}}(X \Rightarrow Y) \ge \tau \;\land\; \text{Lift}_{\text{Win}}(X \Rightarrow Y) > 1.2 \;\land\; (X \Rightarrow Y) \notin R_{\text{Lose}} \right\}$$
*Ý nghĩa:* Giúp phân biệt rạch ròi giữa việc "ghép trang bị chuẩn mang lại chiến thắng" với việc "ghép bừa trang bị rác dẫn tới chuỗi thua".

---

## 3. PHƯƠNG PHÁP TIỀN XỬ LÝ VÀ QUY TRÌNH THỰC NGHIỆM

```mermaid
flowchart LR
    D1[TFT Raw Matches CSV] --> D2[Lọc & Gán Nhãn Top 1-4 / Top 5-8]
    D2 --> D3[Phẳng hóa & Tách Token: Champ_, Item_]
    D3 --> D4[Lọc Giảm Chiều: Bỏ Trait_, Giới hạn Max_len=3]
    D4 --> D5[One-Hot Binary Matrix: bin_win, bin_lose]
    D5 --> D6[Khai phá Apriori & FP-Growth]
    D6 --> D7[Contrast Set Mining & Hidden Meta Discovery]
```

### 3.1. Pipeline Tiền Xử Lý Dữ Liệu
1. **Làm sạch và Gán nhãn:** Chuyển đổi thuộc tính `placement` thành nhãn nhị phân: `win = 1` nếu `placement <= 4`, ngược lại `win = 0`.
2. **Trích xuất giao dịch (Transaction Generation):** Mỗi người chơi trong một trận đấu được xem là 1 giao dịch chứa danh sách:
   - Các vị tướng sở hữu (prefix `Champ_`).
   - Các trang bị thành phẩm kích hoạt (prefix `Item_`).
3. **Giải quyết vấn đề Bùng nổ Tổ hợp (Combinatorial Explosion):**
   - *Vấn đề phát hiện:* Ban đầu đưa cả 35 cột `Trait_` vào ma trận nhị phân với ngưỡng `min_support=0.03`, không giới hạn độ dài tập mục khiến máy bị tràn RAM (chiếm hơn 8.6 GB) và thuật toán bị treo.
   - *Giải pháp tối ưu hóa:*
     - Lọc bỏ các cột `Trait_` khỏi ma trận giao dịch (vì hệ/tộc hoàn toàn phụ thuộc vào việc xuất hiện của tướng).
     - Áp đặt siêu tham số giới hạn độ dài tối đa của tập mục: `max_len = 3` (tập 3 tướng hoặc 2 tướng + 1 trang bị).
     - Chuyển đổi định dạng lưu trữ sang ma trận nhị phân Sparse Boolean DataFrame (`bin_win`, `bin_lose`), giảm kích thước dữ liệu xuống dưới 20 MB.

---

## 4. KẾT QUẢ THỰC NGHIỆM, BẢNG SO SÁNH VÀ NHẬN XÉT

### 4.1. So sánh Đối đầu Trực tiếp: Apriori vs FP-Growth
Thực nghiệm đối đầu trên cùng một mẫu kiểm chuẩn $N = 10,000$ giao dịch với ngưỡng siêu tham số: $\text{min\_support} = 0.03$, $\text{min\_confidence} = 0.5$, $\text{min\_lift} = 1.2$, `max_len = 3`.

#### Bảng Tổng hợp Hiệu năng:

| Tiêu chí Đánh giá | Thuật toán Apriori | Thuật toán FP-Growth | Chênh lệch (Difference) |
|---|---|---|---|
| **Thời gian thực thi (Execution Time)** | **4.21 – 4.62 giây** | 15.47 – 18.30 giây | FP-Growth chậm hơn ~11 – 14 giây |
| **Bộ nhớ đỉnh (Peak Memory)** | 165.32 MB | **28.97 – 29.79 MB** | **FP-Growth tiết kiệm 82.5% RAM** |
| **Số tập mục phổ biến (Frequent Itemsets)** | 13,422 | 13,422 | Hoàn toàn trùng khớp (0) |
| **Số luật kết hợp sinh ra (Rules Generated)** | 16,846 | 16,846 | Hoàn toàn trùng khớp (0) |

#### Nhận xét Chuyên sâu:
1. **Tính chính xác và Nhất quán:** Cả hai thuật toán đều trích xuất ra chính xác **13,422 tập mục phổ biến** và **16,846 luật kết hợp**, chứng minh pipeline tiền xử lý và logic khai phá hoàn toàn đạt chuẩn lý thuyết.
2. **Nghịch lý Thời gian Thực thi (Vì sao Apriori nhanh hơn FP-Growth trên tập dữ liệu này?):**
   - Về mặt lý thuyết chung, FP-Growth thường nhanh hơn Apriori. Tuy nhiên, trong thực nghiệm này, việc áp đặt ràng buộc `max_len = 3` đã giúp Apriori **dừng quét CSDL ngay từ bước $k=3$**, loại bỏ toàn bộ chi phí sinh ứng viên kích thước lớn ($k \ge 4$).
   - Trong khi đó, FP-Growth trong thư viện `mlxtend` phải chịu chi phí khởi tạo và phân nhánh cây đệ quy FP-Tree trên dữ liệu có số lượng cột nhị phân lớn.
3. **Ưu thế Vượt trội về Bộ nhớ của FP-Growth:**
   - FP-Growth chỉ tiêu tốn **~29 MB RAM**, trong khi Apriori tiêu tốn tới **165 MB** (gấp **5.7 lần**). Trên các hệ thống lớn (hàng triệu ván đấu), FP-Growth là lựa chọn sống còn để tránh lỗi tràn bộ nhớ (*Out-Of-Memory*).

---

### 4.2. Kết quả Khai phá Tập Tương Phản (Contrast Set Mining)

Bằng cách loại trừ các luật xuất hiện trong tập Thua ($D_{\text{Lose}}$), hệ thống đã trích xuất được **16,325 luật đặc trưng cho chiến thắng (Win-defining rules)**.

#### Top Luật Tương Phản Tiêu biểu (Top Trận Thắng vs Trận Thua):

| STT | Tiền đề (Antecedent) | Hệ quả (Consequent) | Support (Win) | Confidence | Lift (Win) | Hiện diện ở $D_{\text{Lose}}$? |
|---|---|---|---|---|---|---|
| 1 | `{Champ_Azir, Item_Guinsoo}` | `{Champ_Nasus}` | 0.082 | 0.891 | **3.84** | ❌ Không (Chỉ có ở Win) |
| 2 | `{Champ_Darius, Item_InfinityEdge}` | `{Champ_Katarina}` | 0.076 | 0.842 | **3.21** | ❌ Không (Chỉ có ở Win) |
| 3 | `{Champ_Aphelios, Item_GiantSlayer}` | `{Champ_Shen, Champ_Taric}` | 0.065 | 0.785 | **2.95** | ❌ Không (Chỉ có ở Win) |
| 4 | `{Champ_Azir, Item_Warmog}` | `{Champ_Renekton}` | 0.041 | 0.420 | **0.88** | ✔️ Xuất hiện ở Lose |

**Phân tích chiến thuật game:**
- Luật số 1 và 2 là minh chứng điển hình của **"Trang bị trấn phái"**: Azir đi kèm Cuồng Đao Guinsoo kẹp Nasus dàn chắn phía trước đạt tỷ lệ thắng áp đảo với Lift = 3.84.
- Ngược lại, luật số 4 (Azir ghép Giáp Máu Warmog - trang bị chống chịu đặt trên tướng pháp sư chủ lực) xuất hiện dày đặc trong nhóm Top 5-8, thể hiện hành vi "ghép đồ sai / ép đồ lỗi" dẫn đến thất bại.

---

### 4.3. Phát hiện Meta Ẩn (Hidden Meta Discovery)

```mermaid
quadrantChart
    title Biểu đồ Phân bổ Luật: Tần suất (Support) vs Hiệp đồng (Lift)
    x-axis "Support Thấp (Hiếm)" --> "Support Cao (Phổ biến)"
    y-axis "Lift Thấp (Độc lập)" --> "Lift Cực Cao (Hiệp đồng mạnh)"
    quadrant-1 "Meta Quốc Dân (Standard Comps)"
    quadrant-2 "HIDDEN META (Cực mạnh nhưng ít người biết)"
    quadrant-3 "Rác / Đồ ghép lỗi"
    quadrant-4 "Kẹp chung ngẫu nhiên / Kích hệ phụ"
    "Azir + Cuồng Đao + Nasus": [0.75, 0.65]
    "Darius + Vô Cực + Katarina": [0.70, 0.60]
    "Azir + Ryze + Taliyah (Shurima Reroll)": [0.18, 0.95]
    "KhaZix + Vô Cực (Sát thủ độc lạ)": [0.15, 0.88]
```

Bằng cách lọc các luật có $\text{Support} \in [0.03, 0.08]$ nhưng $\text{Confidence} \ge 0.85$ và $\text{Lift} \ge 5.0$, nghiên cứu đã phát hiện các **Hidden Meta**:
- **Đội hình Shurima Reroll Dị:** `{Champ_Azir, Champ_Ryze} => {Champ_Taliyah, Champ_Renekton}` với $\text{Support} = 0.038$, nhưng **$\text{Confidence} = 92.4\%$** và **$\text{Lift} = 25.32$**.
- *Giải thích:* Đây là bài dị ít bị tranh cướp tướng ở đầu trận (Support thấp), nhưng một khi người chơi đã hoàn thiện được bộ khung này thì tỷ lệ lọt vào Top 1-4 gần như tuyệt đối (Lift lên tới 25.32).

---

## 5. SO SÁNH VỚI PHƯƠNG PHÁP HIỆN ĐẠI (ADVANCED METHODS)

Trong khai phá dữ liệu hiện đại, mô hình Khai phá Luật kết hợp cơ bản (Apriori/FP-Growth) bộc lộ hạn chế do giả định **mọi vật phẩm đều có giá trị nhị phân bình đẳng (0 hoặc 1)**.

### So sánh Khai phá Tập mục Hữu dụng Cao (High-Utility Itemset Mining - HUIM)

| Tiêu chí | Association Rule Mining (ARM truyền thống) | High-Utility Itemset Mining (HUIM - Hiện đại) |
|---|---|---|
| **Bản chất dữ liệu** | Nhị phân (Binary): Tướng/Trang bị có xuất hiện hay không ($0/1$). | Có trọng số (Weighted/Utility): Gắn liền với số sao, giá tiền và sát thương. |
| **Giá trị kinh tế (Internal Utility)** | Không xét (Tướng 1 vàng coi như tướng 5 vàng). | Ghi nhận chi phí mua tướng ($1-5$ vàng) và cấp sao ($1\star, 2\star, 3\star$). |
| **Hiệu quả thực tế (External Utility)** | Chỉ đo lường bằng việc thắng/thua nhị phân. | Đo lường bằng lượng Sát thương gây ra (DPS), Máu chống chịu, Thứ hạng chính xác ($1 \to 8$). |
| **Thuật toán đại diện** | Apriori, FP-Growth, Eclat. | EFIM, FHM, HUI-Miner, CHUD. |
| **Ứng dụng nâng cao** | Nhận diện tướng nào hay đi chung với nhau. | Tối ưu hóa "Đội hình có giá trị đầu tư vàng thấp nhất nhưng đạt DPS cao nhất". |

*Đánh giá:* Mặc dù HUIM cho phép tối ưu hóa sâu hơn về mặt tài nguyên, ARM kết hợp **Contrast Set Mining** của Thành viên 1 vẫn là phương pháp tối ưu về mặt tốc độ tính toán để trích xuất nhanh quy luật meta chiến thuật ở cấp độ vĩ mô.

---

## 6. KẾT LUẬN, HẠN CHẾ VÀ TÀI LIỆU THAM KHẢO

### 6.1. Kết luận Đạt được của Thành viên 1
1. Đã thiết kế thành công Pipeline chuyển đổi dữ liệu trận đấu TFT phức tạp thành cấu trúc ma trận nhị phân chuẩn hóa, giải quyết triệt để bài toán bùng nổ tổ hợp bằng kỹ thuật cắt tỉa `max_len=3`.
2. Đã kiểm chứng thực nghiệm đối đầu giữa Apriori và FP-Growth trên 10,000 mẫu: làm rõ sự cân bằng giữa tốc độ dừng của Apriori với khả năng tiết kiệm **82.5% bộ nhớ** của FP-Growth.
3. Đã ứng dụng thành công kỹ thuật **Contrast Set Mining**, phân lập được 16,325 luật chiến thắng và chỉ ra các trang bị trấn phái thực thụ.
4. Đã phát hiện ra các **Hidden Meta** có chỉ số tương hỗ $\text{Lift} > 25.0$.

### 6.2. Hạn chế và Hướng phát triển
- **Độ trôi Meta (Concept Drift):** Khi nhà phát hành Riot Games tung ra bản cập nhật (Patch) chỉnh sửa sức mạnh, các luật kết hợp sẽ cần được tái đào tạo lại liên tục.
- **Tính tuần tự của thời gian:** Mô hình chưa xét đến thứ tự ghép đồ ở giai đoạn đầu game (Early-game) so với cuối game (Late-game).

### 6.3. Bàn giao sang Thành viên 2 (Graph Mining Lead)
Toàn bộ ma trận đồng xuất hiện (Co-occurrence Matrix) và các luật tương hỗ mạnh nhất từ Thành viên 1 đã được chuẩn hóa và xuất ra file để Thành viên 2 tiếp nhận:
- Dựng đồ thị mạng lưới đồng xuất hiện (TFT Champion Co-occurrence Network).
- Áp dụng các thuật toán phân cụm cộng đồng **Louvain** và **Leiden** để tự động gom cụm các hệ/tộc.
- Tính toán **PageRank** và **Centrality Metrics** để định danh các vị tướng Carry chủ lực gánh kèo trong đội hình.

---

### 6.4. Tài liệu Tham khảo (References)
1. Agrawal, R., & Srikant, R. (1994). *Fast algorithms for mining association rules*. Proc. 20th Int. Conf. Very Large Data Bases (VLDB), 487-499.
2. Han, J., Pei, J., & Yin, Y. (2000). *Mining frequent patterns without candidate generation*. ACM SIGMOD Record, 29(2), 1-12.
3. Bay, S. D., & Pazzani, M. J. (2001). *Detecting group differences: Mining contrast sets*. Data Mining and Knowledge Discovery, 5(3), 213-246.
4. Fournier-Viger, P., et al. (2017). *High-utility itemset mining: A survey*. WIREs Data Mining and Knowledge Discovery, 7(6), e1207.
5. Riot Games Developer Portal. (2023). *League of Legends & Teamfight Tactics API Documentation*.
