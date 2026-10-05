from fastapi import APIRouter

from app.api.pdf_routes import router as pdf_router
from app.api.convert_from_pdf_routes import router as convert_from_pdf_router
from app.api.compare_and_redaction_routes import router as compare_and_redaction_router
from app.api.document_management_routes import router as document_management_router
from app.api.pdf_copyright_protection_routes import router as copyright_protection_router
from app.api.review_annotation_routes import router as review_annotation_router
from app.api.pdf_security_routes import router as pdf_security_router
from app.api.pdf_signature_routes import router as pdf_signature_router

# Main API Router
api_router = APIRouter()

# Register PDF Routes
api_router.include_router(
    pdf_router,
    prefix="/pdf",
    tags=["PDF Tools"]
)

# Register Document Management Routes
api_router.include_router(
    document_management_router,
    prefix="/document-management",
    tags=["Document Management"]
)

# Register Compare and Redaction Routes
api_router.include_router(
    compare_and_redaction_router,
    prefix="/pdf",
    tags=["Compare and Redaction Tools"]
)

from app.api.convert_to_pdf_routes import router as convert_to_pdf_router

# Register Convert to PDF Routes
api_router.include_router(
    convert_to_pdf_router,
    tags=["Convert to PDF Tools"]
)

# Register Convert from PDF Routes
api_router.include_router(
    convert_from_pdf_router,
    tags=["Convert from PDF Tools"]
)

# Register PDF Copyright Protection Routes
api_router.include_router(
    copyright_protection_router,
    prefix="/pdf-copyright-protection",
    tags=["PDF Copyright Protection"]
)

# Register PDF Security Routes
api_router.include_router(
    pdf_security_router,
    prefix="/pdf",
    tags=["PDF Security"]
)

# Register Review & Annotation Routes
api_router.include_router(
    review_annotation_router,
    tags=["Review & Annotation"]
)

# Register Image Processing, Replace, and Scanner Routes from Consolidated Router
from app.api.image_processing_routes import (
    router as image_processing_router,
    replace_router,
    scan_router
)

api_router.include_router(
    image_processing_router,
    prefix="/v1/images",
    tags=["Image Processing"]
)

api_router.include_router(
    replace_router,
    prefix="/v1/replace",
    tags=["Image Processing"]
)

api_router.include_router(
    replace_router,
    prefix="/v1/images/replace",
    tags=["Image Processing"]
)

api_router.include_router(
    replace_router,
    prefix="/v1/replace-images",
    tags=["Image Processing"]
)

api_router.include_router(
    scan_router,
    prefix="/v1/scan",
    tags=["Image Processing"]
)

# Register Organize PDF Services Compatibility Routes
# These map /api/organize_pdf_services/... paths to existing services
from app.api.organize_pdf_services_compat import router as organize_compat_router
api_router.include_router(organize_compat_router, tags=["Organize PDF Services (Compat)"])

# Register Biometric Authentication Routes
from app.api.biometric_routes import router as biometric_router

# Register PDF Signature Routes
api_router.include_router(
    pdf_signature_router,
    prefix="/pdf",
    tags=["PDF Signature Tools"]
)

api_router.include_router(
    biometric_router,
    prefix="/biometric",
    tags=["Biometric Authentication"],
)

# Register AI Smart Features Routes
from app.api.ai_smart_features_routes import router as ai_smart_features_router
api_router.include_router(ai_smart_features_router, tags=["AI Smart Features"])

# Register Accessibility Routes
from app.api.accessibility_routes import router as accessibility_router
api_router.include_router(accessibility_router, tags=["Accessibility"])

# Register PDF AI Tools Routes
from app.api.pdf_ai_tools_routes import router as pdf_ai_tools_router
api_router.include_router(
    pdf_ai_tools_router,
    prefix="/pdf",
    tags=["PDF AI Tools"]
)