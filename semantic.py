# semantic.py

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

# --- Khởi tạo ứng dụng FastAPI ---
# Đây là điểm bắt đầu của ứng dụng API.
app = FastAPI(
    title="Semantic Book API",
    description="Một ví dụ về API được thiết kế theo semantic.",
    version="1.0.0",
)

# --- Định nghĩa Model Dữ liệu (Sử dụng Pydantic) ---
# Pydantic giúp xác thực (validate) dữ liệu đầu vào và định dạng dữ liệu đầu ra.
# Điều này đảm bảo rằng dữ liệu luôn tuân theo một cấu trúc nhất định.

class Book(BaseModel):
    """
    Model đại diện cho một cuốn sách.
    Bao gồm các thuộc tính cơ bản của một cuốn sách.
    """
    id: int
    title: str
    author: str
    year: int

class CreateBook(BaseModel):
    """
    Model để tạo sách mới. 'id' sẽ được tự động tạo.
    """
    title: str
    author: str
    year: int

class UpdateBook(BaseModel):
    """
    Model để cập nhật sách. Tất cả các trường đều là Optional,
    cho phép người dùng chỉ cập nhật những thông tin họ muốn (giống PATCH).
    """
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None


# --- Giả lập một Database đơn giản ---
# Use một list để lưu trữ dữ liệu cho dễ hình dung.
db_books = [
    Book(id=1, title="Lão Hạc", author="Nam Cao", year=1943),
    Book(id=2, title="Số Đỏ", author="Vũ Trọng Phụng", year=1936),
    Book(id=3, title="Dế Mèn Phiêu Lưu Ký", author="Tô Hoài", year=1941),
]

# --- Định nghĩa các Endpoints (Routes) ---
#  endpoint gốc
@app.get("/")
def read_root():
    """
    Endpoint cho trang chủ, trả về một thông báo chào mừng.
    """
    return {"message": "Welcome to the Semantic Book API! Go to /docs to see the documentation."}


# [GET] /books - Lấy danh sách tất cả các cuốn sách
@app.get("/books", response_model=List[Book])
def get_all_books():
    """
    Endpoint này trả về một danh sách tất cả các cuốn sách trong "database".
    - URI '/books' là danh từ số nhiều, đại diện cho tài nguyên "sách".
    - HTTP Method GET được sử dụng để lấy dữ liệu mà không thay đổi gì.
    - Response model là một List[Book] để đảm bảo dữ liệu trả về đúng định dạng.
    """
    return db_books

# [GET] /books/{book_id} - Lấy thông tin một cuốn sách cụ thể
@app.get("/books/{book_id}", response_model=Book)
def get_book_by_id(book_id: int):
    """
    Endpoint này trả về thông tin của một cuốn sách dựa trên ID.
    - URI '/books/{book_id}' chỉ định một tài nguyên con cụ thể.
    - Nếu không tìm thấy sách, trả về lỗi 404 Not Found, đúng theo ngữ nghĩa HTTP.
    """
    book = next((b for b in db_books if b.id == book_id), None)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book

# [POST] /books - Tạo một cuốn sách mới
@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_new_book(book_data: CreateBook):
    """
    Endpoint này dùng để tạo một cuốn sách mới.
    - HTTP Method POST được sử dụng để tạo mới tài nguyên.
    - Dữ liệu sách mới được gửi trong body của request và được validate bởi model CreateBook.
    - Trả về status code 201 Created để thông báo tạo thành công.
    - Dữ liệu của cuốn sách vừa tạo sẽ được trả về trong response.
    """
    new_id = max(b.id for b in db_books) + 1 if db_books else 1
    new_book = Book(id=new_id, **book_data.dict())
    db_books.append(new_book)
    return new_book

# [PUT] /books/{book_id} - Cập nhật thông tin một cuốn sách
@app.put("/books/{book_id}", response_model=Book)
def update_book_info(book_id: int, book_data: UpdateBook):
    """
    Endpoint này cập nhật thông tin của một cuốn sách đã tồn tại.
    - HTTP Method PUT (hoặc PATCH) được sử dụng để cập nhật.
    - Ở đây, ta dùng logic giống PATCH: chỉ cập nhật các trường được cung cấp.
    - Nếu không tìm thấy sách, trả về lỗi 404 Not Found.
    """
    book_index = next((i for i, b in enumerate(db_books) if b.id == book_id), None)

    if book_index is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    # Lấy dữ liệu sách hiện tại
    current_book = db_books[book_index]
    # Tạo một bản sao có thể thay đổi được
    update_data = book_data.dict(exclude_unset=True) # Chỉ lấy các trường có giá trị được gửi lên

    # Cập nhật sách
    updated_book = current_book.copy(update=update_data)
    db_books[book_index] = updated_book
    return updated_book

# [DELETE] /books/{book_id} - Xóa một cuốn sách
@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book_by_id(book_id: int):
    """
    Endpoint này dùng để xóa một cuốn sách.
    - HTTP Method DELETE được sử dụng cho hành động xóa.
    - Nếu xóa thành công, trả về status code 204 No Content, báo hiệu rằng
      hành động đã thành công và không có nội dung nào cần trả về.
    - Nếu không tìm thấy sách, trả về lỗi 404 Not Found.
    """
    book = next((b for b in db_books if b.id == book_id), None)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    
    db_books.remove(book)
    # Không cần return vì status code là 204