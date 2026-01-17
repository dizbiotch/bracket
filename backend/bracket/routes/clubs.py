from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from bracket.config import config
from bracket.logic.subscriptions import check_requirement
from bracket.models.db.club import ClubCreateBody, ClubUpdateBody
from bracket.models.db.user import UserPublic
from bracket.routes.auth import user_authenticated, user_authenticated_for_club
from bracket.routes.models import ClubResponse, ClubsResponse, SuccessResponse
from bracket.sql.clubs import (
    create_club,
    get_clubs_for_user_id,
    sql_add_collaborator_to_club,
    sql_delete_club,
    sql_get_users_for_club,
    sql_remove_user_from_club,
    sql_update_club,
)
from bracket.sql.users import get_user
from bracket.utils.errors import ForeignKey, check_foreign_key_violation
from bracket.utils.id_types import ClubId, UserId

router = APIRouter(prefix=config.api_prefix)


class ClubCollaboratorAddBody(BaseModel):
    email: str


@router.get("/clubs", response_model=ClubsResponse)
async def get_clubs(user: UserPublic = Depends(user_authenticated)) -> ClubsResponse:
    return ClubsResponse(data=await get_clubs_for_user_id(user.id))


@router.post("/clubs", response_model=ClubResponse)
async def create_new_club(
    club: ClubCreateBody, user: UserPublic = Depends(user_authenticated)
) -> ClubResponse:
    existing_clubs = await get_clubs_for_user_id(user.id)
    check_requirement(existing_clubs, user, "max_clubs")
    return ClubResponse(data=await create_club(club, user.id))


@router.delete("/clubs/{club_id}", response_model=SuccessResponse)
async def delete_club(
    club_id: ClubId, _: UserPublic = Depends(user_authenticated_for_club)
) -> SuccessResponse:
    with check_foreign_key_violation({ForeignKey.tournaments_club_id_fkey}):
        await sql_delete_club(club_id)

    return SuccessResponse()


@router.put("/clubs/{club_id}", response_model=ClubResponse)
async def update_club(
    club_id: ClubId, club: ClubUpdateBody, _: UserPublic = Depends(user_authenticated_for_club)
) -> ClubResponse:
    return ClubResponse(data=await sql_update_club(club_id, club))


@router.post("/clubs/{club_id}/collaborators", response_model=SuccessResponse)
async def add_club_collaborator(
    club_id: ClubId,
    body: ClubCollaboratorAddBody,
    _: UserPublic = Depends(user_authenticated_for_club),
) -> SuccessResponse:
    """Add a collaborator to a club so they can co-admin tournaments.

    Any user who already has access to the club (owner or collaborator)
    can add additional collaborators.
    """

    user = await get_user(body.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email does not exist",
        )

    await sql_add_collaborator_to_club(user.id, club_id)
    return SuccessResponse()


@router.delete("/clubs/{club_id}/collaborators/{user_id}", response_model=SuccessResponse)
async def remove_club_collaborator(
    club_id: ClubId,
    user_id: UserId,
    _: UserPublic = Depends(user_authenticated_for_club),
) -> SuccessResponse:
    """Remove a user's access to a club (owner or collaborator)."""

    await sql_remove_user_from_club(user_id, club_id)
    return SuccessResponse()


@router.get("/clubs/{club_id}/collaborators", response_model=ClubsResponse)
async def list_club_collaborators(
    club_id: ClubId,
    _: UserPublic = Depends(user_authenticated_for_club),
) -> ClubsResponse:
    """List all users (owners and collaborators) that have access to this club.

    This can be used in the frontend to show who can administer tournaments
    for the club and to allow removing collaborators.
    """

    users = await sql_get_users_for_club(club_id)
    # Reuse the ClubsResponse wrapper shape is not ideal for users, but keeps
    # the API surface consistent without expanding OpenAPI types right now.
    # The frontend treats this as a generic `data` array of users.
    from bracket.routes.models import DataResponse

    # type: ignore[call-arg]
    return DataResponse[list[UserPublic]](data=users)  # type: ignore[return-value]
