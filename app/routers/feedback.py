"""
Roommate Agreement Generator - Feedback Router
API endpoints for roommate feedback and ratings
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from uuid import UUID

from app.database import get_db
from app.deps.auth import get_current_user, CurrentUser
from app.models.models import Feedback, Agreement, AgreementParty, AppUser
from app.schemas.feedback import (
    FeedbackCreate, FeedbackResponse, FeedbackSummary
)

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/{agreement_id}", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    agreement_id: UUID,
    body: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Submit feedback/rating for a roommate in a completed agreement.
    
    - Only parties of the agreement can submit feedback
    - Agreement must be in 'completed' status
    - Can only rate other parties, not yourself
    - One rating per user pair per agreement
    """
    user = current_user.user
    
    # Check agreement exists and is completed
    agreement = db.query(Agreement).filter(Agreement.id == str(agreement_id)).first()
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    if agreement.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit feedback for completed agreements"
        )
    
    # Check current user is a party
    user_party = next(
        (p for p in agreement.parties if p.user_id == user.id),
        None
    )
    if not user_party:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a party to this agreement"
        )
    
    # Check target user is a different party
    target_party = next(
        (p for p in agreement.parties if p.user_id == body.to_user_id),
        None
    )
    if not target_party:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target user is not a party to this agreement"
        )
    
    if body.to_user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot rate yourself"
        )
    
    # Check for existing feedback
    existing = db.query(Feedback).filter(
        Feedback.agreement_id == str(agreement_id),
        Feedback.from_user_id == user.id,
        Feedback.to_user_id == body.to_user_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted feedback for this user"
        )
    
    # Create feedback
    feedback = Feedback(
        agreement_id=str(agreement_id),
        from_user_id=user.id,
        to_user_id=body.to_user_id,
        rating=body.rating,
        comment=body.comment,
        categories=body.categories.model_dump() if body.categories else None,
        is_anonymous=body.is_anonymous
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    # Get user names for response
    to_user = db.query(AppUser).filter(AppUser.id == body.to_user_id).first()
    
    return FeedbackResponse(
        id=feedback.id,
        agreement_id=feedback.agreement_id,
        from_user_id=None if feedback.is_anonymous else feedback.from_user_id,
        from_user_name=None if feedback.is_anonymous else user.name,
        to_user_id=feedback.to_user_id,
        to_user_name=to_user.name if to_user else None,
        rating=feedback.rating,
        comment=feedback.comment,
        categories=feedback.categories,
        is_anonymous=feedback.is_anonymous,
        created_at=feedback.created_at
    )


@router.get("/{agreement_id}", response_model=List[FeedbackResponse])
async def get_agreement_feedback(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get all feedback for an agreement.
    
    Only parties of the agreement can view feedback.
    """
    user = current_user.user
    
    agreement = db.query(Agreement).filter(Agreement.id == str(agreement_id)).first()
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )
    
    # Check user is a party
    is_party = any(p.user_id == user.id for p in agreement.parties)
    if not is_party:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a party to this agreement"
        )
    
    feedback_list = db.query(Feedback).filter(
        Feedback.agreement_id == str(agreement_id)
    ).all()
    
    result = []
    for fb in feedback_list:
        from_user = db.query(AppUser).filter(AppUser.id == fb.from_user_id).first()
        to_user = db.query(AppUser).filter(AppUser.id == fb.to_user_id).first()
        
        result.append(FeedbackResponse(
            id=fb.id,
            agreement_id=fb.agreement_id,
            from_user_id=None if fb.is_anonymous else fb.from_user_id,
            from_user_name=None if fb.is_anonymous else (from_user.name if from_user else None),
            to_user_id=fb.to_user_id,
            to_user_name=to_user.name if to_user else None,
            rating=fb.rating,
            comment=fb.comment,
            categories=fb.categories,
            is_anonymous=fb.is_anonymous,
            created_at=fb.created_at
        ))
    
    return result


@router.get("/user/{user_id}/summary", response_model=FeedbackSummary)
async def get_user_feedback_summary(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get feedback summary for a user.
    
    Shows average rating and recent feedback.
    """
    target_user = db.query(AppUser).filter(AppUser.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get all feedback for this user
    feedback_list = db.query(Feedback).filter(
        Feedback.to_user_id == user_id
    ).order_by(Feedback.created_at.desc()).all()
    
    total_ratings = len(feedback_list)
    average_rating = 0.0
    
    if total_ratings > 0:
        average_rating = sum(fb.rating for fb in feedback_list) / total_ratings
    
    # Calculate category averages
    category_totals = {}
    category_counts = {}
    for fb in feedback_list:
        if fb.categories:
            for cat, val in fb.categories.items():
                if val is not None:
                    category_totals[cat] = category_totals.get(cat, 0) + val
                    category_counts[cat] = category_counts.get(cat, 0) + 1
    
    category_averages = {
        cat: category_totals[cat] / category_counts[cat]
        for cat in category_totals
    }
    
    # Get recent feedback (last 5)
    recent = []
    for fb in feedback_list[:5]:
        from_user = db.query(AppUser).filter(AppUser.id == fb.from_user_id).first()
        recent.append(FeedbackResponse(
            id=fb.id,
            agreement_id=fb.agreement_id,
            from_user_id=None if fb.is_anonymous else fb.from_user_id,
            from_user_name=None if fb.is_anonymous else (from_user.name if from_user else None),
            to_user_id=fb.to_user_id,
            to_user_name=target_user.name,
            rating=fb.rating,
            comment=fb.comment,
            categories=fb.categories,
            is_anonymous=fb.is_anonymous,
            created_at=fb.created_at
        ))
    
    return FeedbackSummary(
        user_id=user_id,
        user_name=target_user.name,
        total_ratings=total_ratings,
        average_rating=round(average_rating, 2),
        category_averages=category_averages if category_averages else None,
        recent_feedback=recent
    )


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    feedback_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Delete your own feedback.
    
    Only the feedback author can delete it.
    """
    user = current_user.user
    
    feedback = db.query(Feedback).filter(Feedback.id == str(feedback_id)).first()
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    if feedback.from_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own feedback"
        )
    
    db.delete(feedback)
    db.commit()
    
    return None
