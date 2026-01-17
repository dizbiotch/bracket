from bracket.database import database
from bracket.models.db.club import Club, ClubCreateBody, ClubUpdateBody
from bracket.models.db.user import UserPublic
from bracket.utils.id_types import ClubId, UserId
from bracket.utils.types import assert_some


async def sql_give_user_access_to_club(user_id: UserId, club_id: ClubId) -> None:
    query_many_to_many = """
        INSERT INTO users_x_clubs (club_id, user_id, relation)
        VALUES (:club_id, :user_id, 'OWNER')
        """
    await database.execute(
        query=query_many_to_many,
        values={"club_id": assert_some(club_id), "user_id": user_id},
    )


async def sql_add_collaborator_to_club(user_id: UserId, club_id: ClubId) -> None:
    """Grant a user collaborator access to a club.

    This makes the user a co-admin for all tournaments in the club.
    """

    query = """
        INSERT INTO users_x_clubs (club_id, user_id, relation)
        VALUES (:club_id, :user_id, 'COLLABORATOR')
        """
    await database.execute(query=query, values={"club_id": club_id, "user_id": user_id})


async def sql_remove_user_from_club(user_id: UserId, club_id: ClubId) -> None:
    """Revoke a user's access (owner or collaborator) to a club."""

    query = """
        DELETE FROM users_x_clubs
        WHERE club_id = :club_id AND user_id = :user_id
        """
    await database.execute(query=query, values={"club_id": club_id, "user_id": user_id})


async def sql_get_users_for_club(club_id: ClubId) -> list[UserPublic]:
    query = """
                SELECT users.*
                FROM users
                JOIN users_x_clubs uxc ON users.id = uxc.user_id
                WHERE uxc.club_id = :club_id
                """
    results = await database.fetch_all(query=query, values={"club_id": club_id})
    return [UserPublic.model_validate(dict(result._mapping)) for result in results]


async def create_club(club: ClubCreateBody, user_id: UserId) -> Club:
    async with database.transaction():
        query = """
            INSERT INTO clubs (name, created)
            VALUES (:name, NOW())
            RETURNING *
        """
        result = await database.fetch_one(query=query, values={"name": club.name})
        if result is None:
            raise ValueError("Could not create club")

        club_created = Club.model_validate(dict(result._mapping))

        await sql_give_user_access_to_club(user_id, club_created.id)

    return club_created


async def sql_update_club(club_id: ClubId, club: ClubUpdateBody) -> Club | None:
    query = """
        UPDATE clubs
        SET name = :name
        WHERE id = :club_id
        RETURNING *
        """
    result = await database.fetch_one(query=query, values={"name": club.name, "club_id": club_id})
    return Club.model_validate(result) if result is not None else None


async def sql_delete_club(club_id: ClubId) -> None:
    query = """
        DELETE FROM clubs
        WHERE id = :club_id
        """
    await database.execute(query=query, values={"club_id": club_id})


async def get_clubs_for_user_id(user_id: UserId) -> list[Club]:
    query = """
        SELECT clubs.* FROM clubs
        JOIN users_x_clubs uxc on clubs.id = uxc.club_id
        WHERE uxc.user_id = :user_id
        """
    results = await database.fetch_all(query=query, values={"user_id": user_id})
    return [Club.model_validate(dict(result._mapping)) for result in results]
