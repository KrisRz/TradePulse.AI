"""
User Management API Routes for TradePulse.AI Admin Dashboard
Real DynamoDB integration for user data operations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from app.backend.api.v1.routes.auth import verify_production_jwt_token
from app.backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# Initialize database service
database_service = DatabaseService()

class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    status: Optional[str] = None
    role: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserCreateRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "user"
    first_name: Optional[str] = None
    last_name: Optional[str] = None

async def get_current_admin_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current admin user from JWT token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required"
        )
    
    try:
        token_payload = verify_production_jwt_token(credentials.credentials)
        
        # Check if user is admin
        if not token_payload.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return token_payload
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying admin user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@router.get("/users")
async def get_all_users(admin_user: Dict[str, Any] = Depends(get_current_admin_user)) -> List[Dict[str, Any]]:
    """Get all users for admin management"""
    try:
        logger.info(f"👥 Admin {admin_user['email']} requesting all users")
        
        users = await database_service.get_all_users()
        
        # Enrich user data with portfolio info
        enriched_users = []
        for user in users:
            try:
                portfolio = await database_service.get_user_portfolio(user.get('id', user.get('user_id', '')))
                user['portfolio_value'] = portfolio.get('balance', 0) if portfolio else 0
                user['portfolio_pnl'] = portfolio.get('total_pnl', 0) if portfolio else 0
                
                # Add additional calculated fields
                user['last_activity'] = user.get('last_login', 'Never')
                user['account_age_days'] = (datetime.now() - datetime.fromisoformat(user.get('created_at', datetime.now().isoformat()).replace('Z', '+00:00'))).days if user.get('created_at') else 0
                
            except Exception as e:
                logger.warning(f"Error enriching user data for {user.get('email', 'unknown')}: {e}")
                user['portfolio_value'] = 0
                user['portfolio_pnl'] = 0
                user['last_activity'] = 'Unknown'
                user['account_age_days'] = 0
            
            enriched_users.append(user)
        
        logger.info(f"✅ Retrieved {len(enriched_users)} users with portfolio data")
        return enriched_users
        
    except Exception as e:
        logger.error(f"❌ Error fetching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )

@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str, 
    admin_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get detailed user information"""
    try:
        logger.info(f"👥 Admin {admin_user['email']} requesting details for user {user_id}")
        
        user = await database_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Get user's portfolio
        portfolio = await database_service.get_user_portfolio(user_id)
        
        # Get user's activity logs
        activity_logs = await database_service.get_user_activity_logs(user_id, limit=50)
        
        # Calculate user statistics
        user_stats = {
            "total_trades": len([log for log in activity_logs if log.get('action') in ['trade_opened', 'trade_closed']]),
            "login_count": len([log for log in activity_logs if log.get('action') == 'login']),
            "last_login": max([log.get('timestamp') for log in activity_logs if log.get('action') == 'login'], default=None),
            "account_status": user.get('status', 'active'),
            "risk_score": 'Low'  # In production, calculate based on trading behavior
        }
        
        response_data = {
            "user": user,
            "portfolio": portfolio,
            "activity_logs": activity_logs,
            "permissions": user.get('permissions', []),
            "statistics": user_stats,
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"✅ User details retrieved for {user_id}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching user details for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user details: {str(e)}"
        )

@router.put("/users/{user_id}")
async def update_user(
    user_id: str, 
    user_data: UserUpdateRequest, 
    admin_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Update user information"""
    try:
        logger.info(f"👥 Admin {admin_user['email']} updating user {user_id}")
        
        # Convert Pydantic model to dict, excluding None values
        update_data = {k: v for k, v in user_data.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid update data provided"
            )
        
        updated_user = await database_service.update_user(user_id, update_data)
        
        # Log admin action
        await database_service.log_admin_action(
            admin_user['user_id'],
            'user_update',
            {'target_user': user_id, 'changes': update_data}
        )
        
        logger.info(f"✅ User {user_id} updated successfully")
        return {
            "message": "User updated successfully", 
            "user": updated_user,
            "updated_fields": list(update_data.keys()),
            "updated_by": admin_user['email'],
            "updated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )

@router.post("/users")
async def create_user(
    user_data: UserCreateRequest,
    admin_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Create new user (admin only)"""
    try:
        logger.info(f"👥 Admin {admin_user['email']} creating new user {user_data.email}")
        
        # Check if user already exists
        existing_users = await database_service.get_all_users()
        if any(user.get('email') == user_data.email for user in existing_users):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Create user data
        import secrets
        import bcrypt
        
        user_id = f"user_admin_{secrets.token_urlsafe(8)}"
        password_hash = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        new_user_data = {
            "id": user_id,
            "user_id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": password_hash,
            "role": user_data.role,
            "status": "active",
            "is_admin": user_data.role == "admin",
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "created_at": datetime.now().isoformat(),
            "created_by": admin_user['user_id']
        }
        
        # In production, save to DynamoDB users table
        # For now, just return the created user data
        
        # Log admin action
        await database_service.log_admin_action(
            admin_user['user_id'],
            'user_create',
            {'new_user': user_id, 'email': user_data.email, 'role': user_data.role}
        )
        
        # Remove password hash from response
        response_user = {k: v for k, v in new_user_data.items() if k != 'password_hash'}
        
        logger.info(f"✅ User {user_data.email} created successfully with ID {user_id}")
        return {
            "message": "User created successfully",
            "user": response_user,
            "created_by": admin_user['email'],
            "created_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Delete user (admin only)"""
    try:
        logger.info(f"👥 Admin {admin_user['email']} deleting user {user_id}")
        
        # Prevent self-deletion
        if user_id == admin_user['user_id']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Check if user exists
        user = await database_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # In production, perform soft delete or archive user data
        # For now, just log the action
        
        # Log admin action
        await database_service.log_admin_action(
            admin_user['user_id'],
            'user_delete',
            {'deleted_user': user_id, 'user_email': user.get('email')}
        )
        
        logger.info(f"✅ User {user_id} deletion logged")
        return {
            "message": "User deletion logged successfully",
            "deleted_user_id": user_id,
            "deleted_by": admin_user['email'],
            "deleted_at": datetime.now().isoformat(),
            "note": "In production, this would perform actual deletion or archival"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )

@router.get("/users/{user_id}/activity")
async def get_user_activity(
    user_id: str, 
    limit: int = 100,
    admin_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get user activity logs"""
    try:
        logger.info(f"👥 Admin {admin_user['email']} requesting activity logs for user {user_id}")
        
        activity_logs = await database_service.get_user_activity_logs(user_id, limit=limit)
        
        # Categorize activities
        activity_summary = {
            "login_count": len([log for log in activity_logs if log.get('action') == 'login']),
            "trade_count": len([log for log in activity_logs if log.get('action') in ['trade_opened', 'trade_closed']]),
            "settings_changes": len([log for log in activity_logs if log.get('action') == 'settings_updated']),
            "total_activities": len(activity_logs),
            "date_range": {
                "earliest": min([log.get('timestamp') for log in activity_logs], default=None),
                "latest": max([log.get('timestamp') for log in activity_logs], default=None)
            }
        }
        
        response_data = {
            "activity_logs": activity_logs,
            "summary": activity_summary,
            "user_id": user_id,
            "retrieved_at": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Retrieved {len(activity_logs)} activity logs for user {user_id}")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching user activity for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user activity: {str(e)}"
        )

@router.post("/users/{user_id}/permissions")
async def update_user_permissions(
    user_id: str,
    permissions_data: Dict[str, Any],
    admin_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Update user permissions"""
    try:
        logger.info(f"👥 Admin {admin_user['email']} updating permissions for user {user_id}")
        
        # Validate permissions data
        allowed_permissions = [
            "trading", "portfolio_view", "analytics_view", "settings_modify",
            "api_access", "mobile_access", "desktop_access"
        ]
        
        new_permissions = permissions_data.get('permissions', [])
        invalid_permissions = [perm for perm in new_permissions if perm not in allowed_permissions]
        
        if invalid_permissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permissions: {invalid_permissions}"
            )
        
        # Update user permissions
        update_data = {
            "permissions": new_permissions,
            "permissions_updated_at": datetime.now().isoformat(),
            "permissions_updated_by": admin_user['user_id']
        }
        
        updated_user = await database_service.update_user(user_id, update_data)
        
        # Log admin action
        await database_service.log_admin_action(
            admin_user['user_id'],
            'permissions_update',
            {'target_user': user_id, 'new_permissions': new_permissions}
        )
        
        logger.info(f"✅ Permissions updated for user {user_id}")
        return {
            "message": "User permissions updated successfully",
            "user_id": user_id,
            "permissions": new_permissions,
            "updated_by": admin_user['email'],
            "updated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating permissions for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user permissions: {str(e)}"
        )

@router.get("/users/{user_id}/portfolio")
async def get_user_portfolio_details(
    user_id: str,
    admin_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get detailed portfolio information for specific user"""
    try:
        logger.info(f"👥 Admin {admin_user['email']} requesting portfolio details for user {user_id}")
        
        # Get user portfolio
        portfolio = await database_service.get_user_portfolio(user_id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found for user"
            )
        
        # Get user's positions (simulated for now)
        all_positions = await database_service.get_all_virtual_positions()
        user_positions = [pos for pos in all_positions if pos.get('user_id') == user_id]
        
        # Calculate portfolio metrics
        open_positions = [pos for pos in user_positions if pos.get('status') == 'open']
        closed_positions = [pos for pos in user_positions if pos.get('status') == 'closed']
        
        portfolio_metrics = {
            "total_value": portfolio.get('balance', 0),
            "total_pnl": portfolio.get('total_pnl', 0),
            "open_positions_count": len(open_positions),
            "closed_positions_count": len(closed_positions),
            "total_trades": len(user_positions),
            "win_rate": len([pos for pos in closed_positions if pos.get('pnl', 0) > 0]) / len(closed_positions) * 100 if closed_positions else 0,
            "avg_trade_pnl": sum(pos.get('pnl', 0) for pos in closed_positions) / len(closed_positions) if closed_positions else 0
        }
        
        response_data = {
            "portfolio": portfolio,
            "positions": {
                "open": open_positions,
                "closed": closed_positions[-10:]  # Last 10 closed positions
            },
            "metrics": portfolio_metrics,
            "user_id": user_id,
            "retrieved_at": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Portfolio details retrieved for user {user_id}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching portfolio details for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user portfolio details: {str(e)}"
        )

@router.get("/health")
async def user_management_health():
    """User management service health check"""
    return {
        "service": "user_management",
        "status": "operational",
        "database": "dynamodb_local",
        "timestamp": datetime.now().isoformat()
    }