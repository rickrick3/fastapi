from typing import Annotated, Any, Generic, TypeVar
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Field, SQLModel, create_engine, Session, select


# -------------------------------------------------------------------
# Database Model
# -------------------------------------------------------------------
class Campaign(SQLModel, table=True):
    campaign_id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    due_date: datetime | None = Field(default=None, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=True,
        index=True
    )


# -------------------------------------------------------------------
# Request Models (for POST and PUT)
# -------------------------------------------------------------------
class CampaignCreate(BaseModel):
    name: str
    due_date: datetime | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    due_date: datetime | None = None


# -------------------------------------------------------------------
# Database Setup
# -------------------------------------------------------------------
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


# -------------------------------------------------------------------
# Lifespan Hook (Startup Task)
# -------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()

    with Session(engine) as session:
        if not session.exec(select(Campaign)).first():
            session.add_all(
                [
                    Campaign(name="Campaign tesla", due_date=datetime.now()),
                    Campaign(name="Campaign apple", due_date=datetime.now())
                ]
            )
            session.commit()

    yield


# -------------------------------------------------------------------
# FastAPI App
# -------------------------------------------------------------------
app = FastAPI(lifespan=lifespan, root_path="/api/v1")


@app.get("/")
async def read_root():
    return {"message": "Hello World!"}


# -------------------------------------------------------------------
# Generic Response Model
# -------------------------------------------------------------------
T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    data: T


# -------------------------------------------------------------------
# CRUD ENDPOINTS
# -------------------------------------------------------------------

# READ ALL
@app.get("/campaigns", response_model=ApiResponse[list[Campaign]])
async def read_campaigns(session: SessionDep):
    data = session.exec(select(Campaign)).all()
    return ApiResponse(data=data)


# READ ONE
@app.get("/campaigns/{id}", response_model=ApiResponse[Campaign])
async def read_campaign(id: int, session: SessionDep):
    campaign = session.get(Campaign, id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return ApiResponse(data=campaign)


# CREATE
@app.post("/campaigns", response_model=ApiResponse[Campaign])
async def create_campaign(body: CampaignCreate, session: SessionDep):
    new_campaign = Campaign(
        name=body.name,
        due_date=body.due_date,
        created_at=datetime.now(timezone.utc)
    )

    session.add(new_campaign)
    session.commit()
    session.refresh(new_campaign)

    return ApiResponse(data=new_campaign)


# UPDATE
@app.put("/campaigns/{id}", response_model=ApiResponse[Campaign])
async def update_campaign(id: int, body: CampaignUpdate, session: SessionDep):
    campaign = session.get(Campaign, id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if body.name is not None:
        campaign.name = body.name

    if body.due_date is not None:
        campaign.due_date = body.due_date

    session.add(campaign)
    session.commit()
    session.refresh(campaign)

    return ApiResponse(data=campaign)


# DELETE
@app.delete("/campaigns/{id}", response_model=ApiResponse[str])
async def delete_campaign(id: int, session: SessionDep):
    campaign = session.get(Campaign, id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    session.delete(campaign)
    session.commit()

    return ApiResponse(data="Campaign deleted successfully")


    """
    Using mock data without database
    """

# @app.get("/campaigns")
# async def read_campaigns():
#     return {
#         "campaigns" : data
#     }
# @app.get("/campaigns/{id}")
# async def read_campaign(id: int):
#     for campaign in data:
#         if campaign.get("campaign_id") == id:
#             return {"campaign" : campaign}
#     raise HTTPException(status_code=404, detail="Campaign not found")

# @app.post("/campaigns")
# async def create_campaign(body: dict[str, Any]):
#    new : Any = {
#          "campaign_id": len(data) + 1,
#          "name": body.get("name"),
#          "due_date": body.get("due_date"),
#          "created_at": datetime.now()
#    }
   
#    data.append(new)
#    return {"campaign" : new}

# @app.put("/campaigns/{id}")
# async def update_campaign(id: int, body: dict[str, Any]):
#     for index, campaign in enumerate(data):
#         if campaign.get("campaign_id") == id:
#             updated : Any = {
#                 "campaign_id": id,
#                 "name": body.get("name"),
#                 "due_date": body.get("due_date"),
#                 "created_at": campaign.get("created_at")
#             }
#             data[index] = updated
#             return {"campaign" : updated}
#     raise HTTPException(status_code=404, detail="Campaign not found")

# @app.delete("/campaigns/{id}")
# async def delete_campaign(id: int):
#     for index, campaign in enumerate(data):
#         if campaign.get("campaign_id") == id:
#             data.pop(index)
#             return {"message" : "Campaign deleted successfully"}
#     raise HTTPException(status_code=404, detail="Campaign not found")


