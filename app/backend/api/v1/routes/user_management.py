"""
🏢 Enterprise User Management API Routes
Advanced user lifecycle management with invitation system and role management
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pydantic import BaseModel, EmailStr

from app.backend.services import database_service as user_management_service
from app.backend.utils.dependencies import require_admin_role, get_current_user, User

logger = logging.getLogger(__name__)

router = APIRouter()

# =================================================================
# PYDANTIC MODELS
# =================================================================

class UserFilters(BaseModel):
    search: Optional[str] = None
    status: Optional[str] = None
    role: Optional[str] = None
    subscription_type: Optional[str] = None

class InvitationRequest(BaseModel):
    email: EmailStr
    role: str = 'user'
    custom_message: Optional[str] = None
    expires_in_days: int = 7

class BulkInvitationRequest(BaseModel):
    emails: List[EmailStr]
    role: str = 'user'
    custom_message: Optional[str] = None
    expires_in_days: int = 7

class UserStatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = None

class UserRoleUpdate(BaseModel):
    role: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    status: str
    subscription_type: str
    created_at: str
    last_login: str
    portfolio_value: float
    total_trades: int
    total_profit_loss: float

# =================================================================
# USER MANAGEMENT ENDPOINTS
# =================================================================

@router.get("/users", summary="Get Users with Filtering")
async def get_users(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query('created_at'),
    sort_order: str = Query('desc'),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    subscription_type: Optional[str] = Query(None),
    admin_user: User = Depends(require_admin_role)
):
    """
    🔍 GET USERS WITH ADVANCED FILTERING
    
    Retrieve paginated user list with comprehensive search and filtering capabilities:
    - Search across username and email
    - Filter by status, role, subscription type
    - Sort by multiple fields
    - Pagination support
    """
    try:
        filters = {}
        if search:
            filters['search'] = search
        if status:
            filters['status'] = status
        if role:
            filters['role'] = role
        if subscription_type:
            filters['subscription_type'] = subscription_type
        
        result = await user_management_service.get_users(
            filters=filters,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        logger.info(f"Retrieved {len(result.get('users', []))} users for admin {admin_user.id}")
        
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve users: {str(e)}")

@router.get("/users/{user_id}", summary="Get User Details")
async def get_user_details(
    user_id: str,
    admin_user: User = Depends(require_admin_role)
):
    """
    👤 GET DETAILED USER INFORMATION
    
    Retrieve comprehensive user details including:
    - Profile information
    - Trading permissions
    - Activity history
    - Subscription details
    """
    try:
        user = await user_management_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        logger.info(f"Retrieved user details for {user_id} by admin {admin_user.id}")
        
        return {
            "status": "success",
            "data": user,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user details: {str(e)}")

@router.put("/users/{user_id}/status", summary="Update User Status")
async def update_user_status(
    user_id: str,
    status_update: UserStatusUpdate,
    admin_user: User = Depends(require_admin_role)
):
    """
    🔄 UPDATE USER STATUS
    
    Change user status with audit trail:
    - active: User can access all features
    - suspended: Temporary access restriction
    - banned: Permanent access restriction
    - pending: Awaiting verification
    """
    try:
        # Validate status
        valid_statuses = ['active', 'suspended', 'banned', 'pending']
        if status_update.status not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {valid_statuses}"
            )
        
        success = await user_management_service.update_user_status(
            user_id=user_id,
            new_status=status_update.status,
            reason=status_update.reason,
            admin_id=admin_user.id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update user status")
        
        logger.info(f"Updated user {user_id} status to {status_update.status} by admin {admin_user.id}")
        
        return {
            "status": "success",
            "message": f"User status updated to {status_update.status}",
            "data": {
                "user_id": user_id,
                "new_status": status_update.status,
                "reason": status_update.reason
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update user status: {str(e)}")

@router.put("/users/{user_id}/role", summary="Update User Role")
async def update_user_role(
    user_id: str,
    role_update: UserRoleUpdate,
    admin_user: User = Depends(require_admin_role)
):
    """
    🔐 UPDATE USER ROLE
    
    Change user role and permissions:
    - user: Basic access to virtual trading
    - premium: Access to live trading features
    - admin: Full system access
    """
    try:
        # Validate role
        valid_roles = ['user', 'premium', 'admin']
        if role_update.role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {valid_roles}"
            )
        
        success = await user_management_service.update_user_role(
            user_id=user_id,
            new_role=role_update.role,
            admin_id=admin_user.id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update user role")
        
        logger.info(f"Updated user {user_id} role to {role_update.role} by admin {admin_user.id}")
        
        return {
            "status": "success",
            "message": f"User role updated to {role_update.role}",
            "data": {
                "user_id": user_id,
                "new_role": role_update.role
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user role: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update user role: {str(e)}")

# =================================================================
# INVITATION MANAGEMENT ENDPOINTS
# =================================================================

@router.post("/invitations", summary="Send User Invitation")
async def send_invitation(
    invitation: InvitationRequest,
    admin_user: User = Depends(require_admin_role)
):
    """
    📧 SEND USER INVITATION
    
    Send invitation email to new user with:
    - Custom welcome message
    - Role pre-assignment
    - Expiration date
    - Tracking capabilities
    """
    try:
        # Validate role
        valid_roles = ['user', 'premium', 'admin']
        if invitation.role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {valid_roles}"
            )
        
        result = await user_management_service.send_invitation(
            email=invitation.email,
            role=invitation.role,
            invited_by=admin_user.id,
            custom_message=invitation.custom_message,
            expires_in_days=invitation.expires_in_days
        )
        
        logger.info(f"Sent invitation to {invitation.email} by admin {admin_user.id}")
        
        return {
            "status": "success",
            "message": f"Invitation sent to {invitation.email}",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send invitation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send invitation: {str(e)}")

@router.post("/invitations/bulk", summary="Send Bulk Invitations")
async def send_bulk_invitations(
    bulk_invitation: BulkInvitationRequest,
    admin_user: User = Depends(require_admin_role)
):
    """
    📧 SEND BULK INVITATIONS
    
    Send invitations to multiple users at once:
    - Batch processing
    - Individual error handling
    - Progress tracking
    """
    try:
        # Validate role
        valid_roles = ['user', 'premium', 'admin']
        if bulk_invitation.role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {valid_roles}"
            )
        
        results = []
        errors = []
        
        for email in bulk_invitation.emails:
            try:
                result = await user_management_service.send_invitation(
                    email=email,
                    role=bulk_invitation.role,
                    invited_by=admin_user.id,
                    custom_message=bulk_invitation.custom_message,
                    expires_in_days=bulk_invitation.expires_in_days
                )
                results.append({
                    "email": email,
                    "status": "sent",
                    "invitation_id": result["invitation_id"]
                })
            except Exception as e:
                errors.append({
                    "email": email,
                    "error": str(e)
                })
        
        logger.info(f"Sent {len(results)} bulk invitations by admin {admin_user.id}")
        
        return {
            "status": "success",
            "message": f"Processed {len(bulk_invitation.emails)} invitations",
            "data": {
                "successful": results,
                "errors": errors,
                "summary": {
                    "total": len(bulk_invitation.emails),
                    "sent": len(results),
                    "failed": len(errors)
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send bulk invitations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send bulk invitations: {str(e)}")

@router.get("/invitations", summary="Get Invitations")
async def get_invitations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    invited_by: Optional[str] = Query(None),
    admin_user: User = Depends(require_admin_role)
):
    """
    📋 GET INVITATION LIST
    
    Retrieve paginated invitation list with filtering:
    - Filter by status (sent, opened, registered, expired)
    - Filter by admin who sent the invitation
    - Track invitation conversion funnel
    """
    try:
        filters = {}
        if status:
            filters['status'] = status
        if invited_by:
            filters['invited_by'] = invited_by
        
        result = await user_management_service.get_invitations(
            filters=filters,
            page=page,
            limit=limit
        )
        
        logger.info(f"Retrieved {len(result.get('invitations', []))} invitations for admin {admin_user.id}")
        
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get invitations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve invitations: {str(e)}")

@router.post("/invitations/{invitation_id}/resend", summary="Resend Invitation")
async def resend_invitation(
    invitation_id: str,
    admin_user: User = Depends(require_admin_role)
):
    """
    🔄 RESEND INVITATION
    
    Resend a pending invitation with updated tracking
    """
    try:
        success = await user_management_service.resend_invitation(
            invitation_id=invitation_id,
            admin_id=admin_user.id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to resend invitation")
        
        logger.info(f"Resent invitation {invitation_id} by admin {admin_user.id}")
        
        return {
            "status": "success",
            "message": "Invitation resent successfully",
            "data": {"invitation_id": invitation_id},
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resend invitation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resend invitation: {str(e)}")

@router.delete("/invitations/{invitation_id}", summary="Cancel Invitation")
async def cancel_invitation(
    invitation_id: str,
    admin_user: User = Depends(require_admin_role)
):
    """
    ❌ CANCEL INVITATION
    
    Cancel a pending invitation
    """
    try:
        success = await user_management_service.cancel_invitation(
            invitation_id=invitation_id,
            admin_id=admin_user.id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to cancel invitation")
        
        logger.info(f"Cancelled invitation {invitation_id} by admin {admin_user.id}")
        
        return {
            "status": "success",
            "message": "Invitation cancelled successfully",
            "data": {"invitation_id": invitation_id},
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel invitation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel invitation: {str(e)}")

# =================================================================
# ANALYTICS ENDPOINTS
# =================================================================

@router.get("/analytics/user-summary", summary="Get User Analytics Summary")
async def get_user_analytics_summary(
    admin_user: User = Depends(require_admin_role)
):
    """
    📊 USER ANALYTICS SUMMARY
    
    Get comprehensive user analytics and statistics
    """
    try:
        # Get all users for analytics
        result = await user_management_service.get_users(limit=1000)
        users = result.get('users', [])
        summary = result.get('summary', {})
        
        # Get invitation analytics
        invitation_result = await user_management_service.get_invitations(limit=1000)
        invitation_summary = invitation_result.get('summary', {})
        
        analytics = {
            "user_metrics": summary,
            "invitation_metrics": invitation_summary,
            "growth_metrics": {
                "new_users_today": len([
                    u for u in users 
                    if u.get('created_at', '').startswith(datetime.now().strftime('%Y-%m-%d'))
                ]),
                "active_users_30d": len([
                    u for u in users 
                    if u.get('status') == 'active'
                ]),
                "conversion_rate": (
                    invitation_summary.get('registered', 0) / 
                    max(invitation_summary.get('total_invitations', 1), 1) * 100
                ) if invitation_summary.get('total_invitations', 0) > 0 else 0
            }
        }
        
        logger.info(f"Generated user analytics summary for admin {admin_user.id}")
        
        return {
            "status": "success",
            "data": analytics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get user analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user analytics: {str(e)}") 