"""Theme and extension management REST API endpoints.

This module provides HTTP endpoints for customization including:
- Listing, creating, and managing themes
- Installing and uninstalling themes
- Importing VS Code themes
- Managing extensions
- Exporting customizations
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Path,
    File,
    UploadFile,
    status
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from pydantic import BaseModel, Field

from src.models.theme_config import ThemeConfiguration
from src.models.extension import Extension
from src.services.theme_service import ThemeService, ThemeConfig
from src.services.extension_service import ExtensionService, ExtensionConfig
from src.database.base import get_db

# Initialize router
router = APIRouter(prefix="/api/v1", tags=["Customization"])

# Initialize services (singletons)
theme_service = ThemeService(config=ThemeConfig())
extension_service = ExtensionService(config=ExtensionConfig())


# Pydantic models for request/response validation
class ThemeResponse(BaseModel):
    """Response model for theme."""
    themeId: UUID
    name: str
    description: Optional[str]
    category: str
    author: str
    version: str
    colors: dict
    fonts: dict
    customCss: Optional[str]
    isBuiltin: bool
    isPublic: bool
    downloads: int
    rating: float
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


class ThemeListResponse(BaseModel):
    """Response model for theme list."""
    themes: List[ThemeResponse]
    total: int
    limit: int
    offset: int


class CreateThemeRequest(BaseModel):
    """Request model for creating a theme."""
    name: str = Field(..., description="Theme name")
    description: Optional[str] = Field(None, description="Theme description")
    colors: dict = Field(..., description="Color configuration")
    fonts: dict = Field(..., description="Font configuration")
    customCss: Optional[str] = Field(None, description="Custom CSS")
    isPublic: bool = Field(default=False, description="Make theme public")
    importUrl: Optional[str] = Field(None, description="URL to import theme from")


class UpdateThemeRequest(BaseModel):
    """Request model for updating a theme."""
    name: Optional[str] = None
    description: Optional[str] = None
    colors: Optional[dict] = None
    fonts: Optional[dict] = None
    customCss: Optional[str] = None
    isPublic: Optional[bool] = None


class ExtensionResponse(BaseModel):
    """Response model for extension."""
    extensionId: UUID
    name: str
    description: Optional[str]
    version: str
    author: str
    category: str
    entryPoint: str
    permissions: List[str]
    isEnabled: bool
    isVerified: bool
    downloads: int
    rating: float
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


class ExtensionListResponse(BaseModel):
    """Response model for extension list."""
    extensions: List[ExtensionResponse]
    total: int
    limit: int
    offset: int


# Dependency to get current user ID (placeholder for auth)
async def get_current_user_id() -> UUID:
    """Get current authenticated user ID.

    TODO: Replace with actual authentication logic.
    """
    # Placeholder - in production this would verify JWT/session token
    return UUID("00000000-0000-0000-0000-000000000001")


# Theme Endpoints
@router.get("/themes", response_model=ThemeListResponse)
async def list_themes(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    sortBy: str = Query("name", description="Sort by field"),
    sortOrder: str = Query("asc", description="Sort order (asc/desc)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum themes to return"),
    offset: int = Query(0, ge=0, description="Number of themes to skip"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """List available themes.

    Args:
        category: Optional category filter (builtin, user, public, installed)
        search: Optional search query
        sortBy: Sort field (name, rating, downloads, created, updated)
        sortOrder: Sort order (asc or desc)
        limit: Maximum number of themes to return (1-100)
        offset: Number of themes to skip for pagination
        db: Database session
        user_id: Current user ID

    Returns:
        ThemeListResponse with themes array
    """
    from src.models.user_profile import UserProfile

    # Build query
    query = select(ThemeConfiguration)

    # Apply category filter
    if category == "builtin":
        query = query.where(ThemeConfiguration.is_builtin == True)
    elif category == "user":
        query = query.where(
            ThemeConfiguration.created_by == user_id,
            ThemeConfiguration.is_builtin == False
        )
    elif category == "public":
        query = query.where(
            ThemeConfiguration.is_public == True,
            ThemeConfiguration.is_builtin == False
        )
    elif category == "installed":
        # Get user's installed themes from profile
        profile_query = select(UserProfile).where(UserProfile.user_id == user_id)
        profile_result = await db.execute(profile_query)
        profile = profile_result.scalar_one_or_none()
        if profile and profile.installed_themes:
            query = query.where(ThemeConfiguration.theme_id.in_(profile.installed_themes))
        else:
            query = query.where(ThemeConfiguration.theme_id == None)  # Return empty

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                ThemeConfiguration.name.ilike(search_pattern),
                ThemeConfiguration.description.ilike(search_pattern),
                ThemeConfiguration.author.ilike(search_pattern)
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_field = getattr(ThemeConfiguration, sortBy.lower(), ThemeConfiguration.name)
    if sortOrder.lower() == "desc":
        query = query.order_by(sort_field.desc())
    else:
        query = query.order_by(sort_field.asc())

    # Apply pagination
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    themes = result.scalars().all()

    # Convert to response models
    theme_responses = [
        ThemeResponse(
            themeId=t.theme_id,
            name=t.name,
            description=t.description,
            category=t.category,
            author=t.author,
            version=t.version,
            colors=t.colors,
            fonts=t.fonts,
            customCss=t.custom_css,
            isBuiltin=t.is_builtin,
            isPublic=t.is_public,
            downloads=t.downloads,
            rating=t.rating,
            createdAt=t.created_at,
            updatedAt=t.updated_at
        )
        for t in themes
    ]

    return ThemeListResponse(
        themes=theme_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("/themes", response_model=ThemeResponse, status_code=status.HTTP_201_CREATED)
async def create_theme(
    request: CreateThemeRequest = None,
    file: Optional[UploadFile] = File(None, description="Theme file to import"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create or import a theme.

    Args:
        request: Theme creation parameters
        file: Optional theme file to import
        db: Database session
        user_id: Current user ID

    Returns:
        Created theme details

    Raises:
        HTTPException: 400 if validation fails, 409 if name conflict
    """
    from datetime import timezone

    # Handle file import
    if file:
        try:
            file_content = await file.read()
            theme_data = await theme_service.import_theme(
                file_content=file_content,
                file_name=file.filename,
                user_id=str(user_id)
            )
            request.name = theme_data.get("name", request.name)
            request.colors = theme_data.get("colors", request.colors)
            request.fonts = theme_data.get("fonts", request.fonts)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to import theme: {str(e)}"
            )

    # Handle URL import
    elif request.importUrl:
        try:
            theme_data = await theme_service.import_from_url(
                url=request.importUrl,
                user_id=str(user_id)
            )
            request.name = theme_data.get("name", request.name)
            request.colors = theme_data.get("colors", request.colors)
            request.fonts = theme_data.get("fonts", request.fonts)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to import theme from URL: {str(e)}"
            )

    # Validate theme
    try:
        validation_result = await theme_service.validate_theme({
            "name": request.name,
            "colors": request.colors,
            "fonts": request.fonts,
            "customCss": request.customCss
        })
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Theme validation failed: {', '.join(validation_result.errors)}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Theme validation failed: {str(e)}"
        )

    # Check for name conflict
    existing_query = select(ThemeConfiguration).where(
        ThemeConfiguration.name == request.name,
        ThemeConfiguration.created_by == user_id
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Theme with name '{request.name}' already exists"
        )

    # Create theme
    theme = ThemeConfiguration(
        created_by=user_id,
        name=request.name,
        description=request.description,
        category="user",
        author="User",  # TODO: Get from user profile
        version="1.0.0",
        colors=request.colors,
        fonts=request.fonts,
        custom_css=request.customCss,
        is_builtin=False,
        is_public=request.isPublic
    )

    db.add(theme)
    await db.commit()
    await db.refresh(theme)

    return ThemeResponse(
        themeId=theme.theme_id,
        name=theme.name,
        description=theme.description,
        category=theme.category,
        author=theme.author,
        version=theme.version,
        colors=theme.colors,
        fonts=theme.fonts,
        customCss=theme.custom_css,
        isBuiltin=theme.is_builtin,
        isPublic=theme.is_public,
        downloads=theme.downloads,
        rating=theme.rating,
        createdAt=theme.created_at,
        updatedAt=theme.updated_at
    )


@router.get("/themes/{themeId}", response_model=ThemeResponse)
async def get_theme(
    themeId: UUID = Path(..., description="Theme ID"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get theme details.

    Args:
        themeId: Theme identifier
        db: Database session
        user_id: Current user ID

    Returns:
        Theme details

    Raises:
        HTTPException: 404 if theme not found
    """
    query = select(ThemeConfiguration).where(ThemeConfiguration.theme_id == themeId)
    result = await db.execute(query)
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theme {themeId} not found"
        )

    # Check access permissions
    if not theme.is_public and not theme.is_builtin and theme.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to private theme"
        )

    return ThemeResponse(
        themeId=theme.theme_id,
        name=theme.name,
        description=theme.description,
        category=theme.category,
        author=theme.author,
        version=theme.version,
        colors=theme.colors,
        fonts=theme.fonts,
        customCss=theme.custom_css,
        isBuiltin=theme.is_builtin,
        isPublic=theme.is_public,
        downloads=theme.downloads,
        rating=theme.rating,
        createdAt=theme.created_at,
        updatedAt=theme.updated_at
    )


@router.patch("/themes/{themeId}", response_model=ThemeResponse)
async def update_theme(
    themeId: UUID = Path(..., description="Theme ID"),
    request: UpdateThemeRequest = None,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update theme configuration.

    Args:
        themeId: Theme identifier
        request: Update parameters
        db: Database session
        user_id: Current user ID

    Returns:
        Updated theme details

    Raises:
        HTTPException: 404 if not found, 403 if not owner
    """
    from datetime import timezone

    query = select(ThemeConfiguration).where(ThemeConfiguration.theme_id == themeId)
    result = await db.execute(query)
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theme {themeId} not found"
        )

    # Check ownership
    if theme.created_by != user_id or theme.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify this theme"
        )

    # Update fields
    if request.name is not None:
        theme.name = request.name
    if request.description is not None:
        theme.description = request.description
    if request.colors is not None:
        theme.colors = request.colors
    if request.fonts is not None:
        theme.fonts = request.fonts
    if request.customCss is not None:
        theme.custom_css = request.customCss
    if request.isPublic is not None:
        theme.is_public = request.isPublic

    theme.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(theme)

    return ThemeResponse(
        themeId=theme.theme_id,
        name=theme.name,
        description=theme.description,
        category=theme.category,
        author=theme.author,
        version=theme.version,
        colors=theme.colors,
        fonts=theme.fonts,
        customCss=theme.custom_css,
        isBuiltin=theme.is_builtin,
        isPublic=theme.is_public,
        downloads=theme.downloads,
        rating=theme.rating,
        createdAt=theme.created_at,
        updatedAt=theme.updated_at
    )


@router.delete("/themes/{themeId}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_theme(
    themeId: UUID = Path(..., description="Theme ID"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Delete a user-created theme.

    Args:
        themeId: Theme identifier
        db: Database session
        user_id: Current user ID

    Raises:
        HTTPException: 404 if not found, 403 if not owner
    """
    query = select(ThemeConfiguration).where(ThemeConfiguration.theme_id == themeId)
    result = await db.execute(query)
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theme {themeId} not found"
        )

    # Check ownership
    if theme.created_by != user_id or theme.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete this theme"
        )

    await db.delete(theme)
    await db.commit()


@router.post("/themes/{themeId}/install", response_model=ThemeResponse)
async def install_theme(
    themeId: UUID = Path(..., description="Theme ID"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Install a theme for the user.

    Args:
        themeId: Theme identifier
        db: Database session
        user_id: Current user ID

    Returns:
        Installed theme details

    Raises:
        HTTPException: 404 if theme not found, 409 if already installed
    """
    from src.models.user_profile import UserProfile

    # Get theme
    theme_query = select(ThemeConfiguration).where(ThemeConfiguration.theme_id == themeId)
    theme_result = await db.execute(theme_query)
    theme = theme_result.scalar_one_or_none()

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theme {themeId} not found"
        )

    # Get or create user profile
    profile_query = select(UserProfile).where(UserProfile.user_id == user_id)
    profile_result = await db.execute(profile_query)
    profile = profile_result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=user_id, installed_themes=[])
        db.add(profile)

    # Check if already installed
    if profile.installed_themes and themeId in profile.installed_themes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Theme already installed"
        )

    # Install theme
    if not profile.installed_themes:
        profile.installed_themes = []
    profile.installed_themes.append(themeId)

    # Increment download count
    theme.downloads += 1

    await db.commit()
    await db.refresh(theme)

    return ThemeResponse(
        themeId=theme.theme_id,
        name=theme.name,
        description=theme.description,
        category=theme.category,
        author=theme.author,
        version=theme.version,
        colors=theme.colors,
        fonts=theme.fonts,
        customCss=theme.custom_css,
        isBuiltin=theme.is_builtin,
        isPublic=theme.is_public,
        downloads=theme.downloads,
        rating=theme.rating,
        createdAt=theme.created_at,
        updatedAt=theme.updated_at
    )


@router.post("/themes/{themeId}/uninstall", status_code=status.HTTP_204_NO_CONTENT)
async def uninstall_theme(
    themeId: UUID = Path(..., description="Theme ID"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Uninstall a theme.

    Args:
        themeId: Theme identifier
        db: Database session
        user_id: Current user ID

    Raises:
        HTTPException: 404 if theme not found or not installed
    """
    from src.models.user_profile import UserProfile

    # Get user profile
    profile_query = select(UserProfile).where(UserProfile.user_id == user_id)
    profile_result = await db.execute(profile_query)
    profile = profile_result.scalar_one_or_none()

    if not profile or not profile.installed_themes or themeId not in profile.installed_themes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not installed"
        )

    # Uninstall theme
    profile.installed_themes.remove(themeId)
    await db.commit()


@router.get("/themes/{themeId}/export")
async def export_theme(
    themeId: UUID = Path(..., description="Theme ID"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Export theme as JSON file.

    Args:
        themeId: Theme identifier
        db: Database session
        user_id: Current user ID

    Returns:
        FileResponse with theme JSON

    Raises:
        HTTPException: 404 if theme not found
    """
    query = select(ThemeConfiguration).where(ThemeConfiguration.theme_id == themeId)
    result = await db.execute(query)
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theme {themeId} not found"
        )

    # Check access permissions
    if not theme.is_public and not theme.is_builtin and theme.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to private theme"
        )

    # Export theme
    try:
        export_path = await theme_service.export_theme(str(themeId))
        return FileResponse(
            path=export_path,
            media_type="application/json",
            filename=f"{theme.name}.theme.json"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to export theme: {str(e)}"
        )


@router.post("/themes/import/vscode", response_model=ThemeResponse, status_code=status.HTTP_201_CREATED)
async def import_vscode_theme(
    file: UploadFile = File(..., description="VS Code theme JSON file"),
    name: Optional[str] = Query(None, description="Custom theme name"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Import VS Code theme.

    Args:
        file: VS Code theme JSON file
        name: Optional custom theme name
        db: Database session
        user_id: Current user ID

    Returns:
        Created theme details

    Raises:
        HTTPException: 400 if import fails
    """
    from datetime import timezone

    try:
        file_content = await file.read()
        theme_data = await theme_service.import_vscode_theme(
            file_content=file_content,
            user_id=str(user_id),
            custom_name=name
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to import VS Code theme: {str(e)}"
        )

    # Create theme
    theme = ThemeConfiguration(
        created_by=user_id,
        name=theme_data["name"],
        description=theme_data.get("description", "Imported from VS Code"),
        category="user",
        author="User",
        version="1.0.0",
        colors=theme_data["colors"],
        fonts=theme_data["fonts"],
        is_builtin=False,
        is_public=False
    )

    db.add(theme)
    await db.commit()
    await db.refresh(theme)

    return ThemeResponse(
        themeId=theme.theme_id,
        name=theme.name,
        description=theme.description,
        category=theme.category,
        author=theme.author,
        version=theme.version,
        colors=theme.colors,
        fonts=theme.fonts,
        customCss=theme.custom_css,
        isBuiltin=theme.is_builtin,
        isPublic=theme.is_public,
        downloads=theme.downloads,
        rating=theme.rating,
        createdAt=theme.created_at,
        updatedAt=theme.updated_at
    )


# Extension Endpoints
@router.get("/extensions", response_model=ExtensionListResponse)
async def list_extensions(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    limit: int = Query(20, ge=1, le=100, description="Maximum extensions to return"),
    offset: int = Query(0, ge=0, description="Number of extensions to skip"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """List available extensions.

    Args:
        category: Optional category filter
        search: Optional search query
        limit: Maximum number of extensions to return (1-100)
        offset: Number of extensions to skip for pagination
        db: Database session
        user_id: Current user ID

    Returns:
        ExtensionListResponse with extensions array
    """
    # Build query
    query = select(Extension)

    # Apply category filter
    if category:
        query = query.where(Extension.category == category)

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Extension.name.ilike(search_pattern),
                Extension.description.ilike(search_pattern)
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.limit(limit).offset(offset).order_by(Extension.name.asc())
    result = await db.execute(query)
    extensions = result.scalars().all()

    # Convert to response models
    extension_responses = [
        ExtensionResponse(
            extensionId=e.extension_id,
            name=e.name,
            description=e.description,
            version=e.version,
            author=e.author,
            category=e.category,
            entryPoint=e.entry_point,
            permissions=e.permissions,
            isEnabled=e.is_enabled,
            isVerified=e.is_verified,
            downloads=e.downloads,
            rating=e.rating,
            createdAt=e.created_at,
            updatedAt=e.updated_at
        )
        for e in extensions
    ]

    return ExtensionListResponse(
        extensions=extension_responses,
        total=total,
        limit=limit,
        offset=offset
    )
