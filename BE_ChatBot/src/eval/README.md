# Eval benchmark

Folder này chứa bộ đo chỉ số cho báo cáo tốt nghiệp của chatbot du lịch. Bộ đo tập trung vào 3 nhóm đã chốt:

1. Dataset Coverage
2. Retrieval Quality
3. Output Validity

## Cấu trúc folder

```text
src/eval/
  __init__.py
  README.md
  run_all.py
  self_check.py

  common/
    config.py
    metrics.py
    path_utils.py
    place_loader.py
    schemas.py

  dataset/
    coverage.py

  retrieval/
    benchmark.py
    relevance.py
    data/cases.json

  output/
    validity.py
    response_parser.py
    data/cases.json

  reporting/
    report_builder.py

  outputs/
```

## Vai trò từng nhóm

| Nhóm      | File                          | Vai trò                                                                   | Có gọi LLM không                   |
| --------- | ----------------------------- | ------------------------------------------------------------------------- | ---------------------------------- |
| Common    | `common/config.py`            | Cấu hình đường dẫn, K values, field bắt buộc, provider/model runtime info | Không                              |
| Common    | `common/schemas.py`           | Dataclass cho metric row, benchmark case, result                          | Không                              |
| Common    | `common/path_utils.py`        | Đọc/ghi JSON, CSV, normalize text                                         | Không                              |
| Common    | `common/place_loader.py`      | Load 600 địa điểm từ `src/source_data/places_data`                        | Không                              |
| Common    | `common/metrics.py`           | Precision@K, Recall@K, nDCG@K, latency summary                            | Không                              |
| Dataset   | `dataset/coverage.py`         | Đo quy mô dữ liệu, số địa điểm theo vùng, metadata missing, rating        | Không                              |
| Retrieval | `retrieval/relevance.py`      | Rule tạo ground truth mềm theo region/tag/type                            | Không                              |
| Retrieval | `retrieval/benchmark.py`      | Đo Precision@K, Recall@5, nDCG@5, latency, rerank improvement             | Có thể có                          |
| Retrieval | `retrieval/data/cases.json`   | 18 query benchmark retrieval, 3 case mỗi vùng                             | Không                              |
| Output    | `output/response_parser.py`   | Tách JSON plan từ câu trả lời model                                       | Không                              |
| Output    | `output/validity.py`          | Đo JSON output, số ngày, đúng vùng, field đầy đủ, latency end-to-end      | Có                                 |
| Output    | `output/data/cases.json`      | 12 query benchmark output, 2 case mỗi vùng                                | Không                              |
| Reporting | `reporting/report_builder.py` | Gộp các file summary CSV thành bảng báo cáo                               | Không                              |
| Root      | `run_all.py`                  | Chạy toàn bộ benchmark                                                    | Có nếu không skip retrieval/output |
| Root      | `self_check.py`               | Kiểm tra nhanh parser/metric/dataset/case file                            | Không                              |
| Root      | `outputs/`                    | Nơi ghi kết quả đo                                                        | Không                              |

## Nguồn dữ liệu

Benchmark đọc dữ liệu địa điểm từ:

```powershell
D:\KLTN\Project\BE_ChatBot\src\source_data\places_data
```

Kỳ vọng hiện tại:

- 6 file JSON theo vùng.
- 100 địa điểm mỗi vùng.
- Tổng 600 địa điểm.

## Điểm cần lưu ý về LLM

### `dataset/coverage.py`

Không gọi LLM. File này chỉ đọc JSON địa điểm và tính các chỉ số tĩnh.

### `retrieval/benchmark.py`

Có thể gọi LLM ở bước rewrite/multi-query retrieval:

- Entry code: `RAGStorage.get_multi_query_retriever()`.
- LLM liên quan: rewrite LLM của `MultiQueryRetriever`.
- Env cần ghi nhận khi báo cáo:
  - `REWRITE_LLM_PROVIDER`
  - `REWRITE_LLM_MODEL`

File này cũng gọi reranker:

- Entry code: `DocumentReranker.compress_documents(...)`.
- Env cần ghi nhận khi báo cáo:
  - `RERANKER_PROVIDER`
  - `RERANKER_MODEL_NAME`
  - `RERANKER_TOP_N`
  - Nếu dùng Cohere: cần `COHERE_API_KEY` trong `.env`, không ghi API key vào báo cáo.

Kết quả benchmark sẽ ghi `llm_runtime` vào JSON output để biết lần đo dùng provider/model nào.

### `output/validity.py`

Có gọi pipeline end-to-end:

- Entry code: `RAGInference.predict_async(...)`.
- Có thể gọi:
  - rewrite LLM: `REWRITE_LLM_PROVIDER`, `REWRITE_LLM_MODEL`
  - retriever + reranker: `RERANKER_PROVIDER`, `RERANKER_MODEL_NAME`, `RERANKER_TOP_N`
  - core answer LLM: `LLM_PROVIDER`, `LLM_MODEL`

Đây là chỉ số phụ thuộc model. Khi đổi provider/model trong `.env`, nên restart backend hoặc process Python trước khi đo lại vì một số LLM object có thể được cache trong runtime.

## Cách chạy sau khi confirm

Chạy từ root backend:

```powershell
cd D:\KLTN\Project\BE_ChatBot
$env:PYTHONPATH="."
$env:EVAL_CASE_DELAY_SECONDS="7"
```

`EVAL_CASE_DELAY_SECONDS` là thời gian chờ giữa các case trong retrieval/output benchmark. Mặc định trong code là `7` giây để giảm khả năng chạm rate limit theo phút. Có thể đặt `0` nếu muốn tắt delay.

### 1. Self-check tĩnh, không gọi LLM

```powershell
python -m src.eval.self_check
```

Kỳ vọng:

```text
Eval self-check passed. No LLM, Chroma, or reranker call was made.
```

### 2. Chỉ đo Dataset Coverage, không gọi LLM

```powershell
python -m src.eval.dataset.coverage
```

Output:

- `src/eval/outputs/dataset_coverage.json`
- `src/eval/outputs/dataset_coverage_summary.csv`

### 3. Đo Retrieval Quality

Nên chạy thử 1 case trước vì có thể gọi rewrite LLM và reranker:

```powershell
python -m src.eval.retrieval.benchmark --limit 1
```

Chạy toàn bộ 18 case (Tốn 18 lần call Cohere + Groq):

```powershell
python -m src.eval.retrieval.benchmark
```

Output:

- `src/eval/outputs/retrieval_results.json`
- `src/eval/outputs/retrieval_summary.csv`

### 4. Đo Output Validity

Nên chạy thử 1 case trước vì bước này gọi `RAGInference.predict_async(...)` và core answer LLM:

```powershell
python -m src.eval.output.validity --limit 1
```

Chạy 10 case (Tốn khoảng 10 lần call Ollama + Cohere + Groq):

```powershell
python -m src.eval.output.validity --limit 10
```

Output:

- `src/eval/outputs/output_validity_results.json`
- `src/eval/outputs/output_validity_summary.csv`

### 5. Gộp bảng báo cáo

Nếu đã chạy các nhóm metric riêng:

```powershell
python -m src.eval.reporting.report_builder
```

Output:

- `src/eval/outputs/benchmark_table.csv`
- `src/eval/outputs/benchmark_summary.json`
- `src/eval/outputs/benchmark_report.md`

### 6. Chạy toàn bộ

Chạy smoke với 1 case retrieval/output:

```powershell
python -m src.eval.run_all --limit 1
```

Chạy toàn bộ:

```powershell
python -m src.eval.run_all
```

Nếu chỉ muốn đo dataset coverage rồi build report, không gọi LLM:

```powershell
python -m src.eval.run_all --skip-retrieval --skip-output
```

## Cách đọc chỉ số

| Nhóm              | Chỉ số chính                            | Ý nghĩa                                                               |
| ----------------- | --------------------------------------- | --------------------------------------------------------------------- |
| Dataset Coverage  | Tổng số địa điểm, số địa điểm theo vùng | Chứng minh quy mô dữ liệu và độ cân bằng 100 địa điểm/vùng            |
| Dataset Coverage  | Tỷ lệ thiếu metadata                    | Metadata thiếu có thể làm retrieval/rerank/lập lịch trình kém ổn định |
| Retrieval Quality | Precision@K                             | Top-K có bao nhiêu tài liệu đúng                                      |
| Retrieval Quality | Recall@5                                | Top-5 đã tìm được bao nhiêu tài liệu liên quan trong ground truth     |
| Retrieval Quality | nDCG@5                                  | Tài liệu đúng có được xếp ở rank cao không                            |
| Retrieval Quality | Rerank improvement                      | Reranker cải thiện hay làm giảm Precision/nDCG                        |
| Output Validity   | Day-count match rate                    | Lịch trình có đúng số ngày user yêu cầu không                         |
| Output Validity   | Region consistency rate                 | Địa điểm trả về có đúng vùng không                                    |
| Output Validity   | Required-field completion rate          | JSON output có đủ field để FE hiển thị không                          |
| Output Validity   | End-to-end latency                      | Thời gian từ query đến câu trả lời hoàn chỉnh                         |

## Ghi chú báo cáo

- Dataset Coverage là chỉ số ổn định nhất vì không phụ thuộc LLM.
- Retrieval Quality phụ thuộc trạng thái ChromaDB, rewrite LLM và reranker.
- Output Validity phụ thuộc toàn bộ pipeline và core answer LLM, nên cần ghi rõ provider/model trong báo cáo.
- Không đưa API key vào báo cáo. Chỉ ghi provider, model name, top_n và ngày/giờ chạy benchmark.

## Troubleshooting

### `KeyError: 'results'` khi chạy retrieval benchmark

Lỗi này thường xuất hiện khi reranker API trả về JSON lỗi, ví dụ rate limit, quota, auth error hoặc request bị provider từ chối. Thư viện `rerankers` kỳ vọng response có key `results`, nên nếu provider trả JSON lỗi thì có thể văng `KeyError: 'results'`.

Benchmark retrieval hiện đã catch lỗi reranker theo từng case:

- Case lỗi sẽ fallback dùng raw retrieved docs thay cho reranked docs.
- `src/eval/outputs/retrieval_results.json` sẽ có `rerank_error_count`.
- Từng case lỗi sẽ có field `rerank_error`.
- `case_delay_seconds` trong output cho biết benchmark đã chờ bao lâu giữa các case.

Có thể tăng delay nếu provider vẫn báo rate limit:

```powershell
$env:EVAL_CASE_DELAY_SECONDS="10"
python -m src.eval.retrieval.benchmark
```

Nếu muốn tránh gọi API reranker khi đo nhiều case, có thể dùng local reranker:

```powershell
$env:RERANKER_PROVIDER="huggingface"
$env:RERANKER_MODEL_NAME="BAAI/bge-reranker-v2-m3"
```

Nếu vẫn dùng Cohere, nên chạy từng phần nhỏ:

```powershell
python -m src.eval.retrieval.benchmark --limit 3
python -m src.eval.retrieval.benchmark --case-id rq_hcm_history
```

### Lỗi provider khi chạy output validity

`output/validity.py` gọi `RAGInference.predict_async(...)`, nên có thể lỗi ở core LLM, rewrite LLM hoặc reranker. Benchmark hiện đã catch lỗi theo từng case:

- Case lỗi sẽ có `parse_success=false`.
- `parse_error` sẽ ghi lỗi provider/runtime.
- `src/eval/outputs/output_validity_results.json` sẽ có `error_count`.
- `case_delay_seconds` trong output cho biết benchmark đã chờ bao lâu giữa các case.
