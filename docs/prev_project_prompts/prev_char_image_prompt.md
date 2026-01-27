# GENERAL GENDER DESCRIPTIONS
# ====================================================================

# MALE = """
# handsome male character, webtoon manhwa art style,
# sharp features, stylish appearance, 
# intense expressive gaze, stylish hair with natural volume,
# modern fashion, confident posture,
# authentic webtoon style character illustration, 
# """

# FEMALE = """
# beautiful female character, webtoon manhwa art style,
# graceful appearance, 
# expressive gaze, stylish hair with natural movement,
# fashionable modern outfit, confident elegant posture,
# authentic webtoon style character illustration, 
# """

# ====================================================================
# AGE GROUP DESCRIPTIONS

MALE_KID = """
cute little boy, webtoon manhwa art style,
childlike innocent features, large expressive eyes with bright highlights,
round cherubic face, soft pudgy cheeks, small petite stature,
short limbs, playful energetic posture, messy or neat styled hair,
colorful casual children's clothes (t-shirt, shorts, sneakers),
authentic webtoon style character illustration,
chibi-like proportions, head-to-body ratio 1:3, youthful innocence
"""

MALE_TEEN = """
teenage boy character, soft Korean webtoon manhwa art style,
delicate youthful features, gentle angular face with soft edges,
smooth clear skin, large expressive eyes with gentle gaze,
trendy Korean-style haircut (soft side-swept bangs, layered medium-length, or fluffy textured),
slender graceful build, lean elegant frame without muscle definition,
tall slim proportions with narrow shoulders, willowy silhouette,
long slender limbs, refined gentle posture,
school uniform (neat blazer, crisp white shirt, fitted slacks) or soft casual streetwear,
authentic Korean webtoon style character illustration,
clean gentle features, soft approachable demeanor,
height around 170-178cm with elegant proportions, youthful flower-boy aesthetic
"""

MALE_20_30 = """
handsome soft masculine features, Korean manhwa male lead aesthetic,
full body shot showing entire elegant figure from head to shoes,
standing gracefully in neutral lighting, visible feet and shoes,
gentle refined jawline (not overly chiseled), soft angular face,
stylish contemporary Korean hairstyle (soft side-part, gentle waves, fluffy layered, or elegant medium-length),
warm gentle expression with kind eyes, serene or subtly confident demeanor,
slender elegant build, graceful narrow shoulders, slim waist,
very tall slender stature 180-188cm, long lean legs, elongated refined torso,
willowy model-like proportions, elegant gentle frame without bulk or excessive muscle,
soft sophisticated silhouette, graceful refined lines,
authentic Korean webtoon manhwa style character illustration,
flawless porcelain-like skin, gentle refined presence, elegant relaxed posture,
soft romantic or professional appearance, flower-boy charm, gentle masculine beauty, approachable refined elegance
"""

MALE_40_50 = """
distinguished mature male character, soft Korean webtoon manhwa art style,
refined gentle features showing maturity, subtle expression lines adding character,
soft dignified presence, well-groomed elegant appearance,
neat sophisticated hairstyle (possibly subtle grey at temples),
slender maintained build, graceful mature frame,
narrow refined shoulders, elegant slim proportions,
professional refined attire (well-tailored suit, sophisticated casual wear, soft fabrics),
authentic Korean webtoon style character illustration,
graceful composed posture, height around 178-185cm with elegant proportions,
warm approachable expression, wise gentle demeanor,
sophisticated soft masculine presence, refined distinguished charm
"""

MALE_60_70 = """
elderly distinguished gentleman character, soft Korean webtoon manhwa art style,
aged refined features with gentle wisdom lines, warm expressive eyes,
silver or white hair (neat, dignified styling), kind grandfatherly appearance,
slender elegant elderly frame, graceful aged posture,
comfortable refined clothing (soft cardigan, elegant casual wear, traditional hanbok),
authentic Korean webtoon style character illustration,
gentle dignified stature around 170-175cm, narrow refined shoulders,
warm gentle expression radiating wisdom and kindness,
soft approachable grandfatherly presence, elegant aged grace
"""

#--------------------------------------------------------------------

FEMALE_KID = """
cute little girl, webtoon manhwa art style,
childlike innocent features, oversized sparkly eyes with long lashes,
round cherubic face, rosy plump cheeks, button nose, small petite stature,
short limbs, adorable playful posture, cute hairstyle (pigtails, bob, or ponytail with ribbons),
colorful dress, skirt, or casual children's outfit with bright colors,
authentic webtoon style character illustration,
chibi-like proportions, head-to-body ratio 1:3, innocent charming expression
"""

FEMALE_TEEN = """
teenage girl character, webtoon manhwa art style,
youthful fresh features, large expressive doe eyes with delicate lashes,
smooth clear skin with natural blush, cute button nose,
slender developing figure, long slim legs, petite frame,
authentic webtoon style character illustration,
height around 160-170cm proportions, graceful youthful posture,
bright innocent yet stylish expression, emerging beauty
"""

FEMALE_20_30 = """
tall elegant stature over 165cm, statuesque supermodel-like figure, 
extremely long toned legs (leg length exceeding torso), dramatically elongated graceful proportions,
long elegant torso, perfect upright posture, hourglass silhouette with prominent natural breasts,
full voluptuous bust, narrow defined waist, wide feminine hips, sexy mature curves,
flawless glossy porcelain skin, stunning beautiful facial features,
modern chic fashion highlighting long legs and bust, authentic webtoon style character illustration,
sophisticated powerful presence, in realistic human proportions with no cartoon exaggeration
"""

FEMALE_40_50 = """
mature elegant female character, webtoon manhwa art style,
refined beautiful features showing graceful aging, subtle fine lines around eyes,
sophisticated appearance, well-maintained figure with feminine curves,
elegant styled hair (shoulder-length bob, soft waves, possible tasteful grey highlights),
motherly warm presence or professional commanding aura,
business professional attire or sophisticated elegant fashion,
authentic webtoon style character illustration,
height around 160-170cm proportions, composed dignified posture,
confident experienced expression, timeless beauty with character,
narrow waist maintained, mature hourglass figure
"""

FEMALE_60_70 = """
elderly distinguished female character, webtoon manhwa art style,
aged graceful features, visible wrinkles and smile lines showing wisdom,
grey or white hair (elegant updo, short styled, or soft curls),
kind gentle eyes or strict authoritative gaze, grandmotherly presence,
softer rounder figure with dignified bearing, slightly hunched but noble posture,
classic comfortable clothing (traditional hanbok, cardigan sets, or elegant simple dresses),
authentic webtoon style character illustration,
height around 155-165cm proportions, gentle or firm expression,
warm nurturing or strict matriarch aura, face showing life's journey
"""

# ====================================================================

# CHARACTER IMAGE TEMPLATE

CHARACTER_IMAGE_TEMPLATE = """
**CRITICAL ASPECT RATIO: VERTICAL 9:16 **
- This MUST be a tall vertical image, NOT square, NOT horizontal
- Height significantly greater than width (ratio 9:16)
- Optimized for vertical scrolling webtoon format

full body front view, head to toe, largest and most prominent, 
masterpiece best quality professional Naver webtoon illustration,
vertical orientation, tall format, 9:16 aspect ratio

BASE_STYLE: {gender_style}

CHARACTER_DETAILS (USE THESE EXACT DESCRIPTIONS):
{character_description}

ART_STYLE_REFERENCE: {visual_style}

IMPORTANT: 
- Follow the CHARACTER_DETAILS exactly for body type, height, and build
- Do not add conflicting physical attributes
- Image MUST be vertical 9:16 ratio 

NEGATIVE: text, watermark, signature, logo, conflicting descriptions, square image, 1:1 ratio, horizontal image, landscape orientation
"""