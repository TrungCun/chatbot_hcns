"""
Campaign Routes - Các endpoint API cho quản lý chiến dịch tuyển dụng
"""

from flask import Blueprint
from src.views.recruitment.campaign_view import CampaignView

# Tạo blueprint
campaign_bp = Blueprint("campaigns", __name__, url_prefix="/api/recruitment/campaigns")


# GET - danh sách chiến dịch
@campaign_bp.route("", methods=["GET"])
def get_campaigns():
    """GET /api/recruitment/campaigns"""
    return CampaignView.get_campaign_list()


# GET - chi tiết một chiến dịch
@campaign_bp.route("/<int:campaign_id>", methods=["GET"])
def get_campaign(campaign_id):
    """GET /api/recruitment/campaigns/<id>"""
    return CampaignView.get_campaign_detail(campaign_id)
