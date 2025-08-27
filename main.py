# main.py
# Hướng dẫn chạy API:
# 1. Cài đặt thư viện cần thiết: pip install fastapi "uvicorn[standard]"
# 2. Chạy server từ terminal: uvicorn main:app --reload

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict
import math

# --- Các Model (Khuôn mẫu dữ liệu) sử dụng Pydantic ---
# Các class này giúp xác thực (validate) dữ liệu gửi đến và trả về từ API,
# đảm bảo dữ liệu luôn đúng cấu trúc và kiểu dữ liệu.

class PoolUpdateRequest(BaseModel):
    """Định nghĩa cấu trúc JSON cho request cập nhật pool."""
    pool_id: int = Field(..., alias='poolId', description="Định danh duy nhất của pool.")
    pool_values: List[float] = Field(..., alias='poolValues', description="Danh sách các giá trị số để thêm vào pool.")

class PoolUpdateResponse(BaseModel):
    """Định nghĩa cấu trúc JSON cho response sau khi cập nhật pool."""
    status: str

class PoolQueryRequest(BaseModel):
    """Định nghĩa cấu trúc JSON cho request truy vấn pool."""
    pool_id: int = Field(..., alias='poolId', description="Định danh của pool cần truy vấn.")
    percentile: float = Field(..., gt=0, lt=100, description="Giá trị percentile cần tính (ví dụ: 99.5).")

class PoolQueryResponse(BaseModel):
    """Định nghĩa cấu trúc JSON cho response sau khi truy vấn pool."""
    calculated_quantile: float = Field(..., alias='calculatedQuantile', description="Giá trị quantile đã được tính toán.")
    total_count: int = Field(..., alias='totalCount', description="Tổng số phần tử trong pool.")


# --- Nơi lưu trữ dữ liệu (In-Memory) ---
# Sử dụng một dictionary của Python để làm cơ sở dữ liệu tạm thời trong bộ nhớ.
# - Key: pool_id (int)
# - Value: danh sách các giá trị (List[float])
# Ưu điểm: Tốc độ truy xuất key rất nhanh, trung bình là O(1).
pools: Dict[int, List[float]] = {}


# --- Khởi tạo ứng dụng FastAPI ---
app = FastAPI(
    title="API Tính toán Quantile",
    description="API để quản lý các pool giá trị và tính toán quantile.",
    version="1.0.0"
)


# --- Logic tính toán Quantile ---
def calculate_quantile_from_scratch(data: List[float], percentile: float) -> float:
    """
    Tính toán quantile cho một danh sách dữ liệu mà không dùng thư viện ngoài.
    Hàm này sử dụng phương pháp nội suy tuyến tính (linear interpolation).
    """
    # Kiểm tra trường hợp danh sách rỗng để tránh lỗi
    if not data:
        raise ValueError("Không thể tính quantile cho danh sách rỗng.")

    # 1. Sắp xếp dữ liệu theo thứ tự tăng dần. Đây là bước tốn hiệu năng nhất, O(n log n).
    sorted_data = sorted(data)
    n = len(sorted_data)
    
    # 2. Tính toán vị trí (index) của percentile trong danh sách đã sắp xếp.
    # Công thức: index = (percentile / 100) * (n - 1)
    # Đây là vị trí dựa trên 0-based index.
    rank = (percentile / 100) * (n - 1)
    
    # 3. Nội suy giá trị nếu vị trí không phải là số nguyên.
    if rank.is_integer():
        # Nếu vị trí là số nguyên, quantile chính là giá trị tại vị trí đó.
        return sorted_data[int(rank)]
    else:
        # Nếu vị trí là số thập phân, ta nội suy tuyến tính giữa hai giá trị gần nhất.
        lower_index = math.floor(rank)
        upper_index = math.ceil(rank)
        
        lower_value = sorted_data[lower_index]
        upper_value = sorted_data[upper_index]
        
        # Trọng số chính là phần thập phân của vị trí.
        weight = rank - lower_index
        
        # Công thức nội suy tuyến tính.
        return lower_value + weight * (upper_value - lower_value)


# --- Các Endpoint của API ---

@app.post("/pools/update",
          response_model=PoolUpdateResponse,
          status_code=status.HTTP_200_OK,
          summary="Thêm mới hoặc cập nhật một pool")
async def update_pool(request: PoolUpdateRequest):
    """
    Endpoint này nhận giá trị và thêm vào một pool được chỉ định.
    - Nếu `poolId` chưa tồn tại, tạo một pool mới (insert).
    - Nếu `poolId` đã tồn tại, thêm các giá trị mới vào pool đó (append).
    """
    pool_id = request.pool_id
    values_to_add = request.pool_values

    if pool_id in pools:
        # Thao tác append có độ phức tạp O(k), với k là số lượng giá trị được thêm vào.
        pools[pool_id].extend(values_to_add)
        response_status = "appended"
    else:
        # Thao tác insert vào dictionary có độ phức tạp trung bình O(1).
        pools[pool_id] = values_to_add
        response_status = "inserted"
        
    return PoolUpdateResponse(status=response_status)


@app.post("/pools/query",
          response_model=PoolQueryResponse,
          status_code=status.HTTP_200_OK,
          summary="Truy vấn quantile của một pool")
async def query_pool(request: PoolQueryRequest):
    """
    Endpoint này tính toán một quantile được chỉ định cho một pool.
    Nó trả về giá trị quantile đã tính và tổng số phần tử trong pool.
    """
    pool_id = request.pool_id
    percentile = request.percentile

    # --- Kiểm tra tính hợp lệ (Resiliency) ---
    # 1. Kiểm tra xem pool có tồn tại không.
    if pool_id not in pools:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy pool với ID {pool_id}."
        )
        
    pool_values = pools[pool_id]
    count = len(pool_values)

    # 2. Kiểm tra xem pool có rỗng không.
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pool với ID {pool_id} rỗng, không thể tính quantile."
        )

    # --- Thực thi logic ---
    # Theo yêu cầu, ta sử dụng hàm tự viết.
    # Trong thực tế, với tập dữ liệu lớn (>= 100), có thể dùng thư viện numpy để tối ưu hiệu năng.
    # Ví dụ:
    # if count >= 100:
    #     import numpy as np
    #     quantile_value = np.percentile(pool_values, percentile)
    # else:
    #     quantile_value = calculate_quantile_from_scratch(pool_values, percentile)
    
    try:
        quantile_value = calculate_quantile_from_scratch(pool_values, percentile)
    except ValueError as e:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return PoolQueryResponse(
        calculatedQuantile=quantile_value,
        totalCount=count
    )
