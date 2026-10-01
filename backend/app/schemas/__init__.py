from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------
# Common / utils
# --------------------------------------------------------------------------
class ScrapeLinkResponse(BaseModel):
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    image_url: Optional[str] = None
    favicon: Optional[str] = None


class ExtractedLink(BaseModel):
    title: Optional[str] = None
    url: str


# --------------------------------------------------------------------------
# Settings (hybrid engine)
# --------------------------------------------------------------------------
class SettingOut(BaseModel):
    key: str
    value: Any = None
    type: str
    group: str
    label: str
    help: Optional[str] = None
    is_env_overridden: bool
    source: str  # "env" | "database"
    editable: bool
    public: bool


class SettingsUpdate(BaseModel):
    """Partial update of UI-editable settings (env-overridden keys rejected)."""
    values: dict[str, Any] = Field(..., description="key -> value")


class SettingsResponse(BaseModel):
    settings: list[SettingOut]


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "cookie"


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    username: Optional[str] = None
    password: str
    full_name: Optional[str] = None


class UserOut(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool
    auth_provider: str
    avatar_url: Optional[str] = None


class CreateUserRequest(BaseModel):
    email: str
    username: Optional[str] = None
    password: str
    full_name: Optional[str] = None
    role: str = "user"  # user | admin


class UpdateSelfRequest(BaseModel):
    """Self-service profile update for the logged-in user (display name only)."""

    full_name: Optional[str] = Field(None, max_length=255)


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class OIDCLoginRequest(BaseModel):
    code: str
    state: Optional[str] = None
    redirect_uri: Optional[str] = None


# --------------------------------------------------------------------------
# Wishlist / items
# --------------------------------------------------------------------------
class CategoryBase(BaseModel):
    name: str
    color: str = "#1976d2"
    is_global: bool = False


class CategoryOut(CategoryBase):
    id: str
    wishlist_id: Optional[str] = None


class WishItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    priority: int = 0
    quantity: Optional[int] = None
    category_id: Optional[str] = None
    archived: bool = False


class WishItemCreate(WishItemBase):
    pass


class WishItemOut(WishItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    wishlist_id: str
    status: str
    claimed_by: Optional[str] = None
    claimed_by_name: Optional[str] = None


class BulkItemImportRequest(BaseModel):
    text: str
    category_id: Optional[str] = None
    scrape: bool = False


class BulkItemImportResponse(BaseModel):
    created: int
    items: list[WishItemOut]


class WishlistBase(BaseModel):
    title: str
    description: Optional[str] = None
    visibility: str = "private"
    allow_claims: bool = True
    cover_image: Optional[str] = None


class WishlistCreate(WishlistBase):
    pass


class WishlistUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[str] = None
    allow_claims: Optional[bool] = None
    cover_image: Optional[str] = None
    archived: Optional[bool] = None
    # Link this wishlist to a global Person (Gift Exchange). Pass null to unlink.
    person_id: Optional[str] = None


class WishlistOut(WishlistBase):
    id: str
    slug: str
    owner_id: str
    archived: bool
    person_id: Optional[str] = None
    categories: list[CategoryOut] = []
    items: list[WishItemOut] = []
    shared_with_me: bool = False
    can_edit: bool = False
    can_manage: bool = False
    collaborator_count: int = 0


class WishlistPublicSummary(BaseModel):
    """Lightweight summary of a publicly listed wishlist for the start-page directory.

    Unlike :class:`WishlistOut` it intentionally omits items, shares and the
    owner id, and only public (never unlisted/private) lists are returned.
    """

    id: str
    slug: str
    title: str
    description: Optional[str] = None
    cover_image: Optional[str] = None
    visibility: str
    owner_name: Optional[str] = None
    item_count: int = 0


class CollaboratorUser(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None


class WishlistShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    wishlist_id: str
    user_id: str
    can_edit: bool
    can_manage: bool
    user: CollaboratorUser


class WishlistShareCreate(BaseModel):
    user_id: str
    can_edit: bool = True
    can_manage: bool = False


class WishlistShareUpdate(BaseModel):
    can_edit: Optional[bool] = None
    can_manage: Optional[bool] = None


class UserSearchOut(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None


__all__ = [
    "ScrapeLinkResponse",
    "ExtractedLink",
    "SettingOut",
    "SettingsUpdate",
    "SettingsResponse",
    "TokenResponse",
    "LoginRequest",
    "RegisterRequest",
    "UserOut",
    "OIDCLoginRequest",
    "CategoryBase",
    "CategoryOut",
    "WishItemBase",
    "WishItemCreate",
    "WishItemOut",
    "BulkItemImportRequest",
    "BulkItemImportResponse",
    "WishlistBase",
    "WishlistCreate",
    "WishlistUpdate",
    "WishlistOut",
    "CollaboratorUser",
    "WishlistShareOut",
    "WishlistShareCreate",
    "WishlistShareUpdate",
    "UserSearchOut",
    # Gift Exchange (Secret Santa)
    "GiftGroupCreate",
    "GiftGroupUpdate",
    "PersonBase",
    "PersonCreate",
    "PersonUpdate",
    "PersonOut",
    "GiftGroupAddMember",
    "GiftGroupOut",
    "GiftAssignmentOut",
    "GiftDrawResult",
    "GiftMyAssignment",
    "GiftPairIn",
    "GiftHistoryIn",
]


# --------------------------------------------------------------------------
# Gift Exchange (Secret Santa)
# --------------------------------------------------------------------------
class GiftGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class GiftGroupUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class PersonBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    family: Optional[str] = Field(None, max_length=120)


class PersonCreate(PersonBase):
    user_id: Optional[str] = None


class PersonUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    family: Optional[str] = Field(None, max_length=120)
    # Set to null to unlink from a user.
    user_id: Optional[str] = None


class PersonOut(PersonBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: Optional[str] = None


class GiftGroupAddMember(BaseModel):
    """Add a person to a group. Reference an existing person via ``person_id``
    or supply ``name`` (and optionally ``family``/``user_id``) to create one."""

    person_id: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    family: Optional[str] = Field(None, max_length=120)
    user_id: Optional[str] = None


class GiftGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    owner_id: str
    members: list[PersonOut] = []
    my_assignment: Optional["GiftMyAssignment"] = None


class GiftAssignmentOut(BaseModel):
    giver_id: str
    giver_name: str
    receiver_id: str
    receiver_name: str
    # Slug of the receiver's linked wishlist, if they have one. Lets the UI link
    # straight from "who gives what" to that wishlist (access still depends on the
    # wishlist's visibility).
    receiver_wishlist_slug: Optional[str] = None


class GiftPairIn(BaseModel):
    """A single historical giver -> receiver pairing for a given year."""

    giver_id: str
    receiver_id: str


class GiftHistoryIn(BaseModel):
    """A full set of pairings for one (usually past) year, entered manually so
    the first in-app draw can avoid repeating them."""

    year: int = Field(..., ge=2000, le=3000)
    assignments: list[GiftPairIn]


class GiftDrawResult(BaseModel):
    year: int
    assignments: list[GiftAssignmentOut]
    unsolvable: bool = False
    message: Optional[str] = None


class GiftMyAssignment(BaseModel):
    year: int
    receiver_name: str
    receiver_wishlist_slug: Optional[str] = None

