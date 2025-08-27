# API:
# 1. Cài đặt thư viện cần thiết: pip install fastapi "uvicorn[standard]"
# 2. Chạy server từ terminal: uvicorn main:app --reload

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict
import math

# --- Các Model Dữ liệu (Pydantic) ---

class PoolUpdateRequest(BaseModel):
    """Model cho request cập nhật/thêm mới một pool."""
    pool_id: int = Field(..., alias='poolId', description="Định danh của pool.")
    pool_values: List[float] = Field(..., alias='poolValues', description="Danh sách giá trị để thêm vào pool.")

class PoolUpdateResponse(BaseModel):
    """Model cho response sau khi cập nhật pool."""
    status: str

class PoolQueryRequest(BaseModel):
    """Model cho request truy vấn một pool."""
    pool_id: int = Field(..., alias='poolId', description="Định danh của pool cần truy vấn.")
    percentile: float = Field(..., gt=0, lt=100, description="Percentile cần tính (0 < percentile < 100).")

class PoolQueryResponse(BaseModel):
    """Model cho response sau khi truy vấn pool."""
    calculated_quantile: float = Field(..., alias='calculatedQuantile', description="Giá trị quantile đã được tính toán.")
    total_count: int = Field(..., alias='totalCount', description="Tổng số phần tử trong pool.")


# --- Nơi lưu trữ dữ liệu (In-Memory) ---
# Sử dụng dictionary để lưu trữ các pool, cho phép truy xuất nhanh.
pools: Dict[int, List[float]] = {}


# --- Khởi tạo ứng dụng FastAPI ---
app = FastAPI(
    title="API Tính toán Quantile",
    description="API để quản lý các pool giá trị và tính toán quantile.",
    version="1.0.0"
)


# --- Logic tính toán Quantile ---
def calculate_quantile_from_scratch(data: List[float], percentile: float) -> float:
    """Tính toán giá trị quantile cho một tập dữ liệu.

    Hàm này sử dụng phương pháp nội suy tuyến tính (linear interpolation) để
    ước tính giá trị tại một percentile cho trước.

    Args:
        data: Một danh sách các số.
        percentile: Giá trị percentile cần tính (từ 0 đến 100).

    Returns:
        Giá trị quantile đã được tính toán.

    Raises:
        ValueError: Nếu danh sách `data` rỗng.
    """
    if not data:
        raise ValueError("Không thể tính quantile cho danh sách rỗng.")

    sorted_data = sorted(data)
    n = len(sorted_data)
    # Tính toán thứ hạng (rank) dựa trên percentile.
    rank = (percentile / 100) * (n - 1)
    
    if rank.is_integer():
        return sorted_data[int(rank)]
    else:
        # Nội suy tuyến tính giữa hai giá trị gần nhất.
        lower_index = math.floor(rank)
        upper_index = math.ceil(rank)
        lower_value = sorted_data[lower_index]
        upper_value = sorted_data[upper_index]
        weight = rank - lower_index
        return lower_value + weight * (upper_value - lower_value)


# --- Các Endpoint của API ---

@app.post("/pools/update", response_model=PoolUpdateResponse, status_code=status.HTTP_200_OK)
async def update_pool(request: PoolUpdateRequest):
    """
    Thêm mới (insert) hoặc cập nhật (append) giá trị vào một pool.

    Nếu poolId đã tồn tại, các giá trị mới sẽ được thêm vào cuối danh sách.
    Nếu chưa tồn tại, một pool mới sẽ được tạo với các giá trị đã cho.
    """
    pool_id = request.pool_id
    values_to_add = request.pool_values

    if pool_id in pools:
        pools[pool_id].extend(values_to_add)
        response_status = "appended"
    else:
        pools[pool_id] = values_to_add
        response_status = "inserted"
        
    return PoolUpdateResponse(status=response_status)


@app.post("/pools/query", response_model=PoolQueryResponse, status_code=status.HTTP_200_OK)
async def query_pool(request: PoolQueryRequest):
    """
    Truy vấn một pool để tính toán giá trị quantile được chỉ định.
    """
    pool_id = request.pool_id
    percentile = request.percentile

    # Đảm bảo pool được yêu cầu phải tồn tại.
    if pool_id not in pools:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy pool với ID {pool_id}."
        )
        
    pool_values = pools[pool_id]
    count = len(pool_values)

    # Đảm bảo pool không rỗng trước khi tính toán.
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pool với ID {pool_id} rỗng, không thể tính quantile."
        )
    
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
