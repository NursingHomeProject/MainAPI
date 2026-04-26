from fastapi import APIRouter

from app.modules.calculation.routes import item_router as item_calculation_router
from app.modules.calculation.routes import patient_router as patient_calculation_router
from app.modules.calculation.routes import router as calculation_router
from app.modules.auth.routes import router as auth_router
from app.modules.dashboard.routes import patient_router as patient_dashboard_router
from app.modules.dashboard.routes import router as dashboard_router
from app.modules.health.routes import router as health_router
from app.modules.internal_alerts.routes import router as alerts_router
from app.modules.inventory.routes import router as inventory_router
from app.modules.inventory.routes import stock_router as item_stock_router
from app.modules.items.routes import router as items_router
from app.modules.measurement_units.routes import router as measurement_units_router
from app.modules.patients.routes import router as patients_router
from app.modules.prescriptions.routes import patient_router as patient_prescriptions_router
from app.modules.prescriptions.routes import router as prescriptions_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(
    patient_calculation_router,
    prefix="/patients",
    tags=["calculations"],
)
api_router.include_router(
    item_calculation_router,
    prefix="/items",
    tags=["calculations"],
)
api_router.include_router(
    calculation_router,
    prefix="/calculations",
    tags=["calculations"],
)
api_router.include_router(patients_router, prefix="/patients", tags=["patients"])
api_router.include_router(
    patient_dashboard_router,
    prefix="/patients",
    tags=["dashboard"],
)
api_router.include_router(
    measurement_units_router,
    prefix="/units",
    tags=["units"],
)
api_router.include_router(items_router, prefix="/items", tags=["items"])
api_router.include_router(
    item_stock_router,
    prefix="/items",
    tags=["inventory"],
)
api_router.include_router(
    patient_prescriptions_router,
    prefix="/patients",
    tags=["prescriptions"],
)
api_router.include_router(
    prescriptions_router,
    prefix="/prescriptions",
    tags=["prescriptions"],
)
api_router.include_router(inventory_router, prefix="/inventory", tags=["inventory"])
api_router.include_router(
    alerts_router,
    prefix="/alerts",
    tags=["alerts"],
)
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
