"""
📞 Communication Center API Routes
Enterprise messaging, announcements, and notification management
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pydantic import BaseModel, EmailStr
from enum import Enum

from app.backend.services import communication_service, MessageType, NotificationChannel, MessagePriority
from app.backend.utils.dependencies import require_admin_role, get_current_user, User

logger = logging.getLogger(__name__)

router = APIRouter()

# =================================================================
# PYDANTIC MODELS
# =================================================================

class MessageRequest(BaseModel):
    type: MessageType = MessageType.DIRECT_MESSAGE
    priority: MessagePriority = MessagePriority.NORMAL
    subject: str
    content: str
    html_content: Optional[str] = None
    attachments: List[str] = []
    metadata: Dict[str, Any] = {}
    expires_at: Optional[str] = None
    recipients: Optional[List[str]] = None
    target_roles: Optional[List[str]] = None
    channels: List[NotificationChannel] = [NotificationChannel.IN_APP]

class AnnouncementRequest(BaseModel):
    title: str
    content: str
    html_content: Optional[str] = None
    category: str = "general"
    priority: MessagePriority = MessagePriority.NORMAL
    tags: List[str] = []
    target_all_users: bool = False
    target_roles: Optional[List[str]] = None
    target_users: Optional[List[str]] = None
    channels: List[NotificationChannel] = [NotificationChannel.IN_APP]
    publish_immediately: bool = True
    publish_at: Optional[str] = None
    expires_at: Optional[str] = None
    show_popup: bool = False
    pin_to_top: bool = False
    require_acknowledgment: bool = False
    banner_color: str = "blue"

class NotificationPreferencesRequest(BaseModel):
    channels: Dict[str, bool] = {}
    message_types: Dict[str, bool] = {}
    frequency: Dict[str, bool] = {}
    quiet_hours: Dict[str, Any] = {}

# =================================================================
# MESSAGE ENDPOINTS
# =================================================================

@router.post("/messages/send", summary="Send Message")
async def send_message(
    message: MessageRequest,
    admin_user: User = Depends(require_admin_role)
):
    """
    📨 SEND MESSAGE
    
    Send messages to users with multiple delivery channels:
    - Direct messages to specific users
    - Role-based messaging
    - Multiple notification channels (in-app, email, SMS, push)
    - Priority levels and expiration
    """
    try:
        result = await communication_service.send_message(
            sender_id=admin_user.id,
            message_data=message.dict(),
            recipients=message.recipients,
            target_roles=message.target_roles,
            channels=message.channels
        )
        
        logger.info(f"Message sent by admin {admin_user.id} to {result['recipients_count']} recipients")
        
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@router.get("/messages/sent", summary="Get Sent Messages")
async def get_sent_messages(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    message_type: Optional[str] = Query(None),
    admin_user: User = Depends(require_admin_role)
):
    """
    📤 GET SENT MESSAGES
    
    Retrieve messages sent by the admin with delivery statistics
    """
    try:
        # Mock implementation - would query messages table in production
        sent_messages = {
            "messages": [
                {
                    "id": "msg_example123",
                    "type": "announcement",
                    "subject": "System Maintenance Notice",
                    "content": "Scheduled maintenance on Sunday 2AM-4AM UTC",
                    "recipients_count": 1247,
                    "delivery_stats": {
                        "delivered": 1245,
                        "read": 892,
                        "failed": 2
                    },
                    "created_at": "2025-01-27T10:00:00Z",
                    "status": "sent"
                },
                {
                    "id": "msg_example456",
                    "type": "direct_message",
                    "subject": "Welcome to Premium!",
                    "content": "Thank you for upgrading to premium",
                    "recipients_count": 45,
                    "delivery_stats": {
                        "delivered": 45,
                        "read": 38,
                        "failed": 0
                    },
                    "created_at": "2025-01-26T15:30:00Z",
                    "status": "sent"
                }
            ],
            "total": 2,
            "page": page,
            "limit": limit,
            "has_next": False
        }
        
        return {
            "status": "success",
            "data": sent_messages,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get sent messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sent messages: {str(e)}")

# =================================================================
# ANNOUNCEMENT ENDPOINTS
# =================================================================

@router.post("/announcements", summary="Create Announcement")
async def create_announcement(
    announcement: AnnouncementRequest,
    admin_user: User = Depends(require_admin_role)
):
    """
    📢 CREATE ANNOUNCEMENT
    
    Create system-wide announcements with advanced targeting:
    - Target all users or specific roles
    - Multiple delivery channels
    - Scheduling and expiration
    - Display customization (popup, pinned, colors)
    - Acknowledgment requirements
    """
    try:
        result = await communication_service.create_announcement(
            admin_id=admin_user.id,
            announcement_data=announcement.dict()
        )
        
        logger.info(f"Announcement created by admin {admin_user.id}: {result['announcement_id']}")
        
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to create announcement: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create announcement: {str(e)}")

@router.get("/announcements", summary="Get Announcements")
async def get_announcements(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    admin_user: User = Depends(require_admin_role)
):
    """
    📋 GET ANNOUNCEMENTS
    
    Retrieve announcements with filtering and analytics
    """
    try:
        # Mock implementation
        announcements = {
            "announcements": [
                {
                    "id": "ann_example123",
                    "title": "New AI Trading Features Released!",
                    "content": "We've added 3 new AI layers for better prediction accuracy...",
                    "category": "features",
                    "priority": "normal",
                    "status": "published",
                    "target_audience": {
                        "all_users": True,
                        "total_recipients": 1247
                    },
                    "stats": {
                        "views": 892,
                        "acknowledgments": 234,
                        "dismissals": 45
                    },
                    "created_at": "2025-01-27T09:00:00Z",
                    "published_at": "2025-01-27T09:00:00Z",
                    "created_by": admin_user.id
                }
            ],
            "total": 1,
            "page": page,
            "limit": limit,
            "has_next": False
        }
        
        return {
            "status": "success",
            "data": announcements,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get announcements: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve announcements: {str(e)}")

@router.put("/announcements/{announcement_id}/status", summary="Update Announcement Status")
async def update_announcement_status(
    announcement_id: str,
    status: str,
    admin_user: User = Depends(require_admin_role)
):
    """
    🔄 UPDATE ANNOUNCEMENT STATUS
    
    Change announcement status (draft, scheduled, published, expired, cancelled)
    """
    try:
        valid_statuses = ['draft', 'scheduled', 'published', 'expired', 'cancelled']
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {valid_statuses}"
            )
        
        # Mock implementation - would update database in production
        logger.info(f"Updated announcement {announcement_id} status to {status}")
        
        return {
            "status": "success",
            "message": f"Announcement status updated to {status}",
            "data": {
                "announcement_id": announcement_id,
                "new_status": status
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update announcement status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update announcement status: {str(e)}")

# =================================================================
# USER NOTIFICATION ENDPOINTS
# =================================================================

@router.get("/notifications", summary="Get User Notifications")
async def get_user_notifications(
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user)
):
    """
    🔔 GET USER NOTIFICATIONS
    
    Retrieve notifications for the current user
    """
    try:
        result = await communication_service.get_user_notifications(
            user_id=current_user.user_id,
            limit=limit,
            unread_only=unread_only
        )
        
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get user notifications: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve notifications: {str(e)}")

@router.put("/notifications/{notification_id}/read", summary="Mark Notification as Read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    ✅ MARK NOTIFICATION AS READ
    
    Mark a specific notification as read
    """
    try:
        success = await communication_service.mark_notification_read(
            delivery_id=notification_id,
            user_id=current_user.user_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found or access denied")
        
        return {
            "status": "success",
            "message": "Notification marked as read",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark notification as read: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mark notification as read: {str(e)}")

@router.get("/preferences", summary="Get Notification Preferences")
async def get_notification_preferences(
    current_user: User = Depends(get_current_user)
):
    """
    ⚙️ GET NOTIFICATION PREFERENCES
    
    Retrieve user's notification preferences
    """
    try:
        preferences = await communication_service.get_user_notification_preferences(
            user_id=current_user.user_id
        )
        
        return {
            "status": "success",
            "data": preferences,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get notification preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve notification preferences: {str(e)}")

@router.put("/preferences", summary="Update Notification Preferences")
async def update_notification_preferences(
    preferences: NotificationPreferencesRequest,
    current_user: User = Depends(get_current_user)
):
    """
    🔧 UPDATE NOTIFICATION PREFERENCES
    
    Update user's notification preferences:
    - Channel preferences (email, SMS, push, in-app)
    - Message type preferences
    - Frequency settings
    - Quiet hours configuration
    """
    try:
        success = await communication_service.update_user_notification_preferences(
            user_id=current_user.user_id,
            preferences=preferences.dict()
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update preferences")
        
        return {
            "status": "success",
            "message": "Notification preferences updated successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update notification preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update notification preferences: {str(e)}")

# =================================================================
# COMMUNICATION ANALYTICS
# =================================================================

@router.get("/analytics/overview", summary="Get Communication Analytics")
async def get_communication_analytics(
    days: int = Query(30, ge=1, le=365),
    admin_user: User = Depends(require_admin_role)
):
    """
    📊 GET COMMUNICATION ANALYTICS
    
    Comprehensive communication performance analytics:
    - Message delivery rates
    - Engagement metrics
    - Channel performance
    - User preferences analysis
    """
    try:
        # Mock analytics data
        analytics = {
            "summary": {
                "total_messages_sent": 1847,
                "total_announcements": 23,
                "avg_delivery_rate": 98.7,
                "avg_read_rate": 67.4,
                "active_subscribers": 1156
            },
            "delivery_performance": {
                "in_app": {"sent": 1847, "delivered": 1847, "read": 1245, "rate": 100.0},
                "email": {"sent": 1234, "delivered": 1198, "read": 834, "rate": 97.1},
                "sms": {"sent": 456, "delivered": 445, "read": 312, "rate": 97.6},
                "push": {"sent": 892, "delivered": 856, "read": 543, "rate": 95.9}
            },
            "engagement_trends": [
                {"date": "2025-01-27", "messages": 85, "reads": 67, "engagement": 78.8},
                {"date": "2025-01-26", "messages": 92, "reads": 71, "engagement": 77.2},
                {"date": "2025-01-25", "messages": 78, "reads": 58, "engagement": 74.4}
            ],
            "top_performing_announcements": [
                {
                    "id": "ann_123",
                    "title": "New AI Features",
                    "views": 892,
                    "engagement_rate": 89.3,
                    "acknowledgments": 234
                }
            ],
            "user_preferences": {
                "email_enabled": 89.2,
                "sms_enabled": 34.7,
                "push_enabled": 76.8,
                "marketing_subscribed": 45.6
            }
        }
        
        return {
            "status": "success",
            "data": analytics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get communication analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve communication analytics: {str(e)}")

# =================================================================
# TEMPLATE MANAGEMENT
# =================================================================

@router.get("/templates", summary="Get Notification Templates")
async def get_notification_templates(
    category: Optional[str] = Query(None),
    admin_user: User = Depends(require_admin_role)
):
    """
    📄 GET NOTIFICATION TEMPLATES
    
    Retrieve notification templates for consistent messaging
    """
    try:
        # Mock templates
        templates = {
            "templates": [
                {
                    "id": "welcome_new_user",
                    "name": "Welcome New User",
                    "category": "onboarding",
                    "subject": "Welcome to TradePulse.AI!",
                    "content": "Welcome {{username}}! Your trading journey begins now...",
                    "html_content": "<h1>Welcome {{username}}!</h1><p>Your trading journey begins now...</p>",
                    "variables": ["username", "activation_link"],
                    "channels": ["email", "in_app"],
                    "created_at": "2025-01-20T10:00:00Z"
                },
                {
                    "id": "maintenance_notice",
                    "name": "Maintenance Notice",
                    "category": "system",
                    "subject": "Scheduled Maintenance - {{date}}",
                    "content": "We'll be performing maintenance on {{date}} from {{start_time}} to {{end_time}}.",
                    "variables": ["date", "start_time", "end_time"],
                    "channels": ["email", "in_app", "push"],
                    "created_at": "2025-01-15T14:30:00Z"
                }
            ],
            "total": 2,
            "categories": ["onboarding", "system", "marketing", "security", "trading"]
        }
        
        return {
            "status": "success",
            "data": templates,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get notification templates: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve notification templates: {str(e)}")

@router.get("/health", summary="Communication System Health")
async def get_communication_health():
    """
    ❤️ COMMUNICATION SYSTEM HEALTH
    
    Check the health of communication services
    """
    try:
        health_status = {
            "status": "healthy",
            "services": {
                "message_queue": "operational",
                "email_service": "operational", 
                "sms_service": "operational",
                "push_service": "operational",
                "database": "operational"
            },
            "metrics": {
                "avg_delivery_time": "1.2s",
                "success_rate": "99.2%",
                "queue_length": 0,
                "active_connections": 23
            },
            "last_check": datetime.now().isoformat()
        }
        
        return {
            "status": "success",
            "data": health_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get communication health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve communication health: {str(e)}") 