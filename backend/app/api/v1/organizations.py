import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import Principal, require_permission
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.rbac_data import ALL_ROLES
from app.core.security import generate_secure_token, hash_password
from app.models.organization import MembershipStatus, OrganizationMember
from app.models.rbac import Role
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.rbac_repository import RBACRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import SuccessResponse
from app.schemas.organization import (
    InviteMemberRequest,
    MemberOut,
    OrganizationOut,
    OrganizationUpdateRequest,
    UpdateMemberRequest,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/me", response_model=SuccessResponse[OrganizationOut])
async def get_my_organization(
    principal: Principal = Depends(require_permission("organizations.view")),
    db: AsyncSession = Depends(get_db),
):
    org = await OrganizationRepository(db).get_by_id(principal.organization_id)
    if org is None:
        raise AppError("NOT_FOUND", "Organization not found", 404)
    return SuccessResponse(data=OrganizationOut.model_validate(org))


@router.patch("/me", response_model=SuccessResponse[OrganizationOut])
async def update_my_organization(
    body: OrganizationUpdateRequest,
    principal: Principal = Depends(require_permission("organizations.manage")),
    db: AsyncSession = Depends(get_db),
):
    org = await OrganizationRepository(db).get_by_id(principal.organization_id)
    if org is None:
        raise AppError("NOT_FOUND", "Organization not found", 404)
    if body.name:
        org.name = body.name
    await db.commit()
    return SuccessResponse(data=OrganizationOut.model_validate(org), message="Organization updated")


@router.get("/me/members", response_model=SuccessResponse[list[MemberOut]])
async def list_members(
    principal: Principal = Depends(require_permission("members.view")),
    db: AsyncSession = Depends(get_db),
):
    rows = await OrganizationRepository(db).list_members(organization_id=principal.organization_id)
    data = [
        MemberOut(
            id=member.id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=member.role.name,
            status=member.status.value,
        )
        for member, user in rows
    ]
    return SuccessResponse(data=data)


@router.post("/me/invitations", response_model=SuccessResponse[dict], status_code=201)
async def invite_member(
    body: InviteMemberRequest,
    principal: Principal = Depends(require_permission("members.invite")),
    db: AsyncSession = Depends(get_db),
):
    if body.role not in ALL_ROLES:
        raise AppError("VALIDATION_ERROR", f"Unknown role '{body.role}'", 422)

    users = UserRepository(db)
    orgs = OrganizationRepository(db)
    rbac = RBACRepository(db)

    existing = await users.get_by_email(body.email)
    if existing and await orgs.get_membership(
        organization_id=principal.organization_id, user_id=existing.id
    ):
        raise AppError("CONFLICT", "This user is already a member of your organization", 409)

    role = await rbac.get_role_by_name(body.role)
    if role is None:
        raise AppError("VALIDATION_ERROR", f"Unknown role '{body.role}'", 422)

    if existing is None:
        # In production this would email an invitation link; for now we create the account
        # with a random temporary password and rely on forgot-password to set a real one,
        # since no SMTP provider is configured for local/dev delivery (see notification_service).
        existing = await users.create(
            email=body.email,
            hashed_password=hash_password(generate_secure_token()),
            full_name=body.full_name,
        )

    await orgs.add_member(
        organization_id=principal.organization_id,
        user_id=existing.id,
        role_id=role.id,
        status=MembershipStatus.INVITED,
    )
    await db.commit()
    return SuccessResponse(data={"user_id": str(existing.id)}, message="Invitation created")


@router.patch("/me/members/{member_id}", response_model=SuccessResponse[MemberOut])
async def update_member(
    member_id: uuid.UUID,
    body: UpdateMemberRequest,
    principal: Principal = Depends(require_permission("members.assign_role")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == principal.organization_id,
        )
    )
    row = result.first()
    if row is None:
        raise AppError("NOT_FOUND", "Member not found", 404)
    member, user = row
    audit = AuditRepository(db)

    if body.role is not None:
        if body.role not in ALL_ROLES:
            raise AppError("VALIDATION_ERROR", f"Unknown role '{body.role}'", 422)
        role = await RBACRepository(db).get_role_by_name(body.role)
        if role is None:
            raise AppError("RBAC_NOT_SEEDED", "Roles are not seeded", 500)
        old_role = await db.get(Role, member.role_id)
        old_role_name = old_role.name if old_role else None
        member.role_id = role.id
        await audit.log(
            action="member.role_changed",
            resource_type="organization_member",
            resource_id=str(member.id),
            organization_id=principal.organization_id,
            user_id=principal.user.id,
            metadata={
                "target_user_id": str(user.id),
                "from_role": old_role_name,
                "to_role": role.name,
            },
        )
    if body.status is not None:
        try:
            member.status = MembershipStatus(body.status)
        except ValueError as exc:
            raise AppError("VALIDATION_ERROR", f"Unknown status '{body.status}'", 422) from exc

    await db.commit()
    await db.refresh(member, attribute_names=["role"])
    return SuccessResponse(
        data=MemberOut(
            id=member.id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=member.role.name,
            status=member.status.value,
        ),
        message="Member updated",
    )


@router.delete("/me/members/{member_id}", response_model=SuccessResponse[dict])
async def remove_member(
    member_id: uuid.UUID,
    principal: Principal = Depends(require_permission("members.remove")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == principal.organization_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise AppError("NOT_FOUND", "Member not found", 404)
    await db.delete(member)
    await db.commit()
    return SuccessResponse(data={}, message="Member removed")
