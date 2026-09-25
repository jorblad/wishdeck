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


class UpdateUserRequest(BaseModel):
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


class WishlistOut(WishlistBase):
    id: str
    slug: str
    owner_id: str
    archived: bool
    categories: list[CategoryOut] = []
    items: list[WishItemOut] = []
    shared_with_me: bool = False
    can_edit: bool = False
    collaborator_count: int = 0


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
    user: CollaboratorUser


class WishlistShareCreate(BaseModel):
    user_id: str
    can_edit: bool = True


class WishlistShareUpdate(BaseModel):
    can_edit: bool


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
]
