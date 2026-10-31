# ComfyUI Video Folder

**Load Videos from Folder (Batch)** đọc nhiều **file video** trong một thư mục,
đưa từng video vào workflow dưới dạng danh sách `VIDEO` của ComfyUI.

Package độc lập, lấy cảm hứng từ cách xử lý danh sách của
[Load Images from Folder Pixaroma](https://github.com/pixaroma/ComfyUI-Pixaroma/blob/main/nodes/node_load_images_folder.py).
Mã được viết riêng; không cần cài Pixaroma. Bản này dùng các ô nhập tiêu chuẩn,
không có gallery thumbnail hoặc cửa sổ Browse như Pixaroma.

## Cài đặt — Windows

Mở PowerShell **ngay trong thư mục `ComfyUI/custom_nodes`**, rồi chạy:

```powershell
git clone https://github.com/troubleman2107/ComfyUI-Video-Folder.git
```

**Không thêm `custom_nodes/` sau lệnh trên**, vì terminal đã ở thư mục đó.
Không cần chạy pip: package không thêm dependencies, không nâng NumPy/PyTorch.

Khởi động lại ComfyUI, tải lại giao diện. Nhấp đúp canvas, tìm
**Load Videos from Folder (Batch)** trong nhóm `video/batch`.

Cấu trúc đúng:

```text
ComfyUI/
  custom_nodes/
    ComfyUI-Video-Folder/
      __init__.py
      video_folder.py
```

**macOS/Linux:** chạy cùng lệnh git clone từ `ComfyUI/custom_nodes`.

**Cài bằng ZIP:** tải Code → Download ZIP, giải nén và đổi tên
`ComfyUI-Video-Folder-main` thành `ComfyUI-Video-Folder`, đặt trực tiếp trong
`custom_nodes` rồi restart.

**Yêu cầu:** Python 3.10+ và ComfyUI có các node native **Load Video**, **Get Video
Components**, **Create Video**, **Save Video**. Nếu thiếu native VIDEO API, cập nhật
ComfyUI bằng cách cập nhật phù hợp với bộ cài bạn đang dùng. Không cài thêm NumPy,
PyTorch hay OpenCV chỉ để cài node này. `requirements.txt` chỉ chứa chú thích.

## Dùng nhanh

1. Thêm **Load Videos from Folder (Batch)**.
2. Điền `folder`, ví dụ `D:\Videos\Input`. Đây là đường dẫn trên **máy chạy
   ComfyUI**, không phải máy chỉ mở trình duyệt. Đường dẫn tương đối được tính
   từ `ComfyUI/input`; dùng đường dẫn tuyệt đối để dễ kiểm tra.
3. Đặt `batch_size = 3` để lấy ba video, hoặc `0` để lấy toàn bộ video còn lại.
4. Nối cổng `video` đến node nhận `VIDEO`. Mỗi video là một phần tử riêng,
   không bị nối thành một phim dài.
5. Để Queue batch count ở **1**, nhấn Run.

Ví dụ thư mục có `clip1.mp4`, `clip2.mp4`, `clip10.mp4`:

- `start_index=0`, `batch_size=2` → clip1 và clip2.
- `start_index=2`, `batch_size=2` → clip10.
- `start_index=0`, `batch_size=0` → cả ba video.

`start_index` không tự tăng. Với `skip_done` bật, để start_index=0 và chạy lại
sau khi các kết quả đã lưu; node chọn các file chưa có kết quả.

## Các tùy chọn

| Input | Chức năng |
|---|---|
| `folder` | Thư mục video cục bộ; có thể dán đường dẫn Windows có dấu cách |
| `recursive` | Đọc thêm thư mục con; không đi theo symlink thư mục |
| `sort_by` | `name`: thứ tự tự nhiên; `modified`: thời gian sửa file |
| `descending` | Đảo thứ tự sắp xếp |
| `start_index` | Bỏ qua N video đầu trong danh sách đã lọc, bắt đầu từ 0 |
| `batch_size` | Số **file video** trong lượt chạy; 0 = tất cả còn lại; mặc định 1 |
| `selected_files` | Tùy chọn: mỗi dòng một tên file tương đối, theo đúng thứ tự muốn chạy |
| `skip_done` | Bỏ qua video đã có kết quả, trước khi áp dụng start_index/batch_size |
| `output_folder` | Khi skip_done bật: đường dẫn tuyệt đối đến thư mục kết quả của Save Video |

Ví dụ `selected_files`:

```text
clip2.mp4
subfolder/clip10.mov
clip1.mp4
```

Bật recursive nếu chọn file trong thư mục con. Khi selected_files có nội dung,
node dùng thứ tự các dòng và bỏ tên lặp; sort_by/descending không áp dụng.
Không chọn file nằm ngoài folder.

## Các cổng ra

Tất cả cổng xuất danh sách cùng độ dài để các giá trị luôn đi đúng video:

| Output | Ý nghĩa |
|---|---|
| `video` | VIDEO native, mang theo video/âm thanh/FPS nguồn |
| `filename` | Prefix an toàn để nối vào filename_prefix của Save Video |
| `path` | Đường dẫn đầy đủ; có thể nối vào input đường dẫn của node khác |
| `index` | Chỉ số 1-based trong danh sách sau chọn/lọc, có tính start_index |
| `total` | Số video trong batch hiện tại, lặp cho từng phần tử |
| `available` | Số video sau chọn/lọc/bỏ qua kết quả, trước khi cắt batch |

`filename` giữ thư mục con và thêm phần mở rộng nguồn để tránh trùng tên:
`sub/clip.mp4 → sub/clip__mp4`; `clip.mov → clip__mov`.
Giữ nguyên chữ hoa/thường của tên và đuôi nguồn; `clip.MP4 → clip__MP4`.
Ký tự không dùng được trong đường dẫn xuất được thay thế và thêm mã ngắn
để phân biệt tên. Đây là **prefix**, Save Video vẫn thêm bộ đếm của ComfyUI.

## Workflow mẫu

Kéo các file JSON trong `examples` vào canvas. Thư mục để trống để bạn nhập lại.

### 1. Kiểm tra tải/lưu: folder_to_save_video.json

```text
Load Videos from Folder.video ─────→ Save Video.video
Load Videos from Folder.filename ─→ Save Video.filename_prefix
```

Không cần node watermark. Kết quả lưu trong `ComfyUI/output`, mang prefix nguồn.
Nếu nối thủ công, nhấp phải Save Video và chuyển filename_prefix thành input.

### 2. Đóng watermark hàng loạt: folder_watermark.json

Cài thêm [ComfyUI-Watermask](https://github.com/troubleman2107/ComfyUI-Watermask)
để có **Text Watermark (Image & Video)**:

```text
Load Videos from Folder.video → Get Video Components
                                  ├─ images → Text Watermark → Create Video.images
                                  ├─ audio ──────────────────→ Create Video.audio
                                  └─ fps ────────────────────→ Create Video.fps
                                                               ↓
Load Videos from Folder.filename ───────────────────────────→ Save Video.filename_prefix
Create Video.VIDEO ─────────────────────────────────────────→ Save Video.video
```

Ảnh/frame, audio và FPS của từng video được xử lý theo cùng vị trí trong danh sách.
Giữ các nhánh audio/fps trong workflow mẫu để tránh mất tiếng hoặc sai tốc độ.
Workflow watermark này dành cho SDR. Nó không tự quản lý chuyển màu HDR.

### Với VideoHelperSuite (VHS)

Cổng `VIDEO` native không nối trực tiếp vào `IMAGE` của VHS. Có hai cách:

- Dùng Get Video Components lấy images/audio/fps rồi nối vào các node nhận tương ứng.
- Nối `path` vào cổng đường dẫn của Load Video (Path) VHS. Chuyển widget đường dẫn
  sang input nếu cần. Bản VHS khác nhau có thể đặt tên input khác nhau.

## Bỏ qua video đã xử lý

Bật `skip_done`, nhập `output_folder` đúng thư mục Save Video đang xuất.
Với workflow mẫu, đó là đường dẫn tuyệt đối đến `ComfyUI/output`.
Cổng `filename` phải nối vào Save Video.filename_prefix như mẫu.

Node kiểm tra file video không rỗng có tên `prefix_00001_.mp4` (hoặc bộ đếm,
đuôi video khác), hoặc tên chính xác `prefix.mp4`. Không đánh dấu đã xử lý chỉ
vì có file `.txt`, file rỗng hoặc tên chỉ gần giống. Với thư mục con, nó kiểm tra
đúng thư mục con tương ứng. Giữ thư mục nguồn và kết quả riêng biệt.

Nếu thay nội dung video nguồn hoặc thay watermark và muốn xuất lại, tắt skip_done.
Chế độ này nhận diện bằng tên kết quả, không xác minh nội dung hoặc độ hoàn chỉnh
của file đã lưu. Nếu tất cả đã xử lý, node báo rõ và dừng, không tạo đầu ra rỗng.

## Giới hạn và cách xử lý lỗi

- **Batch theo file**, không phải cắt một video dài thành từng nhóm frame.
- Node chỉ tạo tham chiếu VIDEO và đọc kích thước để kiểm tra file. Tuy nhiên,
  ComfyUI có thể giữ toàn bộ các batch frame ở node giải mã phía sau. Không đảm bảo
  hoàn tất toàn bộ workflow của video 1 trước khi giải mã video 2. Với video dài,
  dùng batch_size=1 hoặc chia batch khung hình bằng công cụ chuyên dụng như VHS.
- Node không có vòng lặp tự queue; không có giao diện xem trước/chọn thumbnail.
- Hỗ trợ lọc MP4, MOV, MKV, WEBM, AVI, M4V, MPEG, MPG, TS, MTS, M2TS, WMV, FLV.
  Có đọc được codec cụ thể hay không phụ thuộc bộ giải mã trong ComfyUI.
- Video lỗi sẽ báo tên file và dừng; kiểm tra kích thước không đảm bảo mọi frame
  giải mã được. Có thể dùng selected_files để loại file hỏng khỏi lượt chạy.
- Không nhận URL, UNC/network path hoặc symlink thoát thư mục nguồn.
- Thư mục quá lớn (hơn 100.000 file được duyệt) cần chia nhỏ.
- Nếu Run lại mà không thay dữ liệu, ComfyUI có thể dùng cache. Thêm/xóa file,
  thay kích thước/thời gian sửa của video trong batch, hoặc thay kết quả skip_done
  sẽ thay dấu nhận diện cache tương ứng.

## Cập nhật

Từ thư mục `ComfyUI/custom_nodes`:

```powershell
git -C .\ComfyUI-Video-Folder pull --ff-only
```

Khởi động lại ComfyUI và tải lại trang.

## Kiểm thử

Không cần cài ComfyUI, torch hay NumPy để chạy bộ test chọn file:

```bash
python -m pip install pytest
python -m pytest -q
```

Test dùng filesystem thật cho lựa chọn, batch, cache, tên đầu ra và skip_done.
Riêng ranh giới factory VIDEO được thay bằng lớp kiểm thử tối thiểu vì bộ test
không chạy server ComfyUI. Xem [chi tiết xác minh](docs/VALIDATION.md).

Tài liệu API: [ComfyUI list processing](https://docs.comfy.org/custom-nodes/backend/lists),
[native video nodes](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_video.py).
