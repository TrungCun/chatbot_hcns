from flask import request, jsonify
from sqlalchemy import desc, func
from src.extensions import db
from src.models.recruitment.recruitment_campaign import (
    RecruitmentCampaign,
    RecruitmentCandidateCampaign,
    RecruitmentRequest,
)
from src.models.recruitment.models import Department
from datetime import datetime

VALID_EXPERIENCE_LEVELS = {0, 1, 2, 3, 4, 5}
VALID_EDUCATION_LEVELS = {1, 2, 3, 4, 5, 6}


class CampaignView:
    """API views for Recruitment Campaigns"""

    @staticmethod
    def get_campaign_list():
        """
        GET /api/recruitment/campaigns
        Lấy danh sách chiến dịch tuyển dụng với phân trang

        Query params:
        - page_num (int): Số trang (default: 1)
        - page_size (int): Số bản ghi/trang (default: 10)
        - name (str): Tìm kiếm theo tên chiến dịch
        - status (int): Lọc theo trạng thái (1=ongoing, 2=paused, 3=cancelled, 4=completed)
        - experience (int): Lọc theo mức kinh nghiệm (0-5)
        - education_filter (int): Lọc theo trình độ học vấn (1-6)
        - sort_by (str): Sắp xếp theo trường (created_at, updated_at, name)
        - sort_order (str): Thứ tự (asc, desc) - default: desc
        """
        try:
            session = db.session()
            page_num = request.args.get("page_num", 1, type=int)
            page_size = request.args.get("page_size", 10, type=int)
            name = request.args.get("name", "", type=str)
            status = request.args.get("status", None, type=int)
            experience_level = request.args.get("experience", None, type=int)
            education_level = request.args.get("education_filter", None, type=int)
            sort_by = request.args.get("sort_by", "created_at", type=str)
            sort_order = request.args.get("sort_order", "desc", type=str)

            # Validate pagination
            if page_num < 1:
                page_num = 1
            if page_size < 1 or page_size > 100:
                page_size = 10

            if experience_level not in VALID_EXPERIENCE_LEVELS:
                experience_level = None
            if education_level not in VALID_EDUCATION_LEVELS:
                education_level = None

            needs_request_join = experience_level is not None or education_level is not None

            # Base query
            query = session.query(RecruitmentCampaign)

            if needs_request_join:
                query = query.join(
                    RecruitmentRequest,
                    RecruitmentCampaign.request_id == RecruitmentRequest.id,
                )

            # Luôn chỉ trả về bản ghi có status = 1
            query = query.filter(RecruitmentCampaign.status == 1)
            # Filter by name
            if name:
                query = query.filter(RecruitmentCampaign.name.ilike(f"%{name}%"))

            # Filter by status
            # if status:
            #     query = query.filter(RecruitmentCampaign.status == status)

            if experience_level is not None:
                query = query.filter(
                    RecruitmentRequest.experience_level == experience_level
                )

            if education_level is not None:
                query = query.filter(
                    RecruitmentRequest.education_level == education_level
                )

            # Count total
            total = query.count()

            # Sort
            if sort_by == "updated_at":
                sort_col = RecruitmentCampaign.updated_at
            elif sort_by == "name":
                sort_col = RecruitmentCampaign.name
            else:
                sort_col = RecruitmentCampaign.created_at

            if sort_order.lower() == "asc":
                query = query.order_by(sort_col.asc())
            else:
                query = query.order_by(sort_col.desc())

            # Pagination
            offset = (page_num - 1) * page_size
            campaigns = query.offset(offset).limit(page_size).all()

            # Format response
            campaign_list = []
            for campaign in campaigns:
                request_row = (
                    session.query(
                        RecruitmentRequest.experience_level,
                        RecruitmentRequest.education_level,
                        RecruitmentRequest.department_id,
                        Department.name.label("department_name"),
                    )
                    .outerjoin(
                        Department,
                        RecruitmentRequest.department_id == Department.id,
                    )
                    .filter(RecruitmentRequest.id == campaign.request_id)
                    .first()
                )

                campaign_data = campaign.to_dict()

                if request_row:
                    campaign_data["experience_level"] = request_row.experience_level
                    campaign_data["education_level"] = request_row.education_level
                    campaign_data["department_id"] = request_row.department_id
                    campaign_data["department_name"] = request_row.department_name

                campaign_list.append(campaign_data)

            session.close()

            return (
                jsonify(
                    {
                        "success": True,
                        "data": campaign_list,
                        "pagination": {
                            "page_num": page_num,
                            "page_size": page_size,
                            "total": total,
                            "total_pages": (total + page_size - 1) // page_size,
                        },
                    }
                ),
                200,
            )

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @staticmethod
    def get_campaign_detail(campaign_id):
        """
        GET /api/recruitment/campaigns/<id>
        Lấy chi tiết một chiến dịch tuyển dụng
        """
        try:
            session = db.session()
            campaign = (
                session.query(RecruitmentCampaign)
                .filter(RecruitmentCampaign.id == campaign_id)
                .first()
            )

            if not campaign:
                return jsonify({"success": False, "error": "Campaign not found"}), 404

            # Get campaign details
            campaign_data = campaign.to_dict()

            cc_stats = (
                session.query(
                    RecruitmentCandidateCampaign.status,
                    func.count(RecruitmentCandidateCampaign.id).label("count"),
                )
                .filter(RecruitmentCandidateCampaign.campaign_id == campaign_id)
                .group_by(RecruitmentCandidateCampaign.status)
                .all()
            )

            campaign_data["application_stats"] = {
                stat[0]: stat[1] for stat in cc_stats
            }

            # Get recruitment request info
            request_info = (
                session.query(RecruitmentRequest)
                .filter(RecruitmentRequest.id == campaign.request_id)
                .first()
            )

            if request_info:
                campaign_data["request_info"] = {
                    "id": request_info.id,
                    "name": request_info.name,
                    "quantity": request_info.quantity,
                    "salary_range": request_info.salary_range,
                }

            session.close()

            return jsonify({"success": True, "data": campaign_data}), 200

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
