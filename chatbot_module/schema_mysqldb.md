# Database Schema: Quản lý Tuyển dụng & Định biên (ATS)

Tài liệu này mô tả chi tiết cấu trúc cơ sở dữ liệu (đã được chuẩn hóa và sửa các lỗi typo nhỏ từ bản nháp gốc) để phục vụ cho việc thao tác và truy vấn sau này.

## 1. Domain: Định biên nhân sự (Staffing Quota)

### `staffing_quota`
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `department_id` | INT | FK | Phòng ban |
| `jobtitle_id` | INT | FK | Chức vụ |
| `quota_number` | INT | Not Null | Số lượng định biên |
| `status` | INT | Default=2 | Trạng thái |
| `created_by` | INT | | Người tạo |
| `created_at` | BIGINT | | Thời gian tạo |
| `deleted_at` | BIGINT | | Thời gian xóa |

### `staffing_quota_change_requests`
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `quota_id` | INT | FK | Khóa ngoại đến Định biên |
| `old_quota_number` | INT | | Định biên cũ |
| `new_quota_number` | INT | | Định biên mới |
| `requested_by` | INT | | Người yêu cầu |
| `approved_by` | INT | | Người duyệt |
| `status` | INT | Default=1 | Trạng thái (1=PENDING, 2=APPROVED, 3=REJECTED) |
| `reason` | TEXT | | Lý do thay đổi |
| `related_recruitment_request_id` | INT | | Liên kết Đề xuất tuyển dụng (nếu có) |
| `created_at` | BIGINT | | Thời gian tạo |

### `staffing_quota_audit_logs`
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `quota_id` | INT | FK | Khóa ngoại đến Định biên |
| `action_type` | VARCHAR(100) | | Loại hành động |
| `performed_by` | INT | | Người thực hiện |
| `performed_at` | BIGINT | | Thời gian thực hiện |
| `quota_before` | JSON | | Dữ liệu định biên cũ |
| `quota_after` | JSON | | Dữ liệu định biên mới |
| `reason` | TEXT | | Lý do |
| `related_recruitment_request_id` | INT | | Liên kết Đề xuất tuyển dụng |

## 2. Domain: Kế hoạch & Yêu cầu Tuyển dụng

### `recruitment_plans`
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `plan_period_month` | INT | | Tháng lập kế hoạch |
| `plan_period_year` | INT | | Năm lập kế hoạch |
| `file_name` | VARCHAR(255)| | Tên file lưu trữ |
| `file_path` | VARCHAR(500)| | Đường dẫn file |
| `original_name` | VARCHAR(255)| | Tên file gốc |
| `note` | TEXT | | Ghi chú |
| `uploaded_by` | INT | FK | Người upload |
| `uploaded_at` | BIGINT | | Thời gian upload |

### `recruitment_requests` (Đề xuất tuyển dụng)
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `department_id` | INT | FK | Phòng ban |
| `jobtitle_id` | INT | FK | Vị trí công việc |
| `jobtitle_detail` | TEXT | | Chi tiết vị trí |
| `name` | NVARCHAR(255)| | Tên đề xuất |
| `quantity` | INT | | Số lượng cần tuyển |
| `gender` | INT | | Giới tính yêu cầu |
| `deadline` | BIGINT | | Thời hạn cần nhân sự |
| `salary_range` | NVARCHAR(255)| | Khoảng lương đề xuất |
| `need_type` | INT | | Nhu cầu tuyển (ngắn/dài hạn) |
| `replacement_type` | INT | | Loại thay thế |
| `replacement_user_id`| INT | FK | Người bị thay thế |
| `replacement_reason` | TEXT | | Lý do thay thế |
| `experience_level` | INT | | Mức kinh nghiệm |
| `education_level` | INT | | Trình độ học vấn |
| `competency_requirements`| TEXT | | Yêu cầu năng lực |
| `appearance_requirements`| TINYINT(1)| | Yêu cầu ngoại hình (Boolean) |
| `job_description` | TEXT | | Mô tả công việc |
| `recruitment_reason` | TEXT | | Lý do tuyển dụng |
| `status` | INT | | Trạng thái đề xuất |
| `status_name` | NVARCHAR(255)| | Tên trạng thái |
| `created_by` | INT | | Người tạo |
| `approved_by` | INT | | Người duyệt cuối |
| `approval_date` | BIGINT | | Thời gian duyệt |
| `rejected_reason` | TEXT | | Lý do từ chối |
| `cancelled_reason` | TEXT | | Lý do hủy |
| `created_at` | BIGINT | | Thời gian tạo |
| `updated_at` | BIGINT | | Thời gian cập nhật |

### `recruitment_request_approval_steps`
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `request_id` | INT | FK | Khóa ngoại Đề xuất TD |
| `step_order` | INT | | Thứ tự bước duyệt |
| `step_code` | VARCHAR(50) | | Mã bước duyệt |
| `position_code` | VARCHAR(50) | | Mã chức vụ người duyệt |
| `department_code` | VARCHAR(50) | | Mã phòng ban người duyệt |
| `status` | INT | | Trạng thái (1=PEND, 2=APPV, 3=REJ, 4=CANCEL) |
| `acted_by` | INT | | Người thực hiện duyệt |
| `acted_at` | BIGINT | | Thời gian thao tác |
| `rejection_reason` | TEXT | | Lý do từ chối bước này |
| `created_at` | BIGINT | | Thời gian tạo |
| `updated_at` | BIGINT | | Thời gian cập nhật |

### `recruitment_request_attachments` & `recruitment_request_questions`
- **`recruitment_request_attachments`**: `id` (PK), `request_id` (FK), `file_name` (VARCHAR), `original_name` (VARCHAR), `file_path` (VARCHAR), `uploaded_by`, `uploaded_at`. (Lưu ý: đã đổi kiểu dữ liệu các cột tên/path từ INT sang VARCHAR).
- **`recruitment_request_questions`**: `id` (PK), `request_id` (FK), `content` (TEXT), `created_at` (BIGINT).

## 3. Domain: Chiến dịch & Cấu hình Phỏng vấn

### `recruitment_campaigns`
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `request_id` | INT | FK | Khóa ngoại Đề xuất TD |
| `name` | VARCHAR(255) | | Tên chiến dịch |
| `status` | INT | | Trạng thái |
| `pause_reason` | TEXT | | Lý do tạm dừng |
| `cancel_reason` | TEXT | | Lý do hủy |
| `assignee_id` | INT | | Người phụ trách (HR) |
| `created_by` | INT | | Người tạo |
| `created_at` | BIGINT | | Thời gian tạo |
| `updated_at` | BIGINT | | Thời gian cập nhật |
| `start_time` | BIGINT | | Thời gian bắt đầu (Unix time) |
| `end_time` | BIGINT | | Thời gian kết thúc (Unix time) |
| `jd_job_description` | TEXT | | JD: Mô tả công việc |
| `jd_competency_requirements`| TEXT | | JD: Yêu cầu năng lực |
| `jd_salary_range` | VARCHAR(255)| | JD: Khoảng lương |
| `jd_benefits` | TEXT | | JD: Quyền lợi |

### `recruitment_campaign_rounds` (Cấu hình Vòng Phỏng vấn)
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `campaign_id` | INT | FK | Chiến dịch |
| `round_number` | INT | | Thứ tự vòng |
| `round_name` | VARCHAR(255) | | Tên vòng |
| `interview_questions` | TEXT | | Câu hỏi phỏng vấn chuẩn |
| `created_at` | BIGINT | | Thời gian tạo |

### `recruitment_campaign_round_interviewers`
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `campaign_round_id` | INT | FK | Khóa ngoại vòng phỏng vấn |
| `user_id` | INT | FK | Người được gán phỏng vấn |

## 4. Domain: Ứng viên (Candidates & Talent Pool)

### `recruitment_cv_sources`
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `name` | VARCHAR(255) | | Tên nguồn CV *(Đã sửa từ INT)* |
| `description` | TEXT | | Mô tả nguồn *(Đã sửa từ INT)* |
| `created_at` | BIGINT | | Thời gian tạo *(Đã sửa từ VARCHAR)* |

### `recruitment_candidates`
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `name` | NVARCHAR(100)| | Họ và tên |
| `email` | NVARCHAR(100)| | Email |
| `phone` | NVARCHAR(100)| | Số điện thoại |
| `birthday` | BIGINT | | Ngày sinh |
| `gender` | INT | | Giới tính |
| `address` | NVARCHAR(255)| | Địa chỉ |
| `education_level` | INT | | Trình độ học vấn |
| `experience_years`| INT | | Kinh nghiệm làm việc |
| `source_id` | INT | FK | Nguồn CV |
| `overall_status` | INT | Default=1 | Trạng thái chung |
| `created_at` | BIGINT | | Thời gian tạo *(Đã sửa từ create_at)* |
| `updated_at` | BIGINT | | Thời gian cập nhật |
| `description` | TEXT | | Ghi chú |

### `recruitment_candidate_cvs`
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `candidate_id` | INT | FK | Ứng viên |
| `cv_file` | NVARCHAR(255)| | Tên file lưu trên server |
| `cv_path` | NVARCHAR(500)| | Đường dẫn file |
| `original_name` | NVARCHAR(255)| | Tên file gốc |
| `is_primary` | TINYINT(1) | | Có phải CV chính không (Boolean) |
| `uploaded_by` | INT | | Người tạo |
| `uploaded_at` | BIGINT | | Thời gian tạo |
| `note` | TEXT | | Ghi chú |

## 5. Domain: Quy trình Ứng tuyển & Kết quả (Application)

### `recruitment_candidate_campaigns` (Hồ sơ ứng tuyển vào 1 Chiến dịch)
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `candidate_id` | INT | FK | Ứng viên |
| `campaign_id` | INT | FK | Chiến dịch tuyển dụng |
| `proposed_salary` | NVARCHAR(255)| | Mức lương đề xuất |
| `status` | INT | | Trạng thái ứng viên trong chiến dịch |
| `start_date` | BIGINT | | Ngày bắt đầu làm việc |
| `probation_period`| INT | | Thời gian thử việc (Tháng/Ngày) |
| `offer_approval_status`| BIGINT | | Trạng thái duyệt Offer |
| `offer_approved_by`| INT | | Người duyệt Offer |
| `offer_rejection_reason`| TEXT | | Lý do từ chối Offer |
| `is_matching` | TINYINT(1) | | Đánh giá độ phù hợp (Boolean) |
| `assigned_at` | BIGINT | | Thời gian gán vào chiến dịch |
| `assigned_by` | INT | | Người thực hiện gán |
| `updated_at` | BIGINT | | Thời gian cập nhật |

### `recruitment_candidate_status_histories`
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `candidate_id` | INT | FK | Ứng viên |
| `campaign_id` | INT | FK | Chiến dịch |
| `old_status` | INT | | Trạng thái cũ |
| `new_status` | INT | | Trạng thái mới |
| `changed_by` | INT | | Người thay đổi |
| `changed_at` | BIGINT | | Thời gian thay đổi |
| `note` | TEXT | | Ghi chú/Lý do thay đổi |

### `candidate_campaign_rounds` (Vòng phỏng vấn thực tế của Ứng viên)
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `campaign_id` | INT | FK | Chiến dịch |
| `candidate_id` | INT | FK | Ứng viên |
| `campaign_round_id`| INT | FK | Link tới cấu hình vòng (nếu có) |
| `round_number` | INT | | Thứ tự vòng phỏng vấn |
| `round_name` | VARCHAR(255) | | Tên vòng phỏng vấn |
| `interview_time` | BIGINT | | Thời gian phỏng vấn |
| `interview_format` | VARCHAR(255) | | Hình thức phỏng vấn (Online/Offline) |
| `status` | INT | | Trạng thái vòng |
| `created_at` | BIGINT | | Thời gian tạo |
| `prescreening_note`| TEXT | | Nhận xét sơ lọc |
| `prescreening_passed`| TINYINT(1) | | Đạt sơ lọc (Boolean) |
| `proposed_salary_gross`| INT | | Lương Gross đề xuất |

### `candidate_campaign_round_interviewers` (Kết quả phỏng vấn chi tiết)
| Thuộc tính | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | Khóa chính |
| `candidate_campaign_round_id`| INT | FK | Vòng phỏng vấn của ứng viên |
| `user_id` | INT | FK | Người phỏng vấn |
| `review` | TEXT | | Nhận xét chi tiết từ người PV |
| `result` | INT | | Kết quả đánh giá (Đạt/Không đạt/...) |
| `proposed_salary_gross`| INT | | Lương Gross đề xuất từ người PV |
