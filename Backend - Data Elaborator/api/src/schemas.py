from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Zone Schemas
class ZoneBase(BaseModel):
    city: str 

class ZoneCreate(ZoneBase):
    pass 

class ZoneUpdate(BaseModel):
    city: Optional[str] = None

class Zone(ZoneBase):
    id: int

    class Config:
        from_attributes = True

# Misurator Schemas
class MisuratorBase(BaseModel):
    active: bool 
    zone_id: int

class MisuratorCreate(MisuratorBase):
    pass 

class MisuratorUpdate(BaseModel):
    active:  Optional[bool] = None
    zone_id: Optional[int] = None

class Misurator(MisuratorBase):
    id: int

    class Config:
        from_attributes = True

# Misuration Schemas
class MisurationBase(BaseModel):
    value: int
    misurator_id: int

class MisurationCreate(MisurationBase): 
    pass

class MisurationUpdate(BaseModel):
    value: Optional[int] = None
    misurator_id: Optional[int] = None

class Misuration(MisurationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Schemas with relationships (for joins)
class Misurator_Zone(Misurator):
    zone: Optional[Zone] = None

class Misuration_Misurator(Misuration):
    misurator: Optional[Misurator] = None

class Misuration_Misurator_Zone(Misuration):
    misurator: Optional[Misurator_Zone] = None

class Misurator_Misurations(Misurator):
    misurations: List[Misuration] = []

class Zone_Misurators(Zone):
    misurators: List[Misurator] = []

class Zone_Misurators_Misurations(Zone):
    misurators: List[Misurator_Misurations] = []


# Statistics schema
class ZoneStats(BaseModel):
    zone_id: int
    city: str
    active_misurators: int
    total_misurators: int
    avg_misuration_value: Optional[float] = None
    last_misuration: Optional[datetime] = None

# To eliminate circular importing errors
Zone_Misurators.model_rebuild()
Zone_Misurators_Misurations.model_rebuild()
Misuration_Misurator.model_rebuild()
Misuration_Misurator_Zone.model_rebuild()
Misurator_Misurations.model_rebuild()


