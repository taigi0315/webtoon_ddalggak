"""sanitize character style keywords

Revision ID: 83f5330535c1
Revises: 1abef5ecd216
Create Date: 2026-01-30 23:04:01.699984

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import re
import json


revision = '83f5330535c1'
down_revision = '1abef5ecd216'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove style keywords from character identity_line and appearance fields."""
    
    # Style keywords to remove
    style_keywords = [
        "manhwa", "webtoon", "aesthetic", "flower-boy", "K-drama",
        "Korean male lead", "romance female lead", "Naver webtoon",
        "authentic", "trending", "statuesque", "willowy",
    ]
    
    # Pattern to match style phrases
    style_patterns = [
        r"\bauthent?ic\s+\w+\s+aesthetic\b",
        r"\b\w+\s+male\s+lead\s+aesthetic\b",
        r"\b\w+\s+female\s+lead\s+aesthetic\b",
        r"\bflower-boy\b",
        r"\bK-drama\b",
    ]
    
    conn = op.get_bind()
    
    # Fetch all characters with identity_line or appearance
    characters = conn.execute(
        text("SELECT character_id, identity_line, appearance FROM characters "
             "WHERE identity_line IS NOT NULL OR appearance IS NOT NULL")
    ).fetchall()
    
    updated_count = 0
    keywords_removed = set()
    
    for char in characters:
        char_id, identity_line, appearance = char
        modified = False
        
        # Sanitize identity_line
        if identity_line:
            original = identity_line
            cleaned = identity_line
            
            # Remove style keywords
            for keyword in style_keywords:
                pattern = rf"\b{re.escape(keyword)}\b"
                if re.search(pattern, cleaned, re.IGNORECASE):
                    cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
                    keywords_removed.add(keyword.lower())
                    modified = True
            
            # Remove style phrases
            for pattern in style_patterns:
                if re.search(pattern, cleaned, re.IGNORECASE):
                    cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
                    modified = True
            
            # Clean up whitespace
            cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
            cleaned = re.sub(r",\s*,", ",", cleaned)
            cleaned = cleaned.strip(" ,")
            
            if modified:
                conn.execute(
                    text("UPDATE characters SET identity_line = :cleaned WHERE character_id = :char_id"),
                    {"cleaned": cleaned, "char_id": char_id}
                )
        
        # Sanitize appearance JSON
        if appearance and isinstance(appearance, dict):
            # Check for style keywords in appearance fields
            for field in ["hair", "face", "build"]:
                if field in appearance and isinstance(appearance[field], str):
                    original = appearance[field]
                    cleaned = original
                    
                    for keyword in style_keywords:
                        pattern = rf"\b{re.escape(keyword)}\b"
                        if re.search(pattern, cleaned, re.IGNORECASE):
                            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
                            modified = True
                    
                    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
                    if cleaned != original:
                        appearance[field] = cleaned
            
            if modified:
                conn.execute(
                    text("UPDATE characters SET appearance = :appearance WHERE character_id = :char_id"),
                    {"appearance": json.dumps(appearance), "char_id": char_id}
                )
        
        if modified:
            updated_count += 1
    
    conn.commit()
    
    print(f"Migration complete: Updated {updated_count} characters")
    print(f"Keywords removed: {keywords_removed}")


def downgrade() -> None:
    """Rollback not supported - original style-polluted data not preserved."""
    pass
