from sqlalchemy import text
from app.tools.mysql import get_mysql_engine
from app.log import get_logger

logger = get_logger(__name__)

def get_active_jobs():
    try:
        engine = get_mysql_engine()
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    rr.jobtitle_id,
                    sq.id AS staffing_quota_id,
                    sq.quota_number AS total_quota,
                    rc.id AS campaign_id,
                    rc.name AS position_name, 
                    rr.quantity AS number_of_positions_to_hire, 
                    rr.experience_level AS min_experience_years, 
                    rr.education_level AS education_requirement, 
                    rc.jd_salary_range AS salary_range, 
                    rc.jd_benefits AS benefits, 
                    GROUP_CONCAT(rcr.round_name ORDER BY rcr.round_number ASC SEPARATOR '; ') AS interview_rounds
                FROM recruitment_campaigns rc
                JOIN recruitment_requests rr ON rc.request_id = rr.id
                LEFT JOIN staffing_quota sq ON rr.department_id = sq.department_id AND rr.jobtitle_id = sq.jobtitle_id
                LEFT JOIN recruitment_campaign_rounds rcr ON rc.id = rcr.campaign_id
                WHERE rc.status = 1 
                AND (rc.end_time IS NULL OR rc.end_time >= UNIX_TIMESTAMP())
                GROUP BY 
                    rr.jobtitle_id,
                    sq.id,
                    sq.quota_number,
                    rc.id, 
                    rc.name, 
                    rr.quantity, 
                    rr.experience_level, 
                    rr.education_level, 
                    rc.jd_salary_range, 
                    rc.jd_benefits
                ORDER BY rc.name;
            """)
            result = conn.execute(query).mappings().fetchall()
            return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
        return []
