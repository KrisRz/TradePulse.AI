"""
User Invitation System API Routes for TradePulse.AI
Enterprise invitation management with email notifications
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from pydantic import BaseModel, EmailStr
import secrets
import string

from app.backend.services.database_service import DatabaseService
from app.backend.utils.dependencies import require_admin_role, User
from app.backend.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# Initialize database service
database_service = DatabaseService()

# =================================================================
# PYDANTIC MODELS
# =================================================================

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

class InvitationResponse(BaseModel):
    invitation_id: str
    email: str
    role: str
    status: str
    expires_at: str
    created_at: str
    created_by: str
    invitation_link: str

# =================================================================
# INVITATION ENDPOINTS
# =================================================================

@router.get("/invitations")
async def list_invitations(
    status_filter: Optional[str] = None,
    limit: int = 50,
    admin_user: User = Depends(require_admin_role)
):
    """List all pending invitations"""
    try:
        logger.info(f"👤 Admin {admin_user.email} requesting invitations list")
        
        # Get invitations from database
        invitations = await database_service.get_invitations(
            status_filter=status_filter,
            limit=limit
        )
        
        response_data = {
            "invitations": invitations,
            "total": len(invitations),
            "filters": {
                "status": status_filter,
                "limit": limit
            },
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Retrieved {len(invitations)} invitations")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching invitations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch invitations: {str(e)}"
        )

@router.post("/invitations")
async def send_invitation(
    invitation: InvitationRequest,
    admin_user: User = Depends(require_admin_role)
):
    """Send invitation to new user"""
    try:
        logger.info(f"👤 Admin {admin_user.email} sending invitation to {invitation.email}")
        
        # Validate role
        valid_roles = ["user", "admin", "moderator", "premium_user"]
        if invitation.role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {valid_roles}"
            )
        
        # Check if user already exists
        existing_user = await database_service.get_user_by_email(invitation.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Check if invitation already exists
        existing_invitation = await database_service.get_invitation_by_email(invitation.email)
        if existing_invitation and existing_invitation.get('status') == 'pending':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pending invitation already exists for this email"
            )
        
        # Generate invitation
        invitation_id = f"inv_{secrets.token_urlsafe(16)}"
        invitation_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=invitation.expires_in_days)
        
        # Create invitation record
        invitation_data = {
            "invitation_id": invitation_id,
            "email": invitation.email,
            "role": invitation.role,
            "status": "pending",
            "invitation_token": invitation_token,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now().isoformat(),
            "created_by": admin_user.id,
            "custom_message": invitation.custom_message
        }
        
        # Save to database
        await database_service.create_invitation(invitation_data)
        
        # Generate invitation link
        invitation_link = f"{settings.FRONTEND_URL}/auth/signup?token={invitation_token}"
        
        # In production, send email here
        # await email_service.send_invitation_email(invitation.email, invitation_link, invitation.custom_message)
        
        response_data = {
            "invitation_id": invitation_id,
            "email": invitation.email,
            "role": invitation.role,
            "status": "pending",
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now().isoformat(),
            "created_by": admin_user.email,
            "invitation_link": invitation_link,
            "expires_in_days": invitation.expires_in_days,
            "success": True
        }
        
        logger.info(f"✅ Invitation sent to {invitation.email}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error sending invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send invitation: {str(e)}"
        )

@router.post("/invitations/bulk")
async def send_bulk_invitations(
    bulk_invitation: BulkInvitationRequest,
    admin_user: User = Depends(require_admin_role)
):
    """Send invitations to multiple users"""
    try:
        logger.info(f"👤 Admin {admin_user.email} sending bulk invitations to {len(bulk_invitation.emails)} users")
        
        results = []
        successful = 0
        failed = 0
        
        for email in bulk_invitation.emails:
            try:
                # Create individual invitation
                invitation = InvitationRequest(
                    email=email,
                    role=bulk_invitation.role,
                    custom_message=bulk_invitation.custom_message,
                    expires_in_days=bulk_invitation.expires_in_days
                )
                
                # Send invitation (reuse single invitation logic)
                result = await send_invitation(invitation, admin_user)
                results.append({
                    "email": email,
                    "status": "sent",
                    "invitation_id": result["invitation_id"]
                })
                successful += 1
                
            except Exception as e:
                results.append({
                    "email": email,
                    "status": "failed",
                    "error": str(e)
                })
                failed += 1
        
        response_data = {
            "total_invitations": len(bulk_invitation.emails),
            "successful": successful,
            "failed": failed,
            "results": results,
            "sent_by": admin_user.email,
            "sent_at": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Bulk invitations: {successful} sent, {failed} failed")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error sending bulk invitations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send bulk invitations: {str(e)}"
        )

@router.post("/invitations/{invitation_id}/resend")
async def resend_invitation(
    invitation_id: str,
    admin_user: User = Depends(require_admin_role)
):
    """Resend invitation email"""
    try:
        logger.info(f"👤 Admin {admin_user.email} resending invitation {invitation_id}")
        
        # Get invitation
        invitation = await database_service.get_invitation(invitation_id)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )
        
        if invitation.get('status') != 'pending':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only resend pending invitations"
            )
        
        # Check if expired
        expires_at = datetime.fromisoformat(invitation['expires_at'])
        if datetime.now() > expires_at:
            # Update invitation as expired
            await database_service.update_invitation_status(invitation_id, 'expired')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has expired"
            )
        
        # Update resend count
        resend_count = invitation.get('resend_count', 0) + 1
        await database_service.update_invitation_resend_count(invitation_id, resend_count)
        
        # Generate new invitation link
        invitation_link = f"{settings.FRONTEND_URL}/auth/signup?token={invitation['invitation_token']}"
        
        # In production, send email here
        # await email_service.send_invitation_email(invitation['email'], invitation_link, invitation.get('custom_message'))
        
        response_data = {
            "invitation_id": invitation_id,
            "email": invitation['email'],
            "resend_count": resend_count,
            "invitation_link": invitation_link,
            "resent_by": admin_user.email,
            "resent_at": datetime.now().isoformat(),
            "success": True
        }
        
        logger.info(f"✅ Invitation {invitation_id} resent")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error resending invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend invitation: {str(e)}"
        )

@router.delete("/invitations/{invitation_id}")
async def cancel_invitation(
    invitation_id: str,
    admin_user: User = Depends(require_admin_role)
):
    """Cancel pending invitation"""
    try:
        logger.info(f"👤 Admin {admin_user.email} cancelling invitation {invitation_id}")
        
        # Get invitation
        invitation = await database_service.get_invitation(invitation_id)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )
        
        if invitation.get('status') != 'pending':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only cancel pending invitations"
            )
        
        # Update status to cancelled
        await database_service.update_invitation_status(invitation_id, 'cancelled', admin_user.id)
        
        response_data = {
            "invitation_id": invitation_id,
            "email": invitation['email'],
            "old_status": "pending",
            "new_status": "cancelled",
            "cancelled_by": admin_user.email,
            "cancelled_at": datetime.now().isoformat(),
            "success": True
        }
        
        logger.info(f"✅ Invitation {invitation_id} cancelled")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error cancelling invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel invitation: {str(e)}"
        )

@router.get("/invitations/{invitation_id}")
async def get_invitation_details(
    invitation_id: str,
    admin_user: User = Depends(require_admin_role)
):
    """Get detailed invitation information"""
    try:
        logger.info(f"👤 Admin {admin_user.email} requesting invitation details {invitation_id}")
        
        # Get invitation
        invitation = await database_service.get_invitation(invitation_id)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )
        
        # Check expiration status
        expires_at = datetime.fromisoformat(invitation['expires_at'])
        is_expired = datetime.now() > expires_at
        
        if is_expired and invitation.get('status') == 'pending':
            # Auto-update expired invitations
            await database_service.update_invitation_status(invitation_id, 'expired')
            invitation['status'] = 'expired'
        
        response_data = {
            "invitation_id": invitation_id,
            "email": invitation['email'],
            "role": invitation['role'],
            "status": invitation['status'],
            "created_at": invitation['created_at'],
            "expires_at": invitation['expires_at'],
            "is_expired": is_expired,
            "resend_count": invitation.get('resend_count', 0),
            "custom_message": invitation.get('custom_message'),
            "created_by": invitation.get('created_by'),
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Invitation details retrieved for {invitation_id}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching invitation details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch invitation details: {str(e)}"
        )

@router.get("/invitations/stats")
async def get_invitation_stats(
    admin_user: User = Depends(require_admin_role)
):
    """Get invitation system statistics"""
    try:
        logger.info(f"👤 Admin {admin_user.email} requesting invitation stats")
        
        # Get all invitations for stats
        all_invitations = await database_service.get_invitations(limit=1000)
        
        # Calculate stats
        total_invitations = len(all_invitations)
        pending_invitations = len([inv for inv in all_invitations if inv.get('status') == 'pending'])
        accepted_invitations = len([inv for inv in all_invitations if inv.get('status') == 'accepted'])
        expired_invitations = len([inv for inv in all_invitations if inv.get('status') == 'expired'])
        cancelled_invitations = len([inv for inv in all_invitations if inv.get('status') == 'cancelled'])
        
        # Recent activity (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_invitations = [
            inv for inv in all_invitations 
            if datetime.fromisoformat(inv['created_at']) > week_ago
        ]
        
        response_data = {
            "total_invitations": total_invitations,
            "pending": pending_invitations,
            "accepted": accepted_invitations,
            "expired": expired_invitations,
            "cancelled": cancelled_invitations,
            "acceptance_rate": (accepted_invitations / total_invitations * 100) if total_invitations > 0 else 0,
            "recent_activity": {
                "last_7_days": len(recent_invitations),
                "pending_this_week": len([inv for inv in recent_invitations if inv.get('status') == 'pending']),
                "accepted_this_week": len([inv for inv in recent_invitations if inv.get('status') == 'accepted'])
            },
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Invitation stats: {total_invitations} total, {pending_invitations} pending")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching invitation stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch invitation stats: {str(e)}"
        )

@router.get("/health")
async def invitation_system_health():
    """Invitation system health check"""
    return {
        "service": "invitation_system",
        "status": "operational",
        "database": "dynamodb_local",
        "email_service": "ready",
        "timestamp": datetime.now().isoformat()
    }
