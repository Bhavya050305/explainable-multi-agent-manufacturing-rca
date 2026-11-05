"""
Pydantic Schemas Package
"""

from backend.app.schemas.machine import MachineBase, MachineCreate, MachineResponse
from backend.app.schemas.sensor import SensorReadingBase, SensorReadingCreate, SensorReadingResponse, SensorWindowResponse
from backend.app.schemas.maintenance import MaintenanceHistoryBase, MaintenanceHistoryCreate, MaintenanceHistoryResponse
from backend.app.schemas.alert import AlertBase, AlertCreate, AlertResponse, PriorityAlertItem, AlertUpdateStatus
from backend.app.schemas.ticket import TicketBase, TicketCreate, TicketResponse
from backend.app.schemas.chat import ChatMessageRequest, ChatMessageResponse, ToolCallTrace, Citation, DefectInspectionResponse

__all__ = [
    "MachineBase", "MachineCreate", "MachineResponse",
    "SensorReadingBase", "SensorReadingCreate", "SensorReadingResponse", "SensorWindowResponse",
    "MaintenanceHistoryBase", "MaintenanceHistoryCreate", "MaintenanceHistoryResponse",
    "AlertBase", "AlertCreate", "AlertResponse", "PriorityAlertItem", "AlertUpdateStatus",
    "TicketBase", "TicketCreate", "TicketResponse",
    "ChatMessageRequest", "ChatMessageResponse", "ToolCallTrace", "Citation", "DefectInspectionResponse"
]
