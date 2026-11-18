# ĐẶC TẢ KỸ THUẬT CẤP ĐỘ STUDIO (v3.0)
## KIẾN TRÚC ĐỒ THỊ TỰ PHẢN BIỆN ĐA AGENT — THE AUTONOMOUS ADVERSARIAL BRAIN

---

## 1. TRIẾT LÝ THIẾT KẾ v3.0: TẠI SAO PHẢI XÓA BỎ LUỒNG TUYẾN TÍNH (LINEAR PIPELINE)?

Trong các hệ thống tự động hóa thế hệ cũ (v1.0 – v2.0), quy trình diễn ra theo một đường thẳng cố định: **Cào kịch bản $\to$ Tìm kiếm từ khóa $\to$ Tóm tắt $\to$ Viết kịch bản**. Cách tiếp cận này mắc phải 3 giới hạn chí mạng:
1. **Không có khả năng tự nghi ngờ (Zero Self-Doubt):** Nếu công cụ tìm kiếm trả về các bài báo SEO bề nổi hoặc thông tin sai lệch, Agent viết kịch bản ở cuối nguồn vẫn ngoan ngoãn dùng dữ liệu rác đó để viết thành kịch bản.
2. **Mù ngữ cảnh phát sinh (Blindness to Emergent Clues):** Trong quá trình điều tra một vụ án hay sự kiện lịch sử, manh mối quan trọng nhất thường chỉ xuất hiện ở trang thứ 15 của một biên bản PDF (ví dụ: một mã hiệu tài khoản lạ hoặc tên một kỹ sư bị sa thải). Luồng cố định không biết tự rẽ nhánh để đào sâu vào manh mối mới phát sinh này.
3. **Đồng thuận giả tạo (Sycophancy & Mode Collapse):** Khi một LLM vừa tìm kiếm vừa tự đánh giá kết quả của chính nó, nó luôn có xu hướng tự khen dữ liệu đã đủ tốt để kết thúc sớm.

### Giải pháp v3.0: Mô hình Phiên tòa Tranh tụng & Đồ thị Có Chu trình (Adversarial Cyclic Graph)
Thay vì một dây chuyền lắp ráp cứng nhắc, **Giai đoạn 1 (The Brain v3.0)** được thiết kế như một **Phòng điều tra báo chí kết hợp Phiên tòa tranh tụng**:
* **Chia tách Quyền lực (Separation of Powers):** Agent lập giả thuyết, Agent đi săn bằng chứng và Agent kiểm duyệt hoàn toàn độc lập và có mục tiêu đối kháng nhau.
* **Cơ chế Công tố viên Đỏ (Red-Team Prosecution):** Một Agent chuyên biệt được lập trình với nhân cách hoài nghi cực đoan, có nhiệm vụ duy nhất là tìm lỗ hổng logic, chỉ ra sự thiếu hụt nguồn sơ cấp (Primary Sources) và bác bỏ hồ sơ.
* **Điều hướng Động (Dynamic Routing & Map-Reduce):** Các Agent tự quyết định bước tiếp theo sẽ đi đâu dựa trên chất lượng bằng chứng thực tế, tự động tách luồng chạy song song khi phát hiện nhiều đầu mối mới.

---

## 2. GIẢI PHẪU CHI TIẾT TỪNG BƯỚC: CÔNG NGHỆ, LÝ DO LỰA CHỌN & MODEL CHỊU TRÁCH NHIỆM

### 2.1. Bảng Ma trận Công nghệ & Phân công Model Tổng thể

| Tầng | Bước xử lý / Node | Công nghệ & Thư viện | Model AI Chịu Trách nhiệm | Lý do Lựa chọn Kỹ thuật (Why This Tech & Model?) |
| :--- | :--- | :--- | :--- | :--- |
| **Tầng 0** | **Điều phối & Bộ nhớ** | `LangGraph` (`Command`, `Send` API) + `PostgresSaver` + `Qdrant` | Code Python thuần | Hỗ trợ đồ thị có chu trình (Cyclic Graph), rẽ nhánh động song song và lưu trạng thái chống mất dữ liệu. |
| **Tầng 1** | **Node 1A: Bóc tách Đa phương thức** | `yt-dlp` + `FFmpeg` + `Groq LPU API` | `Whisper Large-v3 Turbo` | Bóc băng 20 phút audio trong $\sim 3\text{ giây}$, trả về `word-level timestamps` để đo tốc độ nói (WPM) và nhịp cắt cảnh. |
| **Tầng 1** | **Node 1B: Giải phẫu Đối thủ** | `Google GenAI SDK` + `YouTube Data API v3` | `Gemini 2.5 Pro` | Cửa sổ ngữ cảnh $2\text{M tokens}$ nuốt trọn transcript dài cùng $100$ bình luận khán giả để tìm điểm mù (Blindspots). |
| **Tầng 2** | **Node 2: Kiến trúc sư Giả thuyết** | `OpenAI SDK` / `DeepSeek API` | `OpenAI o3` (hoặc `DeepSeek-R1`) | Mô hình suy luận chuỗi sâu (Reasoning Model) chống lối mòn tư duy, tìm ra 3 góc nhìn lật ngược (Counter-Hypotheses). |
| **Tầng 2** | **Node 3: Thợ săn Bằng chứng Đa tầng** | `Exa.ai` + `Tavily API` + `Firecrawl` (hoặc `Jina Reader`) | `Gemini 2.5 Flash` | `Exa` tìm kiếm ngữ nghĩa file PDF/học thuật; `Firecrawl` cào toàn văn trang web ra Markdown sạch; `Flash` trích xuất tốc độ cao. |
| **Tầng 2** | **Node 4: Công tố viên Phản biện** | `LangGraph Conditional Command` + `Instructor` | `OpenAI o3-mini` (`reasoning_effort="high"`) | Tư duy phản biện sắc bén, chuyên bắt lỗi ngụy biện, thiếu nguồn sơ cấp, mâu thuẫn thời gian và thiếu chi tiết vật lý. |
| **Tầng 2** | **Node 5: Thẩm phán & Chống lặp** | `NumPy` + `text-embedding-3-small` + `Google GenAI` | `Gemini 2.5 Pro` | Tính điểm mật độ dữ kiện ($FSS \ge 0.85$) và đo độ tương đồng Cosine để cắt vòng lặp nếu tranh cãi bị bão hòa. |
| **Tầng 3** | **Node 6: Đạo diễn Kịch bản Đa hồi** | `Anthropic SDK` + `Pydantic v2` | `Claude 3.5 Sonnet` (hoặc `3.7 Sonnet`) | Khả năng viết văn phong điện ảnh (Cinematic Storytelling) tốt nhất hiện nay, giàu nhịp điệu, tự nhiên, không mùi AI. |
| **Tầng 3** | **Node 7: Bác sĩ Kịch bản & Kiểm định** | `Pydantic @model_validator` + `RegEx` | `OpenAI o3-mini` + Code Python | Tự động sửa lỗi chữ số cho TTS, xóa từ sáo rỗng, khớp `trigger_word` âm thanh và khóa tỷ lệ ngân sách Hybrid Motion. |

---

### 2.2. Giải trình Chuyên sâu Lý do Chọn Công nghệ ở Từng Mắt xích

#### A. Tại sao dùng `LangGraph` (với `Command` & `Send` API) thay vì `CrewAI` hay `AutoGen`?
* `CrewAI` thiết kế theo luồng tuần tự hoặc phân cấp đơn giản, rất khó kiểm soát khi bạn muốn Node 4 (Công tố viên) lúc thì trả hồ sơ về Node 2 (bắt đổi giả thuyết khác vì giả thuyết hiện tại sai), lúc thì trả về Node 3 (giữ nguyên giả thuyết nhưng bắt đi tìm thêm kích thước con ốc vít).
* Với `Command(goto=..., update=...)` của `LangGraph`, bản thân Agent phản biện có quyền điều khiển luồng chạy tiếp theo dựa trên kết quả suy luận. Đồng thời, `Send` API cho phép khi Node 4 phát hiện 4 lỗ hổng thông tin khác nhau, nó tự động khởi tạo 4 tiến trình `MultiToolHunter` chạy song song cùng lúc để lấp đầy cả 4 lỗ hổng chỉ trong 10 giây.

#### B. Tại sao phải kết hợp bộ 3 `Exa.ai` + `Tavily` + `Firecrawl` ở Tầng Nghiên cứu?
* **Vấn đề của Google Search / DuckDuckGo thông thường:** Tối ưu hóa cho quảng cáo và bài viết SEO bề nổi (Top 10 kết quả đầu tiên thường chép lại của nhau từ Wikipedia).
* **Sự khác biệt của `Exa.ai` (Neural Search Engine):** Sử dụng mô hình ngôn ngữ để lập chỉ mục web theo ý nghĩa. Bạn có thể truyền câu lệnh như: *"Here is an unredacted forensic investigation report and technical post-mortem log:"*, Exa sẽ lôi ra các file PDF của cơ quan điều tra, bài nghiên cứu trên ArXiv, hoặc tài liệu lưu trữ lịch sử mà Google ẩn ở trang 20.
* **Sự khác biệt của `Firecrawl` / `Jina Reader`:** Các API tìm kiếm chỉ trả về đoạn trích ngắn $200\text{ từ}$. Khi thấy một đường link chứa nhật ký gốc hoặc biên bản tòa án, Agent gọi `Firecrawl` để cào toàn bộ nội dung trang web/PDF đó thành văn bản Markdown tinh khiết ($5.000 \text{ đến } 20.000\text{ từ}$), giúp lấy được các chi tiết nhỏ nhất như nhiệt độ phòng, nhãn hiệu máy móc hay câu nói nguyên văn.

#### C. Tại sao phân tách `OpenAI o3 / DeepSeek-R1` cho Phản biện và `Claude 3.5 Sonnet` cho Biên kịch?
* Các mô hình suy luận (`o3`, `o3-mini`, `DeepSeek-R1`) cực kỳ xuất sắc trong việc tìm lỗi logic, đối chiếu mốc thời gian và lập kế hoạch điều tra, nhưng văn phong của chúng lại khô khan như báo cáo kỹ thuật.
* Ngược lại, `Claude 3.5 Sonnet` có "nhạc cảm" ngôn từ vượt trội: biết cách ngắt câu ngắn tạo kịch tính, biết chọn tính từ gợi hình ảnh thị giác và ánh sáng điện ảnh. Việc ghép `o3-mini` làm "Người kiểm duyệt" và `Claude 3.5 Sonnet` làm "Người sáng tạo" tạo ra cặp đôi hoàn hảo.

---

## 3. SƠ ĐỒ ĐỒ THỊ TRẠNG THÁI TỰ PHẢN BIỆN (LANGGRAPH CYCLIC TOPOLOGY)

```
                        [INPUT: YouTube Rival URL]
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │ NODE 1: MULTIMODAL RIVAL AUTOPSY                        │
       │  • Tools: yt-dlp + Groq Whisper v3 Turbo + FFmpeg       │
       │  • Model: Gemini 2.5 Pro (2M Context)                   │
       │  • Output: Rival Thesis, WPM Curve, 100 Comments Gaps   │
       └────────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │ NODE 2: COUNTER-HYPOTHESIS ARCHITECT                    │◄─────────┐
       │  • Model: OpenAI o3 / DeepSeek-R1 (Deep Reasoning)      │          │
       │  • Action: Đề xuất 3 Giả thuyết Lật kèo (H1, H2, H3)   │          │
       └────────────────────────────┬────────────────────────────┘          │
                                    │                                       │
              (LangGraph Send API: Phân luồng song song)                    │
                 ┌──────────────────┼──────────────────┐                    │
                 ▼                  ▼                  ▼                    │
       ┌─────────────────┐┌─────────────────┐┌─────────────────┐            │
       │ NODE 3 (Worker1)││ NODE 3 (Worker2)││ NODE 3 (Worker3)│◄───┐       │
       │ FORENSIC HUNTER ││ FORENSIC HUNTER ││ FORENSIC HUNTER │    │       │
       │ • Exa + Tavily  ││ • Exa + Tavily  ││ • Exa + Tavily  │    │       │
       │ • Firecrawl MD  ││ • Firecrawl MD  ││ • Firecrawl MD  │    │       │
       │ • Gemini Flash  ││ • Gemini Flash  ││ • Gemini Flash  │    │       │
       └────────┬────────┘└────────┬────────┘└────────┬────────┘    │       │
                └──────────────────┼──────────────────┘             │       │
                                   ▼                                │       │
       ┌─────────────────────────────────────────────────────────┐  │       │
       │ NODE 4: RED-TEAM PROSECUTOR (Công tố viên Phản biện)    │  │       │
       │  • Model: OpenAI o3-mini (reasoning_effort="high")      │  │       │
       │  • Kiểm tra 4 tiêu chí:                                 │  │       │
       │    1. Có nguồn sơ cấp (Primary Source) chưa?            │  │       │
       │    2. Có mâu thuẫn mốc thời gian / vật lý không?        │  │       │
       │    3. Có chi tiết vật thể để vẽ ảnh (Artifacts) chưa?   │  │       │
       │    4. Có bị trùng lặp với kênh đối thủ không?           │  │       │
       └─────────────┬───────────────────────────┬───────────────┘  │       │
                     │                           │                  │       │
         [Bằng chứng mỏng:           [Giả thuyết sai hoàn toàn:     │       │
          Sinh truy vấn đào sâu]      Bác bỏ, yêu cầu lập lại]      │       │
                     └───────────────────────────┼──────────────────┘       │
                                                 └──────────────────────────┘
                     │ (Khi vượt qua chất vấn hoặc chạm ngưỡng Cosine)
                     ▼
       ┌─────────────────────────────────────────────────────────┐
       │ NODE 5: INVESTIGATIVE JUDGE & DOSSIER LOCK              │
       │  • Model: Gemini 2.5 Pro + Python Math Scorer           │
       │  • Tính điểm FSS >= 0.85 & Đóng dấu ForensicDossier     │
       └────────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │ NODE 6: ACT-BY-ACT SHOWRUNNER & STYLE BIBLE             │◄─────────┐
       │  • Model: Claude 3.5 Sonnet                             │          │
       │  • Sinh dàn ý 5 Hồi + Chạy vòng lặp viết từng Hồi       │          │
       │  • Phân bổ Hybrid Motion (Hồi 1: 100% Video AI)         │          │
       └────────────────────────────┬────────────────────────────┘          │
                                    │                                       │
                                    ▼                                       │
       ┌─────────────────────────────────────────────────────────┐          │
       │ NODE 7: SCRIPT DOCTOR & SELF-HEALING VALIDATOR          │──────────┘
       │  • Tech: Pydantic v2 @model_validator + o3-mini         │ [Bắt lỗi &
       │  • Quét từ cấm AI, cấm chữ số TTS, khớp Trigger Word    │  Ép sửa lại
       └────────────────────────────┬────────────────────────────┘  từng cảnh]
                                    │ (100% Validated)
                                    ▼
                 [OUTPUT: Master_Production_Script_v3.json]
```

---

## 4. CÔNG THỨC TOÁN HỌC ĐIỀU KHIỂN VÒNG LẶP & KIỂM ĐỊNH CHẤT LƯỢNG

Để hệ thống tự chủ không bị rơi vào vòng lặp vô tận (Infinite Loop) tốn tiền API hoặc dừng lại quá sớm khi dữ liệu còn nông, Node 4 và Node 5 được kiểm soát bởi 3 phương trình toán học sau:

### 4.1. Điểm Đặc tả Pháp y ($FSS - \text{Forensic Specificity Score}$)
Hồ sơ bằng chứng thu thập được tại vòng lặp thứ $t$ (ký hiệu là $D_t$) được chấm điểm tự động:

$$
FSS(D_t) = 0.25 \cdot \min\left(\frac{C_{\text{primary}}}{5}, 1\right) + 0.25 \cdot \min\left(\frac{C_{\text{timestamps}}}{12}, 1\right) + 0.25 \cdot \min\left(\frac{C_{\text{metrics}}}{15}, 1\right) + 0.25 \cdot \min\left(\frac{C_{\text{artifacts}}}{10}, 1\right) - P_{\text{contradiction}}
$$

Trong đó:
* $C_{\text{primary}}$: Số lượng nguồn sơ cấp xác thực (biên bản tòa án, báo cáo kỹ thuật, nhật ký, bằng sáng chế).
* $C_{\text{timestamps}}$: Số lượng mốc thời gian có định dạng giờ/phút hoặc ngày tháng chính xác.
* $C_{\text{metrics}}$: Số lượng thông số định lượng vật lý/tài chính cụ thể.
* $C_{\text{artifacts}}$: Số lượng hiện vật vật lý có mô tả chất liệu/nhãn hiệu (dùng làm đầu vào cho Flux sinh ảnh).
* $P_{\text{contradiction}} \in [0, 0.5]$: Điểm phạt từ Công tố viên nếu phát hiện mâu thuẫn chưa được giải thích trong hồ sơ.
* **Điều kiện mở khóa sang Phòng Biên kịch:** $FSS(D_t) \ge 0.85$.

### 4.2. Thuật toán Phá Kẹt Vòng lặp bằng Độ tương đồng Ngữ nghĩa ($\text{Information Gain Breaker}$)
Nếu các công cụ tìm kiếm không thể tìm thêm thông tin mới trên Internet (vụ án thực sự bị mất dấu vết), việc bắt Agent tìm kiếm mãi sẽ gây lãng phí. Hệ thống dùng model embedding (`text-embedding-3-small`) chuyển đổi hồ sơ vòng trước $E(D_{t-1})$ và hồ sơ vòng hiện tại $E(D_t)$ thành vector để tính **Độ lợi Thông tin ($\Delta I_t$)**:

$$
\Delta I_t = 1 - \frac{E(D_{t-1}) \cdot E(D_t)}{\|E(D_{t-1})\| \|E(D_t)\|}
$$

* Nếu $\Delta I_t < 0.03$ (tức là vòng tìm kiếm mới chỉ mang về dưới $3\%$ thông tin mới so với vòng trước) hoặc số vòng tranh biện $t = 4$, Thẩm phán (Node 5) sẽ tự động ngắt vòng lặp, giữ lại giả thuyết có điểm $FSS$ cao nhất và chuyển trạng thái các câu hỏi chưa có lời giải thành **"Bí ẩn lịch sử mở" (Unresolved Mystery Hook)** trong kịch bản.

### 4.3. Phương trình Tối ưu Ngân sách Hybrid Motion ($C_{\text{budget}}$)
Gọi $N$ là tổng số cảnh của video (thường từ $180 \text{ đến } 240$ cảnh). Gọi $I_{\text{video}}(i) \in \{0, 1\}$ là biến chỉ thị cảnh thứ $i$ có sử dụng Video AI (`AI_VIDEO_HIGH_COST`) hay không, và $t_i$ là thời điểm bắt đầu của cảnh $i$ (tính bằng giây):

$$
\begin{cases}
I_{\text{video}}(i) = 1, & \forall i \text{ thỏa mãn } t_i \le 60\text{s} \quad (\text{100\% Hook 1 phút đầu là Video AI}) \\
\frac{\sum_{t_i > 60} I_{\text{video}}(i) \cdot \Delta d_i}{\sum_{t_i > 60} \Delta d_i} \le 0.20, & (\text{Từ phút thứ 2 trở đi, thời lượng Video AI } \le 20\%)
\end{cases}
$$

---

## 5. MÃ NGUỒN CỐT LÕI 1: HỆ THỐNG SCHEMAS TRANH TỤNG & KIỂM ĐỊNH (`core/schemas.py`)

File này định nghĩa toàn bộ cấu trúc dữ liệu cho cả **Hội đồng Nghiên cứu Tự Phản biện** lẫn **Phòng Biên kịch Đa hồi**.

```python
import re
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal

# Từ vựng sáo rỗng bị cấm tuyệt đối trong kịch bản xuất xưởng
BANNED_AI_PHRASES = [
    "delve into", "testament to", "in the realm of", "little did they know",
    "a chilling reminder", "tapestry of", "buckle up", "without further ado",
    "in today's video", "shocked the world", "changed everything forever",
    "it is important to note", "fast forward to", "beacon of hope", "double-edged sword"
]

# =====================================================================
# PHẦN A: SCHEMAS CHO HỘI ĐỒNG NGHIÊN CỨU TỰ PHẢN BIỆN (NODES 1 -> 5)
# =====================================================================
class RivalAutopsyReport(BaseModel):
    video_title: str
    hook_60s_wpm: float = Field(description="Tốc độ đọc trung bình (từ/phút) trong 60 giây đầu của đối thủ")
    body_wpm: float = Field(description="Tốc độ đọc trung bình phần thân video của đối thủ")
    cuts_per_minute_hook: float = Field(description="Số lần chuyển cảnh/phút trong 60 giây đầu")
    rival_core_thesis: str = Field(description="Luận điểm chính mà kênh đối thủ đang cố thuyết phục người xem")
    superficial_claims: List[str] = Field(
        min_length=3,
        description="Các tuyên bố hời hợt, thiếu bằng chứng hoặc giải thích qua loa trong video đối thủ"
    )
    audience_unanswered_questions: List[str] = Field(
        min_length=3,
        description="Những thắc mắc, bắt lỗi hoặc tranh cãi gay gắt nhất trích từ 100 bình luận của khán giả"
    )

class CounterHypothesis(BaseModel):
    hypothesis_id: str = Field(description="Mã giả thuyết, VD: HYP_01")
    pivot_angle_title: str = Field(description="Tên góc nhìn lật ngược")
    core_argument: str = Field(description="Luận điểm phản biện trực diện vào điểm yếu của đối thủ")
    required_smoking_gun: str = Field(description="Bằng chứng cốt lõi cần phải tìm ra để chứng minh giả thuyết này đúng")
    initial_search_vectors: List[str] = Field(min_length=3, description="Các truy vấn Exa/Tavily chuyên sâu để khởi động săn tìm")

class HypothesisBatch(BaseModel):
    hypotheses: List[CounterHypothesis] = Field(min_length=3, max_length=3)

class ForensicEvidenceItem(BaseModel):
    evidence_id: str
    hypothesis_id: str
    source_tier: Literal["PRIMARY_FORENSIC_OR_COURT", "ACADEMIC_OR_TECHNICAL", "INVESTIGATIVE_JOURNALISM", "SECONDARY_SUMMARY"]
    exact_timestamp_or_date: str = Field(description="Mốc thời gian cụ thể đến giờ/phút hoặc ngày tháng")
    physical_location: str = Field(description="Địa điểm vật lý cụ thể, phòng, tầng, tọa độ")
    factual_claim: str = Field(description="Dữ kiện chi tiết chứa tên riêng và hành động cụ thể")
    quantitative_metric: str = Field(description="Con số đo lường, tiền tệ, nhiệt độ, mã hiệu kỹ thuật")
    verbatim_quote: Optional[str] = Field(default=None, description="Trích dẫn nguyên văn từ tài liệu gốc")
    tangible_artifact_desc: str = Field(description="Mô tả hình dáng, nhãn hiệu, màu sắc của vật thể vật lý liên quan")
    source_url: str

class EvidenceHarvestBatch(BaseModel):
    new_evidence: List[ForensicEvidenceItem]

class FlawCritique(BaseModel):
    flaw_type: Literal["LACK_OF_PRIMARY_SOURCE", "TIMELINE_CONTRADICTION", "TOO_ABSTRACT_FOR_VISUAL", "CLICHE_ALREADY_KNOWN", "UNVERIFIED_NUMBER"]
    critique_detail: str = Field(description="Lời buộc tội sắc bén của Công tố viên chỉ rõ chỗ yếu trong bằng chứng hiện tại")
    targeted_search_directive: str = Field(description="Câu lệnh tìm kiếm cực ngách (có toán tử filetype:pdf, site:, v.v.) bắt Hunter đi đào lại")
    search_engine_to_use: Literal["EXA_NEURAL", "TAVILY_DEEP", "FIRECRAWL_FULLTEXT"]

class ProsecutorIndictment(BaseModel):
    verdict: Literal["REJECT_AND_HUNT_DEEPER", "DISCARD_HYPOTHESIS_AND_RETHINK", "APPROVE_FOR_SCRIPTROOM"]
    winning_hypothesis_id: str
    forensic_specificity_score_estimate: float = Field(ge=0.0, le=1.0)
    identified_flaws: List[FlawCritique] = Field(description="Danh sách các lỗ hổng bắt buộc phải lấp nếu verdict không phải APPROVE")
    prosecutor_reasoning: str

# =====================================================================
# PHẦN B: SCHEMAS CHO PHÒNG BIÊN KỊCH ĐA HỒI & KIỂM ĐỊNH (NODES 6 -> 7)
# =====================================================================
class RecurringEntityLock(BaseModel):
    entity_token: str = Field(description="Mã thực thể cố định, VD: [CHAR_CLERK_01] hoặc [OBJ_PRINTER_01]")
    locked_visual_description: str = Field(
        description="Mô tả ngoại hình, quần áo, tuổi tác, chất liệu cố định không đổi xuyên suốt video"
    )

class StyleBible(BaseModel):
    visual_era_and_tone: str
    color_grading_lut: str
    lens_and_grain_spec: str
    negative_prompt: str
    entity_locks: List[RecurringEntityLock] = Field(min_length=4)

class ActBlueprint(BaseModel):
    act_number: int = Field(ge=1, le=5)
    act_title: str
    narrative_phase: Literal["HOOK_0_60S", "SETUP", "ESCALATION", "CLIMAX", "RESOLUTION_OUTRO"]
    target_scene_count: int = Field(ge=12, le=45)
    story_beats: List[str] = Field(min_length=4)
    open_loop_cliffhanger: str = Field(description="Cú lật hoặc câu hỏi bỏ lửng ở cuối Hồi để giữ chân khán giả")

class MasterShowrunnerPlan(BaseModel):
    selected_hypothesis: CounterHypothesis
    viral_titles: List[str] = Field(min_length=5)
    thumbnail_concept: str
    style_bible: StyleBible
    acts: List[ActBlueprint] = Field(min_length=5, max_length=5)

class ParallaxLayers(BaseModel):
    foreground_isolated: str = Field(description="Vật thể tiền cảnh tách nền mở mờ (depth of field) di chuyển nhanh")
    midground_main: str = Field(description="Chủ thể chính ở trung cảnh")
    background_plate: str = Field(description="Không gian hậu cảnh di chuyển chậm")

class AudioCueItem(BaseModel):
    sfx_category: Literal["WHOOSH", "SUB_BASS_HIT", "TENSION_RISER", "MECHANICAL_FOLEY", "PAPER_SLIDE", "GLITCH", "AMBIENT_ROOM"]
    trigger_word: str = Field(description="Từ đơn chính xác nằm trong voiceover_text")
    volume_db: float = Field(default=-6.0)
    sfx_generation_prompt: str

class SceneItem(BaseModel):
    scene_id: str
    act_number: int
    narrative_phase: Literal["HOOK_0_60S", "SETUP", "ESCALATION", "CLIMAX", "RESOLUTION_OUTRO"]
    visual_mode: Literal["AI_VIDEO_HIGH_COST", "STATIC_PARALLAX_LOW_COST", "DOCUMENT_HIGHLIGHT_ZOOM", "KINETIC_DATA_CARD"]
    voiceover_text: str = Field(description="Lời bình 10-22 từ, viết chữ hoàn toàn cho mọi con số, không dùng từ cấm")
    pause_after_sec: float = Field(ge=0.1, le=1.0, default=0.25)
    estimated_duration_sec: float
    target_frames_30fps: int
    visual_bridge_from_prev: str = Field(description="Liên kết chuyển động hoặc ánh sáng nối mượt từ cảnh ngay trước đó")
    flux_base_image_prompt: str = Field(description="Prompt sinh ảnh gốc tối thiểu 40 từ, đã nhúng mô tả từ StyleBible")
    video_motion_prompt: Optional[str] = None
    parallax_spec: Optional[ParallaxLayers] = None
    audio_cues: List[AudioCueItem] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def enforce_studio_quality_standards(self) -> "SceneItem":
        vo_lower = self.voiceover_text.lower()

        # 1. Cấm chữ số 0-9 trong lời bình để TTS đọc chuẩn 100%
        if re.search(r"\d", self.voiceover_text):
            raise ValueError(
                f"[{self.scene_id}] Chứa chữ số trong voiceover_text: '{self.voiceover_text}'. "
                "Bắt buộc chuyển mọi con số sang dạng chữ tiếng Anh."
            )

        # 2. Quét từ vựng sáo rỗng của AI
        for phrase in BANNED_AI_PHRASES:
            if phrase in vo_lower:
                raise ValueError(
                    f"[{self.scene_id}] Phát hiện cụm từ AI sáo rỗng bị cấm '{phrase}'. "
                    "Hãy viết lại bằng động từ vật lý và danh từ cụ thể."
                )

        # 3. Kiểm tra trigger_word phải khớp chính xác từ trong câu thoại
        words_in_vo = set(re.findall(r"\b[a-z']+\b", vo_lower))
        for cue in self.audio_cues:
            clean_trigger = re.sub(r"[^a-z']", "", cue.trigger_word.lower())
            if clean_trigger not in words_in_vo:
                raise ValueError(
                    f"[{self.scene_id}] trigger_word '{cue.trigger_word}' không nằm trong voiceover_text '{self.voiceover_text}'."
                )

        # 4. Khóa chiến thuật Hybrid Motion ở 60 giây đầu
        if self.narrative_phase == "HOOK_0_60S" and self.visual_mode != "AI_VIDEO_HIGH_COST":
            raise ValueError(f"[{self.scene_id}] Cảnh thuộc HOOK_0_60S bắt buộc dùng visual_mode='AI_VIDEO_HIGH_COST'.")

        # 5. Kiểm tra thông số đi kèm theo chế độ hình ảnh
        if self.visual_mode == "AI_VIDEO_HIGH_COST" and not self.video_motion_prompt:
            raise ValueError(f"[{self.scene_id}] Cảnh AI_VIDEO_HIGH_COST bắt buộc phải có video_motion_prompt.")
        if self.visual_mode == "STATIC_PARALLAX_LOW_COST" and not self.parallax_spec:
            raise ValueError(f"[{self.scene_id}] Cảnh STATIC_PARALLAX_LOW_COST bắt buộc phải có parallax_spec tách 3 lớp.")

        # 6. Đảm bảo độ sâu mô tả thị giác
        if len(self.flux_base_image_prompt.split()) < 40:
            raise ValueError(f"[{self.scene_id}] flux_base_image_prompt quá ngắn (< 40 từ). Phải mô tả đủ góc máy, chủ thể, hiện vật, ánh sáng, ống kính.")

        return self
```

---

## 6. MÃ NGUỒN CỐT LÕI 2: ĐỒ THỊ TỰ PHẢN BIỆN LANGGRAPH (`core/adversarial_graph.py`)

Đoạn mã dưới đây hiện thực hóa kiến trúc **Hội đồng Nghiên cứu Tự Phản biện** bằng `LangGraph`, sử dụng `Send` API để tung nhiều Thợ săn Bằng chứng chạy song song và `Command` API để Công tố viên điều hướng vòng lặp động.

```python
import operator
import numpy as np
from typing import Annotated, List, TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, Send
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

from core.schemas import (
    RivalAutopsyReport,
    CounterHypothesis,
    HypothesisBatch,
    ForensicEvidenceItem,
    EvidenceHarvestBatch,
    ProsecutorIndictment,
    MasterShowrunnerPlan,
    SceneItem
)

# =====================================================================
# 1. ĐỊNH NGHĨA BỘ NHỚ TRẠNG THÁI CHUNG (SHARED GRAPH STATE)
# =====================================================================
class BrainGraphState(TypedDict):
    youtube_url: str
    rival_transcript: str
    rival_comments: List[str]
    autopsy_report: RivalAutopsyReport
    
    # Trạng thái của Hội đồng Nghiên cứu Phản biện
    candidate_hypotheses: List[CounterHypothesis]
    evidence_vault: Annotated[List[ForensicEvidenceItem], operator.add] # Tự động gộp bằng chứng từ các luồng song song
    prosecutor_history: Annotated[List[ProsecutorIndictment], operator.add]
    debate_iteration: int
    previous_vault_embedding: List[float]
    
    # Trạng thái của Phòng Biên kịch
    showrunner_plan: MasterShowrunnerPlan
    final_scenes: List[SceneItem]

class HunterTaskState(TypedDict):
    """State cục bộ truyền cho từng Worker chạy song song qua Send API"""
    hypothesis_id: str
    search_queries: List[str]
    engine_preference: str

# =====================================================================
# 2. KHỞI TẠO CÁC MODEL CHUYÊN BIỆT CHO TỪNG VAI TRÒ
# =====================================================================
gemini_pro = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.2)
gemini_flash = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
o3_architect = ChatOpenAI(model="o3-mini", reasoning_effort="high")
o3_prosecutor = ChatOpenAI(model="o3-mini", reasoning_effort="high")
claude_director = ChatAnthropic(model="claude-3-5-sonnet-latest", temperature=0.4, max_tokens=8192)
embedder = OpenAIEmbeddings(model="text-embedding-3-small")

# =====================================================================
# 3. CÁC NODE TRONG HỘI ĐỒNG NGHIÊN CỨU TỰ PHẢN BIỆN
# =====================================================================
def node_rival_autopsy(state: BrainGraphState) -> Command[Literal["hypothesis_architect"]]:
    """Node 1: Giải phẫu kịch bản và 100 bình luận của đối thủ để tìm điểm mù"""
    structured_autopsy = gemini_pro.with_structured_output(RivalAutopsyReport)
    
    prompt = f"""Analyze this competitor's video transcript and top 100 audience comments.
    Identify their core thesis, expose their superficial/unproven claims, and extract the exact questions viewers are arguing about.
    Transcript: {state['rival_transcript'][:30000]}
    Top Comments: {state['rival_comments'][:100]}"""
    
    report = structured_autopsy.invoke(prompt)
    return Command(
        update={"autopsy_report": report, "debate_iteration": 0},
        goto="hypothesis_architect"
    )

def node_hypothesis_architect(state: BrainGraphState):
    """Node 2: Dùng mô hình suy luận sâu (o3) lập 3 giả thuyết lật ngược đối thủ"""
    structured_architect = o3_architect.with_structured_output(HypothesisBatch)
    
    past_rejections = ""
    if state.get("prosecutor_history"):
        last_indictment = state["prosecutor_history"][-1]
        past_rejections = f"PREVIOUS HYPOTHESES WERE REJECTED BY PROSECUTOR BECAUSE: {last_indictment.prosecutor_reasoning}"

    prompt = f"""You are a Investigative Counter-Narrative Architect.
    Competitor Thesis: {state['autopsy_report'].rival_core_thesis}
    Competitor Blindspots: {state['autopsy_report'].superficial_claims}
    Audience Questions: {state['autopsy_report'].audience_unanswered_questions}
    {past_rejections}
    
    Formulate 3 radical, fact-driven Counter-Hypotheses that completely flip or dismantle the competitor's premise.
    For each hypothesis, specify the exact 'Smoking Gun' primary evidence needed and 3 deep search queries."""
    
    batch = structured_architect.invoke(prompt)
    return {"candidate_hypotheses": batch.hypotheses}

def dispatch_parallel_hunters(state: BrainGraphState) -> List[Send]:
    """Hàm Map-Reduce: Tung đồng loạt các Forensic Hunter chạy song song cho từng giả thuyết"""
    sends = []
    for hyp in state["candidate_hypotheses"]:
        sends.append(
            Send("forensic_hunter_worker", {
                "hypothesis_id": hyp.hypothesis_id,
                "search_queries": hyp.initial_search_vectors,
                "engine_preference": "EXA_AND_FIRECRAWL"
            })
        )
    return sends

def node_forensic_hunter_worker(task: HunterTaskState) -> dict:
    """Node 3 (Worker chạy song song): Gọi Exa.ai + Tavily + Firecrawl để săn bằng chứng vật lý"""
    # Tại đây tích hợp lệnh gọi thực tế tới Exa.ai API, Tavily API và Firecrawl Markdown Scraper
    # Sau khi gom được Markdown toàn văn từ các báo cáo PDF/trang web, Gemini 2.5 Flash rút trích thành ForensicEvidenceItem
    structured_extractor = gemini_flash.with_structured_output(EvidenceHarvestBatch)
    
    prompt = f"""You are a Forensic Evidence Harvester working on Hypothesis {task['hypothesis_id']}.
    Execute and extract hard, granular facts from search results for queries: {task['search_queries']}.
    MANDATORY: Extract exact timestamps, physical locations, serial numbers/metrics, verbatim quotes, and tangible artifact descriptions."""
    
    harvest = structured_extractor.invoke(prompt)
    # Nhờ Annotated[List, operator.add], kết quả của mọi Worker tự động gộp vào state['evidence_vault']
    return {"evidence_vault": harvest.new_evidence}

def node_red_team_prosecutor(
    state: BrainGraphState
) -> Command[Literal["forensic_hunter_worker", "hypothesis_architect", "showrunner_scriptroom"]]:
    """Node 4: Công tố viên Phản biện + Kiểm tra Độ lợi Thông tin (Cosine Similarity)"""
    current_iter = state.get("debate_iteration", 0) + 1
    vault = state.get("evidence_vault", [])
    
    # 1. Tính toán Vector Embedding của kho bằng chứng hiện tại để kiểm tra bão hòa thông tin
    vault_text = " ".join([f"{e.exact_timestamp_or_date} {e.factual_claim} {e.quantitative_metric}" for e in vault])
    current_emb = embedder.embed_query(vault_text[:8000]) if vault_text else [0.0] * 1536
    
    info_gain = 1.0
    if state.get("previous_vault_embedding"):
        prev_emb = np.array(state["previous_vault_embedding"])
        curr_emb = np.array(current_emb)
        cosine_sim = np.dot(prev_emb, curr_emb) / (np.linalg.norm(prev_emb) * np.linalg.norm(curr_emb) + 1e-9)
        info_gain = 1.0 - float(cosine_sim)

    # 2. Gọi o3-mini đóng vai Công tố viên Đỏ tấn công kho bằng chứng
    structured_prosecutor = o3_prosecutor.with_structured_output(ProsecutorIndictment)
    prompt = f"""You are a ruthless Red-Team Investigative Prosecutor.
    Attack the gathered evidence in the Evidence Vault against our Candidate Hypotheses.
    Current Debate Iteration: {current_iter} (Information Gain from last round: {info_gain:.4f}).
    
    STRICT CRITERIA FOR APPROVAL ('APPROVE_FOR_SCRIPTROOM'):
    1. Must have at least 5 PRIMARY/FORENSIC/TECHNICAL sources.
    2. Must have at least 12 exact timestamps/dates and 15 hard quantitative metrics.
    3. Every key event must have tangible physical artifacts described (models, materials, colors) so AI can render them.
    4. Zero unexplained timeline contradictions.
    
    If criteria are not met, issue 'REJECT_AND_HUNT_DEEPER' with targeted search directives, or 'DISCARD_HYPOTHESIS_AND_RETHINK' if all hypotheses are fundamentally flawed.
    
    Hypotheses: {state['candidate_hypotheses']}
    Evidence Vault ({len(vault)} items): {vault}"""
    
    indictment = structured_prosecutor.invoke(prompt)

    # 3. Điều hướng Động (Dynamic Routing) dựa trên Phán quyết & Ngưỡng Toán học
    # Nếu đã đạt chuẩn (>= 0.85) HOẶC thông tin đã bão hòa (info_gain < 0.03) HOẶC chạm trần 4 vòng tranh biện:
    if (
        indictment.verdict == "APPROVE_FOR_SCRIPTROOM"
        or indictment.forensic_specificity_score_estimate >= 0.85
        or info_gain < 0.03
        or current_iter >= 4
    ):
        return Command(
            update={
                "prosecutor_history": [indictment],
                "debate_iteration": current_iter,
                "previous_vault_embedding": current_emb
            },
            goto="showrunner_scriptroom"
        )
    
    # Nếu giả thuyết sai hoàn toàn -> Quay về Node 2 lập lại giả thuyết mới
    if indictment.verdict == "DISCARD_HYPOTHESIS_AND_RETHINK":
        return Command(
            update={"prosecutor_history": [indictment], "debate_iteration": current_iter},
            goto="hypothesis_architect"
        )

    # Nếu giả thuyết đúng nhưng thiếu bằng chứng cụ thể -> Tung lại Hunter đi đào đúng các lỗ hổng vừa bị vạch ra
    targeted_queries = [flaw.targeted_search_directive for flaw in indictment.identified_flaws]
    return Command(
        update={
            "prosecutor_history": [indictment],
            "debate_iteration": current_iter,
            "previous_vault_embedding": current_emb
        },
        goto=[
            Send("forensic_hunter_worker", {
                "hypothesis_id": indictment.winning_hypothesis_id,
                "search_queries": targeted_queries,
                "engine_preference": "DEEP_FORENSIC"
            })
        ]
    )

# =====================================================================
# 4. NODE PHÒNG BIÊN KỊCH ĐA HỒI & KIỂM ĐỊNH (NODES 6 & 7)
# =====================================================================
def node_showrunner_scriptroom(state: BrainGraphState) -> Command[Literal[END]]:
    """Node 6 & 7: Lập dàn ý 5 Hồi và sinh kịch bản cuốn chiếu từng Hồi với Self-Healing Validators"""
    winning_id = state["prosecutor_history"][-1].winning_hypothesis_id
    
    # Bước 6.1: Lập MasterShowrunnerPlan (5 Acts + StyleBible khóa thực thể)
    planner = claude_director.with_structured_output(MasterShowrunnerPlan)
    plan = planner.invoke(f"""Design a 5-Act Documentary Master Plan and locked StyleBible for winning hypothesis {winning_id}.
    Evidence Vault: {state['evidence_vault']}""")
    
    # Bước 6.2: Chạy vòng lặp sinh chi tiết từng Hồi (Act 1 -> Act 5), tự động kích hoạt Pydantic Validator
    class ActScenesWrapper(SceneItem.__bases__[0]):
        scenes: List[SceneItem]
        
    scene_generator = claude_director.with_structured_output(ActScenesWrapper)
    all_validated_scenes: List[SceneItem] = []
    prev_bridge = "COLD OPEN - START IN MEDIA RES AT THE EXACT MOMENT OF CRISIS."
    
    for act in plan.acts:
        act_batch = scene_generator.invoke(f"""Execute Act {act.act_number}: {act.act_title} ({act.narrative_phase}).
        Target scenes: {act.target_scene_count}.
        Previous scene bridge: {prev_bridge}.
        Open-loop cliffhanger to plant at end of this Act: {act.open_loop_cliffhanger}.
        StyleBible (MUST embed entity locks): {plan.style_bible.model_dump_json()}.
        Verified Forensic Evidence: {state['evidence_vault']}""")
        
        all_validated_scenes.extend(act_batch.scenes)
        last_sc = act_batch.scenes[-1]
        prev_bridge = f"Last VO: {last_sc.voiceover_text} | Last Visual: {last_sc.flux_base_image_prompt}"
        
    return Command(
        update={"showrunner_plan": plan, "final_scenes": all_validated_scenes},
        goto=END
    )

# =====================================================================
# 5. ĐÓNG GÓI ĐỒ THỊ (COMPILE GRAPH)
# =====================================================================
def build_adversarial_brain_graph():
    builder = StateGraph(BrainGraphState)
    
    builder.add_node("rival_autopsy", node_rival_autopsy)
    builder.add_node("hypothesis_architect", node_hypothesis_architect)
    builder.add_node("forensic_hunter_worker", node_forensic_hunter_worker)
    builder.add_node("red_team_prosecutor", node_red_team_prosecutor)
    builder.add_node("showrunner_scriptroom", node_showrunner_scriptroom)
    
    builder.add_edge(START, "rival_autopsy")
    builder.add_conditional_edges("hypothesis_architect", dispatch_parallel_hunters, ["forensic_hunter_worker"])
    builder.add_edge("forensic_hunter_worker", "red_team_prosecutor")
    
    return builder.compile()
```

---

## 7. BỘ SYSTEM PROMPTS CHUYÊN SÂU CHO HỘI ĐỒNG PHẢN BIỆN (`core/prompts.py`)

### 7.1. System Prompt cho `Red-Team Prosecutor` (Node 4 - `OpenAI o3-mini`)
```text
You are the Chief Red-Team Investigative Prosecutor at a top-tier documentary studio.
Your sole purpose is to DESTROY weak, generic, or poorly sourced research before it ever reaches our scriptwriters.
You are allergic to Wikipedia-level summaries, vague timelines, and abstract descriptions.

When reviewing the [Evidence Vault] against the [Candidate Hypotheses], apply these 4 ruthless tests:

TEST 1: THE PRIMARY SOURCE TEST
- Did the Hunter only find blog posts or news summaries? REJECT IT.
- Demand court dockets, patent filings, declassified memos, technical post-mortems, or eyewitness transcripts.

TEST 2: THE FORENSIC CHRONOLOGY TEST
- Are events described vaguely as "a few days later" or "in early 2016"? REJECT IT.
- Demand exact hours, minutes, timezones, and sequential causality. If Source A says 8:00 PM and Source B says 8:36 PM, flag the contradiction and order a targeted search to resolve it.

TEST 3: THE TANGIBLE VISUAL ARTIFACT TEST
- Can our AI Art Director draw a concrete physical object from this fact?
- If the fact says "hackers used malware to steal money", REJECT IT as too abstract.
- Demand physical details: What model of printer jammed? What color was the warning LED? What exact string of text appeared on the terminal screen? What was the weather outside the building that night?

TEST 4: THE VIRAL DIFFERENTIATION TEST
- Does this evidence merely repeat what the competitor video already said? REJECT IT.
- Only approve when the evidence proves a shocking counter-narrative or exposes a critical 1% detail the competitor missed.

For every flaw you identify, you MUST write a razor-sharp `targeted_search_directive` using advanced operators (e.g., filetype:pdf, "exhibit", "serial", "log", exact names) to force the Hunter Agent to dig deeper.
```

### 7.2. System Prompt cho `Lead Showrunner & Scene Director` (Node 6 - `Claude 3.5 Sonnet`)
```text
You are an Elite Documentary Showrunner combining the investigative rigor of 'Lemmino' with the high-retention visual pacing of 'MagnatesMedia' and '역사한줌'.

UNCOMPROMISING DIRECTING LAWS:

1. THE 60-SECOND HIGH-BUDGET HOOK (ACT 1):
   - Start at Scene 1 right inside a physical room at the exact second something goes wrong. Zero greetings, zero throat-clearing.
   - All scenes in Act 1 (first 60 seconds) MUST use `visual_mode = "AI_VIDEO_HIGH_COST"` with dynamic camera movement (`SLOW_PUSH_IN`, `HANDHELD_TENSION`, `ORBIT_3D`).
   - Within the first 45 seconds, state the competitor's common belief and shatter it using our Smoking Gun paradox.

2. THE COST-OPTIMIZED HYBRID BODY (ACTS 2 TO 5):
   - After the 60-second mark, protect production budget without losing retention:
     * 50% of scenes: `STATIC_PARALLAX_LOW_COST` (You MUST define 3 distinct depth layers: foreground object out-of-focus, midground subject, background environment so our studio engine can animate 2.5D camera motion).
     * 20% of scenes: `DOCUMENT_HIGHLIGHT_ZOOM` (Close-ups on actual archival documents, blueprints, maps, or court transcripts with a glowing highlight box).
     * 10% of scenes: `KINETIC_DATA_CARD` (Stark typography slamming exact financial figures or timestamps onto a dark textured background).
     * 20% of scenes: `AI_VIDEO_HIGH_COST` (Reserved strictly for emotional peaks, explosions, or critical human micro-actions).

3. VISUAL CONTINUITY & ENTITY LOCKING:
   - Never write generic image prompts. Every `flux_base_image_prompt` must be at least 40 words long, containing: [Camera Angle & Lens] + [Locked Entity Descriptor from StyleBible] + [Micro-Action & Physical Props] + [Lighting & Color LUT].
   - Every scene must specify `visual_bridge_from_prev` so cuts feel intentional (e.g., matching a circular radar screen to a circular clock face).

4. ANTI-SLOP & TTS PERFECTION:
   - Write ALL numbers, years, currencies, and percentages out as full English words.
   - Vary sentence length dramatically. Follow a 20-word atmospheric sentence with a 4-word punch.
   - Every `AudioCue.trigger_word` MUST be an exact word copied from that scene's `voiceover_text`.
```

---

## 8. CẤU TRÚC THƯ MỤC DỰ ÁN & LỘ TRÌNH CHẠY THỰC TẾ

```text
faceless_studio_v3/
├── .env                          # API Keys: OPENAI, ANTHROPIC, GOOGLE, GROQ, EXA, TAVILY, FIRECRAWL
├── requirements.txt              # langgraph, pydantic, langchain-*, exa-py, tavily-python, firecrawl-py, yt-dlp
├── core/
│   ├── schemas.py                # Toàn bộ Pydantic Schemas & Self-Healing Validators (Mục 5)
│   ├── prompts.py                # Bộ System Prompts cho Hội đồng Phản biện & Đạo diễn (Mục 7)
│   └── adversarial_graph.py      # Đồ thị LangGraph Cyclic & Map-Reduce (Mục 6)
├── tools/
│   ├── youtube_autopsy.py        # Module yt-dlp + Groq Whisper v3 + Comment Scraper
│   └── forensic_search.py        # Module bọc Exa.ai + Tavily + Firecrawl Markdown Scraper
└── app_mission_control.py        # Giao diện Streamlit hiển thị trực tiếp Phiên tòa Tranh biện real-time
```

### Quy trình Kiểm thử Thực chiến (3 Bước):
1. **Test Mắt xích Giải phẫu (Tầng 1):** Chạy độc lập `youtube_autopsy.py` với 1 link đối thủ bất kỳ, kiểm tra xem `Gemini 2.5 Pro` có trích xuất đúng luận điểm chính và các câu hỏi tranh cãi từ bình luận của người xem hay không.
2. **Test Phiên tòa Tranh tụng (Tầng 2):** Chạy vòng lặp `Node 2 -> Node 3 -> Node 4` trên terminal, quan sát cách `o3-mini` (Công tố viên) bác bỏ bằng chứng ở vòng 1 và ép `Exa.ai` + `Firecrawl` đào ra các con số/hiện vật sâu hơn ở vòng 2 và vòng 3.
3. **Test Phòng Biên kịch 5 Hồi (Tầng 3):** Cho `Claude 3.5 Sonnet` nhận hồ sơ đã duyệt để xuất ra `Master_Production_Script_v3.json`, kiểm tra tự động qua `Pydantic Validators` đảm bảo $0$ lỗi định dạng trước khi chuyển sang Giai đoạn 2 (Sinh Media).